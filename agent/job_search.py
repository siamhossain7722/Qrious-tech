"""
LinkedIn Job Search Module
Searches for jobs on LinkedIn using configured filters.
"""
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlencode, quote_plus

from playwright.async_api import Page


@dataclass
class JobListing:
    """Represents a single job listing found on LinkedIn."""
    job_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    is_easy_apply: bool = False
    description: str = ""
    posted_date: str = ""
    applicant_count: str = ""
    employment_type: str = ""
    experience_level: str = ""
    workplace_type: str = ""
    match_score: int = 0
    match_reasons: str = ""


DATE_POSTED_FILTERS = {
    "past_24_hours": "r86400",
    "past_week": "r604800",
    "past_month": "r2592000",
    "any_time": "",
}

EXPERIENCE_LEVEL_FILTERS = {
    "Internship": "1",
    "Entry level": "2",
    "Associate": "3",
    "Mid-Senior level": "4",
    "Director": "5",
    "Executive": "6",
}

WORKPLACE_TYPE_FILTERS = {
    "all": "",
    "any": "",
    "onsite": "1",
    "remote": "2",
    "hybrid": "3",
    "remote_or_onsite": "1,2",
    "remote_or_hybrid": "2,3",
}

JOB_CARD_SELECTORS = [
    "li.jobs-search-results__list-item",
    "li.scaffold-layout__list-item",
    "li[data-occludable-job-id]",
    "div[data-job-id]",
    ".jobs-search-results-list__list-item",
    "div.job-card-container",
    "div.job-card-list__entity-lockup",
    "ul.jobs-search__results-list > li",
    "ul.jobs-search-results__list > li",
]


class JobSearcher:
    """Searches LinkedIn jobs and returns a list of JobListing objects."""

    def __init__(self, browser_controller, config: dict, cv_matcher=None):
        self.browser = browser_controller
        self.page: Page = browser_controller.page
        self.config = config
        self.search_cfg = config.get("job_search", {})
        self.cv_matcher = cv_matcher

    def _build_search_url(self, keyword: str, start: int = 0) -> str:
        """Build LinkedIn jobs search URL with worldwide/regional filters & pagination."""
        params = {
            "keywords": keyword,
        }

        # Apply Type (All vs Easy Apply Only)
        apply_type = str(self.search_cfg.get("apply_type", "all")).lower()
        if apply_type == "easy_apply":
            params["f_AL"] = "true"

        if start > 0:
            params["start"] = str(start)

        location = str(self.search_cfg.get("location", "Worldwide")).strip()
        loc_lower = location.lower()

        # LinkedIn official geoIds for precise regional/global targeting:
        if loc_lower in ["worldwide", "global", "all", "any", "world", "everywhere", ""]:
            params["location"] = "Worldwide"
            params["geoId"] = "92000000"
        elif loc_lower in ["united states", "us", "usa"]:
            params["location"] = "United States"
            params["geoId"] = "103644278"
        elif loc_lower in ["europe", "eu", "european union"]:
            params["location"] = "European Union"
            params["geoId"] = "91000000"
        elif loc_lower in ["united kingdom", "uk", "great britain"]:
            params["location"] = "United Kingdom"
            params["geoId"] = "102257491"
        elif loc_lower in ["canada", "ca"]:
            params["location"] = "Canada"
            params["geoId"] = "101174742"
        elif loc_lower in ["germany", "de"]:
            params["location"] = "Germany"
            params["geoId"] = "101282230"
        elif loc_lower in ["bangladesh", "bd"]:
            params["location"] = "Bangladesh"
            params["geoId"] = "106215326"
        else:
            params["location"] = location

        date_posted = self.search_cfg.get("date_posted", "past_week")
        f_tpr = DATE_POSTED_FILTERS.get(date_posted, "r604800")
        if f_tpr:
            params["f_TPR"] = f_tpr

        # Experience levels
        exp_levels = self.search_cfg.get("experience_levels", [])
        exp_codes = [
            EXPERIENCE_LEVEL_FILTERS[lvl]
            for lvl in exp_levels
            if lvl in EXPERIENCE_LEVEL_FILTERS
        ]
        if exp_codes:
            params["f_E"] = ",".join(exp_codes)

        # Workplace Type (Remote / On-site / Hybrid / Any)
        wt = str(self.search_cfg.get("workplace_type", "")).lower()
        if not wt and self.search_cfg.get("remote", False):
            wt = "remote"

        if wt in WORKPLACE_TYPE_FILTERS and WORKPLACE_TYPE_FILTERS[wt]:
            params["f_WT"] = WORKPLACE_TYPE_FILTERS[wt]

        query = urlencode(params)
        return f"https://www.linkedin.com/jobs/search/?{query}"

    async def search(self) -> List[JobListing]:
        """Search for all configured keywords with pagination to reach target application count."""
        keywords = self.search_cfg.get("keywords", ["Python Developer"])
        max_per_run = int(self.search_cfg.get("max_applications_per_run", 30))
        blacklist = [c.lower().strip() for c in self.search_cfg.get("blacklisted_companies", [])]
        applied_companies = set(c.lower().strip() for c in self.search_cfg.get("applied_companies", []))
        required_kws = [k.lower() for k in self.search_cfg.get("required_keywords", [])]
        min_score = int(self.search_cfg.get("min_match_score", 50))
        location = self.search_cfg.get("location", "Worldwide")

        # Load database records of previously applied/processed jobs
        db_job_ids = set(str(j).strip() for j in self.search_cfg.get("applied_job_ids", []))
        db_urls = set(str(u).split("?")[0].rstrip("/") for u in self.search_cfg.get("applied_urls", []))
        db_company_titles = set(self.search_cfg.get("applied_company_titles", []))

        try:
            from dashboard.models import JobApplication
            for ja in JobApplication.objects.all():
                if ja.job_id:
                    db_job_ids.add(str(ja.job_id).strip())
                if ja.url:
                    db_urls.add(ja.url.split("?")[0].rstrip("/"))
                if ja.company and ja.title:
                    db_company_titles.add((ja.company.lower().strip(), ja.title.lower().strip()))
                if ja.company:
                    applied_companies.add(ja.company.lower().strip())
        except Exception:
            pass

        print(f"🌍 Job Search Scope: {location.title()} | Target: {max_per_run} applications | Min CV Score: {min_score}%")
        print(f"   📊 Loaded {len(db_job_ids)} existing job IDs and {len(applied_companies)} company records from database.")

        all_jobs: List[JobListing] = []
        seen_ids = set()

        for keyword in keywords:
            print(f"\n🔍 Searching for: '{keyword}' (Worldwide / {location})...")

            # Paginate up to 4 pages per keyword (up to 100 jobs per keyword)
            for page_num in range(4):
                start_offset = page_num * 25
                url = self._build_search_url(keyword, start=start_offset)

                try:
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await self.browser.human_delay(1500, 3000)
                except Exception as e:
                    print(f"   ⚠️ Navigation timeout on page {page_num + 1}: {e}")
                    break

                page_jobs = await self._scrape_job_listings()
                if not page_jobs:
                    break

                new_on_page = 0
                for idx, job in enumerate(page_jobs, start=1):
                    if job.job_id and job.job_id in seen_ids:
                        continue

                    # 1. Check if job ID, URL, or Title+Company has already been applied/processed in database
                    clean_job_url = job.url.split("?")[0].rstrip("/") if job.url else ""
                    job_key = (job.company.lower().strip(), job.title.lower().strip())

                    if (job.job_id and job.job_id in db_job_ids) or (clean_job_url and clean_job_url in db_urls) or (job_key in db_company_titles):
                        print(f"   ℹ️ Skipping serial #{idx}: '{job.title}' at '{job.company}' (Already applied/processed)")
                        continue

                    # 2. Filter blacklisted companies
                    if job.company.lower().strip() in blacklist:
                        print(f"   ⛔ Skipping blacklisted company: {job.company}")
                        continue

                    # 3. Filter previously applied companies
                    if job.company.lower().strip() in applied_companies:
                        print(f"   ℹ️ Skipping {job.company} (Already applied to this company previously)")
                        continue

                    # 4. Filter by required keywords in title
                    if required_kws:
                        title_lower = job.title.lower()
                        if not any(kw in title_lower for kw in required_kws):
                            continue

                    # 5. CV Match scoring
                    if self.cv_matcher:
                        score, reasons, _ = self.cv_matcher.evaluate_match(job.title, job.company, job.description)
                        job.match_score = score
                        job.match_reasons = reasons
                        print(f"   🎯 CV Match: {score}% for serial #{idx} '{job.title}' at '{job.company}' ({reasons})")

                    if job.job_id:
                        seen_ids.add(job.job_id)
                    all_jobs.append(job)
                    new_on_page += 1

                print(f"   📄 Page {page_num + 1}: Found {len(page_jobs)} listings ({new_on_page} new valid)")

                # If we've collected enough high matching jobs across keywords, stop paginating
                if len([j for j in all_jobs if j.match_score >= min_score]) >= max_per_run * 1.5:
                    break

        # Sort jobs by match score descending to apply to best matches first
        all_jobs.sort(key=lambda j: j.match_score, reverse=True)

        # Filter by minimum score if threshold set
        matching_jobs = [j for j in all_jobs if j.match_score >= min_score]
        if not matching_jobs and all_jobs:
            print(f"   ⚠️ No jobs met min score {min_score}%. Taking top candidates.")
            matching_jobs = all_jobs

        print(f"\n✅ Total Found: {len(all_jobs)} jobs | {len(matching_jobs)} matching CV criteria (Target: {max_per_run}).")
        return matching_jobs[:max_per_run]

    async def _scrape_job_listings(self) -> List[JobListing]:
        """Scrape job cards from the search results page."""
        jobs = []
        try:
            # Wait for job cards or search container
            selector_str = ", ".join(JOB_CARD_SELECTORS)
            try:
                await self.page.wait_for_selector(
                    f"{selector_str}, .jobs-search-no-results, .no-eval-results, .jobs-search-results-list, .scaffold-layout__list",
                    timeout=10000,
                )
            except Exception:
                pass

            # Scroll container to trigger lazy loading of cards
            try:
                await self.page.evaluate("""
                    () => {
                        const containers = [
                            document.querySelector('.jobs-search-results-list'),
                            document.querySelector('.scaffold-layout__list'),
                            document.querySelector('.jobs-search__results-list'),
                            document.documentElement
                        ];
                        for (const c of containers) {
                            if (c) {
                                c.scrollTop = c.scrollHeight / 2;
                            }
                        }
                    }
                """)
            except Exception:
                pass

            await self.browser.human_delay(1500, 2500)

            # Query all matching job cards
            job_cards = []
            for sel in JOB_CARD_SELECTORS:
                found = await self.page.query_selector_all(sel)
                if found:
                    job_cards = found
                    break

            if not job_cards:
                # Fallback: query links with job URLs
                job_cards = await self.page.query_selector_all(
                    "a[href*='/jobs/view/'], a[href*='currentJobId=']"
                )

            print(f"   Found {len(job_cards)} job cards on page.")

            for card in job_cards:
                try:
                    job = await self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    print(f"   ⚠️ Error parsing job card: {e}")
                    continue

        except Exception as e:
            print(f"   ⚠️ Could not load job results: {e}")

        return jobs

    async def _parse_job_card(self, card) -> Optional[JobListing]:
        """Extract data from a single job card element."""
        try:
            url = ""
            job_id = ""

            # Check if card itself is an anchor
            tag_name = await card.evaluate("el => el.tagName.toLowerCase()")
            if tag_name == "a":
                link_el = card
                url = await card.get_attribute("href") or ""
            else:
                link_el = await card.query_selector(
                    "a.job-card-list__title--link, a.job-card-container__link, a[data-control-id], a.job-card-list__title, a.base-card__full-link, a[href*='/jobs/view/'], a[href*='currentJobId=']"
                )
                if link_el:
                    url = await link_el.get_attribute("href") or ""

            if url and not url.startswith("http"):
                url = f"https://www.linkedin.com{url}"

            # Extract job ID
            data_id = (
                await card.get_attribute("data-occludable-job-id")
                or await card.get_attribute("data-job-id")
                or ""
            )
            if not data_id:
                child_id_el = await card.query_selector("[data-job-id], [data-occludable-job-id]")
                if child_id_el:
                    data_id = (
                        await child_id_el.get_attribute("data-occludable-job-id")
                        or await child_id_el.get_attribute("data-job-id")
                        or ""
                    )

            if data_id:
                job_id = str(data_id).strip()
            elif "/jobs/view/" in url:
                job_id = url.split("/jobs/view/")[1].split("/")[0].split("?")[0]
            elif "currentJobId=" in url:
                job_id = url.split("currentJobId=")[1].split("&")[0]

            # Job title
            title = ""
            title_el = await card.query_selector(
                ".job-card-list__title, .job-card-container__link span, a.job-card-list__title--link, a.job-card-container__link, strong.job-card-list__title, .base-search-card__title, .artdeco-entity-lockup__title"
            )
            if title_el:
                title = (await title_el.inner_text()).strip()
            elif link_el:
                title = (await link_el.inner_text()).strip()

            if not title or title.lower() in ["unknown", ""]:
                # Try raw text extraction
                raw_text = await card.inner_text()
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                if lines:
                    title = lines[0]

            title = title.split("\n")[0].strip()

            # Company
            company = ""
            company_el = await card.query_selector(
                ".job-card-container__primary-description, .artdeco-entity-lockup__subtitle, .job-card-container__company-name, .base-search-card__subtitle, a[data-control-name='job_card_company_name'], .job-card-container__company-name span"
            )
            if company_el:
                company = (await company_el.inner_text()).strip()
            else:
                raw_text = await card.inner_text()
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                if len(lines) > 1:
                    company = lines[1]

            company = company.split("\n")[0].strip()

            # Location
            location = "Worldwide"
            location_el = await card.query_selector(
                ".job-card-container__metadata-item, .artdeco-entity-lockup__caption, .job-card-container__metadata-wrapper, .job-search-card__location, ul.job-card-container__metadata-wrapper li"
            )
            if location_el:
                loc_text = (await location_el.inner_text()).strip()
                if loc_text:
                    location = loc_text.split("\n")[0].strip()

            # Easy Apply detection
            easy_apply_el = await card.query_selector(
                ".job-card-container__apply-method, .job-card-list__easy-apply, [aria-label*='Easy Apply']"
            )
            is_easy_apply = True
            if easy_apply_el:
                apply_text = (await easy_apply_el.inner_text()).lower()
                is_easy_apply = "easy apply" in apply_text or True

            # Discard broken cards
            if not job_id:
                return None

            if not url:
                url = f"https://www.linkedin.com/jobs/view/{job_id}/"

            return JobListing(
                job_id=job_id,
                title=title or "Software Developer",
                company=company or "Confidential",
                location=location or "Worldwide",
                url=url.split("?")[0],
                is_easy_apply=is_easy_apply,
            )
        except Exception as e:
            print(f"   ⚠️ Error parsing card: {e}")
            return None

    async def get_job_details(self, job: JobListing) -> JobListing:
        """Fetch full job description from the job detail page."""
        try:
            await self.page.goto(job.url, wait_until="domcontentloaded", timeout=20000)
            await self.browser.human_delay(2000, 3000)

            # Description
            desc_el = await self.page.query_selector(
                ".jobs-description__content, .job-details-module, .jobs-box__html-content, .jobs-description-content__text, #job-details"
            )
            if desc_el:
                job.description = (await desc_el.inner_text()).strip()[:3000]

            # Applicant count
            insight_el = await self.page.query_selector(
                ".jobs-unified-top-card__applicant-count, .jobs-details__top-card span[class*='applicant'], .num-applicants__caption"
            )
            if insight_el:
                job.applicant_count = (await insight_el.inner_text()).strip()

            # Check for Easy Apply button
            easy_btn = await self.page.query_selector(
                ".jobs-apply-button--top-card, button.jobs-apply-button, button:has-text('Easy Apply')"
            )
            if easy_btn:
                btn_text = (await easy_btn.inner_text()).lower()
                job.is_easy_apply = "easy apply" in btn_text

        except Exception as e:
            print(f"   ⚠️ Could not fetch details for {job.title}: {e}")

        return job

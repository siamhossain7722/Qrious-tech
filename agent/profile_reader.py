"""
LinkedIn Profile Reader
Scrapes the logged-in user's LinkedIn profile to extract:
- Name, headline, location, about
- Skills, experience, education
- Profile photo URL, connection count
"""
import json
import asyncio
import re
from typing import Optional, List, Dict

from playwright.async_api import Page


class ProfileReader:
    """Reads a LinkedIn profile after login and returns structured data."""

    def __init__(self, browser_controller):
        self.browser = browser_controller
        self.page: Page = browser_controller.page

    async def read_own_profile(self) -> dict:
        """
        Navigate to the logged in user's profile and extract all information.
        Returns a dictionary with profile fields.
        """
        print("\n👤 Reading LinkedIn profile...")

        profile = {
            "full_name": "",
            "headline": "",
            "location": "",
            "about": "",
            "profile_url": "",
            "profile_photo_url": "",
            "connections": "",
            "skills": [],
            "experience": [],
            "education": [],
        }

        try:
            if not self.page or self.page.is_closed():
                return profile

            # 1. Determine profile URL
            profile_url = await self._get_profile_url()
            if profile_url:
                profile["profile_url"] = profile_url
                current_clean_url = self.page.url.split("?")[0].rstrip("/")
                if not current_clean_url.startswith(profile_url.rstrip("/")) and "/in/me" not in profile_url:
                    try:
                        await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
                        await self.browser.human_delay(2000, 3000)
                    except Exception as e:
                        print(f"   ⚠️ Navigation info: {e}")

            # Get canonical vanity URL after redirects
            canonical_url = self.page.url.split("?")[0].rstrip("/")
            if "/in/" in canonical_url and not canonical_url.endswith("/me"):
                profile["profile_url"] = canonical_url

            # Scroll page to trigger lazy loading of profile sections
            await self.browser.scroll_slowly(1200)
            await asyncio.sleep(1.5)

            # Fast check from feed page widget if currently on feed or home
            curr_url = self.page.url
            if "/feed" in curr_url or "linkedin.com" in curr_url:
                try:
                    feed_name = await self._get_text(".feed-identity-module__actor-meta a, .identity-headline, a[href*='/in/'].ember-view, div.feed-identity-module div.t-16, div.feed-identity-module h3, div.feed-identity-module a")
                    if feed_name and len(feed_name) > 2 and "welcome" not in feed_name.lower() and "feed" not in feed_name.lower():
                        profile["full_name"] = feed_name

                    feed_headline = await self._get_text(".feed-identity-module__actor-meta p, div.feed-identity-module div.t-12, .feed-identity-module .text-body-xsmall")
                    if feed_headline and feed_headline != profile["full_name"]:
                        profile["headline"] = feed_headline

                    feed_img = await self.page.query_selector(".feed-identity-module img, img.feed-identity-module__member-photo, img[alt*='Photo of']")
                    if feed_img:
                        profile["profile_photo_url"] = await feed_img.get_attribute("src") or ""

                    prof_link = await self.page.query_selector(".feed-identity-module a[href*='/in/'], a.global-nav__me-photo, a[href*='/in/']")
                    if prof_link:
                        href = await prof_link.get_attribute("href") or ""
                        if "/in/" in href and "/in/me" not in href:
                            profile["profile_url"] = href.split("?")[0].rstrip("/")
                except Exception:
                    pass

            # Fast title extraction
            try:
                raw_title = await self.page.title()
                clean_title = re.sub(r"^\(\d+\)\s*", "", raw_title).strip()
                if " | LinkedIn" in clean_title or " - LinkedIn" in clean_title:
                    cleaned = clean_title.replace(" | LinkedIn", "").replace(" - LinkedIn", "").strip()
                    if " - " in cleaned:
                        parts = cleaned.split(" - ", 1)
                        if not profile["full_name"]:
                            profile["full_name"] = parts[0].strip()
                        if not profile["headline"]:
                            profile["headline"] = parts[1].strip()
                    elif " | " in cleaned:
                        parts = cleaned.split(" | ", 1)
                        if not profile["full_name"]:
                            profile["full_name"] = parts[0].strip()
                    elif not profile["full_name"]:
                        profile["full_name"] = cleaned
            except Exception:
                pass

            # DOM Name Fallback
            if not profile["full_name"]:
                name_selectors = [
                    "h1.inline.t-24.v-align-middle.break-words",
                    "h1.text-heading-xlarge",
                    ".pv-text-details__left-panel h1",
                    "section.artdeco-card h1",
                    "div.ph5 h1",
                    "h1[aria-label]",
                    "main section h1",
                    "h1",
                ]
                for sel in name_selectors:
                    txt = await self._get_text(sel)
                    if txt and len(txt) < 100:
                        clean_n = re.sub(r"Verify in \d+ minutes|1st|2nd|3rd|\(He/Him\)|\(She/Her\)|\(They/Them\)", "", txt, flags=re.I)
                        clean_n = re.sub(r"\s+", " ", clean_n).strip()
                        if clean_n and len(clean_n) > 2 and "feed" not in clean_n.lower() and "linkedin" not in clean_n.lower():
                            profile["full_name"] = clean_n
                            break

            # DOM Headline Fallback
            if not profile["headline"]:
                headline_selectors = [
                    ".text-body-medium.break-words",
                    ".pv-text-details__left-panel .text-body-medium",
                    "div.text-body-medium",
                    "div[data-generated-suggestion-target]",
                    "section.pv-top-card div.text-body-medium",
                ]
                for sel in headline_selectors:
                    txt = await self._get_text(sel)
                    if txt and len(txt) < 200 and txt != profile["full_name"]:
                        profile["headline"] = txt
                        break

            # DOM Location Fallback
            if not profile["location"]:
                loc_selectors = [
                    ".pb2.pv-text-details__left-panel span.text-body-small",
                    "span.text-body-small.inline.t-black--light.break-words",
                    "span.text-body-small.inline",
                    ".pv-text-details__left-panel span.text-body-small",
                    "span.pv-text-details__left-panel",
                ]
                for sel in loc_selectors:
                    txt = await self._get_text(sel)
                    if txt and len(txt) < 100 and "contact info" not in txt.lower():
                        profile["location"] = txt
                        break

            # Profile photo fallback
            if not profile["profile_photo_url"]:
                photo_el = await self.page.query_selector(
                    ".pv-top-card-profile-picture__image, .profile-photo-edit__preview, img.pv-top-card-profile-picture__image--show, img[alt*='Photo of'], img[alt*='photo'], img[src*='media.licdn.com']"
                )
                if photo_el:
                    profile["profile_photo_url"] = await photo_el.get_attribute("src") or ""

            # Fallback for full_name
            if not profile["full_name"]:
                profile["full_name"] = "LinkedIn User"

            print(f"   ✅ Profile loaded: {profile['full_name']}")
            if profile["headline"]:
                print(f"   📌 {profile['headline']}")
            print(f"   🎯 Skills found: {len(profile['skills'])}")
            print(f"   💼 Experience entries: {len(profile['experience'])}")
            print(f"   🎓 Education entries: {len(profile['education'])}")

        except Exception as e:
            print(f"   ⚠️ Error reading profile: {e}")

        return profile

    async def _get_profile_url(self) -> Optional[str]:
        """Get current user's profile URL using navbar, me-dropdown, or redirects."""
        try:
            # 1. If currently already on profile page
            url = self.page.url
            if "/in/" in url and not url.endswith("/in/me") and not url.endswith("/in/me/"):
                return url.split("?")[0].rstrip("/")

            # 2. Look for profile links on page
            selectors = [
                "a.global-nav__me-photo",
                "a[href*='/in/'][aria-label*='profile']",
                "a[data-control-name='nav.settings_view_profile']",
                "a.app-aware-link[href*='/in/']",
            ]
            for sel in selectors:
                el = await self.page.query_selector(sel)
                if el:
                    href = await el.get_attribute("href") or ""
                    if "/in/" in href and not "/in/me" in href:
                        base = href.split("?")[0].rstrip("/")
                        return f"https://www.linkedin.com{base}" if base.startswith("/") else base

            # 3. Try clicking "Me" button to get "View Profile" link
            me_btn = await self.page.query_selector(
                "button.global-nav__primary-link-me-menu-trigger, .global-nav__me button, button[aria-label*='Me']"
            )
            if me_btn:
                try:
                    await me_btn.click()
                    await asyncio.sleep(1)
                    link_el = await self.page.query_selector(
                        "a[href*='/in/'].artdeco-button, a.artdeco-button[href*='/in/'], a.ember-view[href*='/in/']"
                    )
                    if link_el:
                        href = await link_el.get_attribute("href") or ""
                        if "/in/" in href and not "/in/me" in href:
                            base = href.split("?")[0].rstrip("/")
                            return f"https://www.linkedin.com{base}" if base.startswith("/") else base
                except Exception:
                    pass

            # 4. Fallback: navigate to /in/me/
            await self.page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2.5)
            url = self.page.url.split("?")[0].rstrip("/")
            if "/in/" in url and not url.endswith("/me"):
                return url

            return "https://www.linkedin.com/in/me/"
        except Exception:
            return "https://www.linkedin.com/in/me/"

    async def _get_text(self, selector: str) -> str:
        """Get cleaned text from first matching element."""
        try:
            if not self.page or self.page.is_closed():
                return ""
            el = await self.page.query_selector(selector)
            if el:
                txt = (await el.inner_text()).strip()
                return re.sub(r"\s+", " ", txt)
        except Exception:
            pass
        return ""

    async def _get_about(self) -> str:
        """Get About section text."""
        try:
            if not self.page or self.page.is_closed():
                return ""
            see_more = await self.page.query_selector(
                "#about ~ div button.inline-show-more-text__button, section:has(#about) .inline-show-more-text__button"
            )
            if see_more:
                try:
                    await see_more.click()
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

            about_el = await self.page.query_selector(
                "#about ~ div .display-flex span[aria-hidden='true'], section:has(#about) .pv-shared-text-with-see-more span, section:has(#about) div.inline-show-more-text"
            )
            if about_el:
                return (await about_el.inner_text()).strip()[:2000]
        except Exception:
            pass
        return ""

    async def _get_skills_from_page(self, canonical_url: str) -> List[str]:
        """Extract skills from main profile page or details page."""
        skills = []
        try:
            if not self.page or self.page.is_closed():
                return skills

            # Try scraping from main profile page
            skill_items = await self.page.query_selector_all(
                "section:has(#skills) ul > li, #skills ~ .pvs-list__outer-container li, div#skills ~ div li"
            )
            for item in skill_items:
                spans = await item.query_selector_all("span[aria-hidden='true']")
                for s in spans:
                    txt = (await s.inner_text()).strip()
                    if txt and len(txt) < 50 and txt not in skills and not txt.startswith("Passed"):
                        skills.append(txt)
                        break

            # If empty, try detail subpage
            if not skills and canonical_url and "/in/" in canonical_url and not canonical_url.endswith("/me"):
                detail_url = f"{canonical_url}/details/skills/"
                await self.page.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
                await self.browser.human_delay(1500, 2500)
                detail_items = await self.page.query_selector_all(
                    ".pvs-list__item--line-separated, .artdeco-list__item, li.pvs-list__item"
                )
                for item in detail_items:
                    spans = await item.query_selector_all("span[aria-hidden='true']")
                    for s in spans:
                        txt = (await s.inner_text()).strip()
                        if txt and len(txt) < 50 and txt not in skills:
                            skills.append(txt)
                            break
        except Exception:
            pass

        return skills[:30]

    async def _get_experience_from_page(self, canonical_url: str) -> List[dict]:
        """Extract experience entries."""
        experience = []
        try:
            if not self.page or self.page.is_closed():
                return experience

            exp_items = await self.page.query_selector_all(
                "section:has(#experience) ul > li, #experience ~ .pvs-list__outer-container li"
            )
            for item in exp_items[:8]:
                spans = await item.query_selector_all("span[aria-hidden='true']")
                texts = []
                for s in spans:
                    t = (await s.inner_text()).strip()
                    if t and t not in texts:
                        texts.append(t)

                if len(texts) >= 2:
                    exp = {
                        "title": texts[0] if texts else "",
                        "company": texts[1] if len(texts) > 1 else "",
                        "duration": texts[2] if len(texts) > 2 else "",
                        "description": texts[3] if len(texts) > 3 else "",
                    }
                    if exp["title"]:
                        experience.append(exp)
        except Exception:
            pass

        return experience

    async def _get_education_from_page(self, canonical_url: str) -> List[dict]:
        """Extract education entries."""
        education = []
        try:
            if not self.page or self.page.is_closed():
                return education

            edu_items = await self.page.query_selector_all(
                "section:has(#education) ul > li, #education ~ .pvs-list__outer-container li"
            )
            for item in edu_items[:6]:
                spans = await item.query_selector_all("span[aria-hidden='true']")
                texts = []
                for s in spans:
                    t = (await s.inner_text()).strip()
                    if t and t not in texts:
                        texts.append(t)

                if texts:
                    edu = {
                        "school": texts[0] if texts else "",
                        "degree": texts[1] if len(texts) > 1 else "",
                        "field": texts[2] if len(texts) > 2 else "",
                        "years": texts[3] if len(texts) > 3 else "",
                    }
                    if edu["school"]:
                        education.append(edu)
        except Exception:
            pass

        return education

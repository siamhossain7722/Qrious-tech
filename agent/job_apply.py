"""
LinkedIn Easy Apply Module
Automates the Easy Apply multi-step application process.
Supports resume upload from the dashboard.
"""
import asyncio
import random
from pathlib import Path
from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from agent.job_search import JobListing
from agent.ai_helper import AIHelper
from agent.email_sender import EmailApplier, extract_recruiter_emails


class JobApplier:
    """Handles both in-browser (Easy Apply & Direct ATS) and direct Email applications."""

    def __init__(
        self,
        browser_controller,
        ai_helper: AIHelper,
        config: dict,
        dry_run: bool = True,
        resume_path: str = "",
        applied_companies: Optional[set] = None,
        applicant_location: str = "Dhaka, Bangladesh",
    ):
        self.browser = browser_controller
        self.page: Page = browser_controller.page
        self.ai = ai_helper
        self.config = config
        self.applicant = dict(config.get("applicant", {}))
        self.applicant["location"] = applicant_location or self.applicant.get("location") or "Dhaka, Bangladesh"
        # Resume path: prefer dashboard-uploaded file over config
        self.resume_path = resume_path or self.applicant.get("resume_path", "")
        self.dry_run = dry_run
        self.applied_companies = applied_companies or set()
        self.email_applier = EmailApplier(self.config, self.ai, resume_path=self.resume_path)

    async def apply_to_job(self, job: JobListing) -> dict:
        """
        Apply to a single job via Easy Apply, External ATS/Career Site, or Direct Recruiter Email.
        Returns a result dict with status and notes.
        """
        result = {
            "job_id": job.job_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "status": "pending",
            "notes": "",
            "match_score": job.match_score,
            "match_reasons": job.match_reasons,
            "workplace_type": job.workplace_type,
            "is_easy_apply": job.is_easy_apply,
            "description": job.description,
        }

        print(f"\n📋 Processing: {job.title} at {job.company} (Match: {job.match_score}%)")

        # Duplicate company check
        if job.company and job.company.lower().strip() in self.applied_companies:
            result["status"] = "skipped"
            result["notes"] = f"Skipped: already applied to '{job.company}' previously"
            print(f"   ⏭️ Skipped: Already applied to '{job.company}' before.")
            return result

        # 1. Check for Recruiter / HR emails in job description to send direct email application
        recruiter_emails = extract_recruiter_emails(job.description)
        emailed_recruiter = False
        if recruiter_emails:
            target_email = recruiter_emails[0]
            print(f"   📧 Detected HR / Recruiter Email in description: {target_email}")
            if not self.dry_run:
                email_res = self.email_applier.send_application_email(
                    recipient_email=target_email,
                    job_title=job.title,
                    company=job.company,
                    job_description=job.description,
                )
                emailed_recruiter = email_res.get("sent", False)
                if emailed_recruiter:
                    result["notes"] = f"Emailed CV & Cover Letter directly to HR ({target_email})"

        if self.dry_run:
            result["status"] = "dry_run"
            result["notes"] = f"Dry run mode - CV Match: {job.match_score}% ({job.match_reasons})"
            print(f"   🔵 DRY RUN: Would apply to {job.title} at {job.company}")
            return result

        try:
            # Navigate to job page
            await self.page.goto(job.url, wait_until="domcontentloaded", timeout=20000)
            await self.browser.human_delay(2000, 3000)

            # Check if Easy Apply is available
            apply_status = await self._click_easy_apply()

            if apply_status == "already_applied":
                result["status"] = "already_applied"
                result["notes"] = "Already applied to this job on LinkedIn"
                return result
            elif apply_status == "clicked":
                # Handle standard LinkedIn Easy Apply modal
                success = await self._handle_application_modal(job)
                if success:
                    result["status"] = "applied"
                    notes_suffix = f" & Emailed HR ({recruiter_emails[0]})" if emailed_recruiter else ""
                    result["notes"] = f"Successfully applied via Easy Apply{notes_suffix}"
                    print(f"   🎉 SUCCESS: Applied to {job.title} at {job.company}!")
                else:
                    result["status"] = "applied" if emailed_recruiter else "failed"
                    result["notes"] = (
                        f"Emailed CV & Cover Letter directly to HR ({recruiter_emails[0]})"
                        if emailed_recruiter
                        else "Application questions could not be automatically submitted"
                    )
                    await self.browser.take_screenshot(f"failed_{job.job_id}")
            else:
                # Handle Direct / External ATS Apply button (Apply ↗)
                print(f"   🌐 External Company Site / ATS detected for {job.title}. Launching direct apply flow...")
                ext_success = await self._handle_external_apply(job)
                if ext_success or emailed_recruiter:
                    result["status"] = "applied"
                    notes_suffix = f" & Emailed HR ({recruiter_emails[0]})" if emailed_recruiter else ""
                    result["notes"] = f"Successfully submitted application on company portal{notes_suffix}"
                    print(f"   🎉 SUCCESS: Applied via company portal!")
                else:
                    result["status"] = "skipped"
                    result["notes"] = "External job (requires manual application on company site)"
                    print(f"   ℹ️ External job requires manual submission on company website.")

        except Exception as e:
            if emailed_recruiter:
                result["status"] = "applied"
                result["notes"] = f"Applied via direct email to HR ({recruiter_emails[0]}) with CV & Cover Letter"
            else:
                result["status"] = "error"
                result["notes"] = f"Error: {str(e)[:200]}"
            print(f"   ❌ Error during browser application for {job.title}: {e}")
            await self.browser.take_screenshot(f"error_{job.job_id}")

        return result

    async def _handle_external_apply(self, job: JobListing) -> bool:
        """Handle direct/external company websites and ATS forms. Returns True ONLY if submitted."""
        try:
            apply_btn = await self.page.query_selector(
                "button.jobs-apply-button, a.jobs-apply-button, button:has-text('Apply'), "
                "a:has-text('Apply'), [aria-label*='Apply to'], .jobs-apply-button--top-card, "
                "div.jobs-apply-button--top-card button"
            )
            if not apply_btn:
                return False

            # Check if already applied
            btn_text = (await apply_btn.inner_text()).lower()
            if "applied" in btn_text:
                return True

            # Attempt click and catch new ATS tab/window
            submitted_external = False
            try:
                async with self.page.context.expect_page(timeout=6000) as new_page_info:
                    await apply_btn.click()
                    await self.browser.human_delay(1500, 2500)
                ext_page = await new_page_info.value
                await ext_page.wait_for_load_state("domcontentloaded", timeout=12000)
                print(f"   🌐 Company ATS / Website opened: {ext_page.url[:80]}...")
                # Auto-fill external application form
                submitted_external = await self._fill_external_page(ext_page, job)
                await ext_page.close()
            except Exception:
                # If opened in same page or simple modal
                await self.browser.human_delay(2000, 3000)
                modal = await self.page.query_selector(".jobs-easy-apply-modal, div[role='dialog']")
                if modal:
                    return await self._handle_application_modal(job)

            return submitted_external
        except Exception as e:
            print(f"   ℹ️ Direct company apply flow: {e}")
            return False

    async def _fill_external_page(self, page, job: JobListing):
        """Auto-fill common fields on external ATS application pages (micro1, Greenhouse, Lever, Ashby, Workday, etc.)."""
        try:
            name = self.applicant.get("name", "Siam Hossain")
            parts = name.split()
            first_name = parts[0] if parts else "Siam"
            last_name = " ".join(parts[1:]) if len(parts) > 1 else "Hossain"
            email = self.config.get("applicant", {}).get("email", "") or "mdsiamh77@gmail.com"
            phone = self.applicant.get("phone", "+880 1700000000")
            location = self.applicant.get("location", "Dhaka, Bangladesh")

            await page.wait_for_timeout(1000)

            # 1. First Name
            fn_input = await page.query_selector(
                "input[placeholder*='first' i], input[id*='first_name' i], input[id*='firstName' i], "
                "input[name*='first_name' i], input[name*='firstName' i], input[autocomplete*='given-name']"
            )
            if fn_input:
                await fn_input.fill(first_name)

            # 2. Last Name
            ln_input = await page.query_selector(
                "input[placeholder*='last' i], input[id*='last_name' i], input[id*='lastName' i], "
                "input[name*='last_name' i], input[name*='lastName' i], input[autocomplete*='family-name']"
            )
            if ln_input:
                await ln_input.fill(last_name)

            # Full Name fallback
            if not fn_input and not ln_input:
                full_name_input = await page.query_selector(
                    "input[placeholder*='name' i]:not([placeholder*='company' i]), "
                    "input[id*='name' i]:not([id*='first' i]):not([id*='last' i]), "
                    "input[name*='name' i]:not([name*='first' i]):not([name*='last' i])"
                )
                if full_name_input and not (await full_name_input.input_value()):
                    await full_name_input.fill(name)

            # 3. Email
            em_input = await page.query_selector(
                "input[type='email'], input[placeholder*='email' i], input[id*='email' i], input[name*='email' i]"
            )
            if em_input:
                await em_input.fill(email)

            # 4. Phone
            ph_input = await page.query_selector(
                "input[type='tel'], input[placeholder*='phone' i], input[id*='phone' i], input[name*='phone' i], input[placeholder*='number' i]"
            )
            if ph_input:
                # Clean phone format
                await ph_input.fill("1700000000" if "+880" in (await ph_input.input_value() or "") else phone)

            # 5. LinkedIn Profile URL
            li_input = await page.query_selector(
                "input[placeholder*='linkedin' i], input[id*='linkedin' i], input[name*='linkedin' i], input[aria-label*='LinkedIn' i]"
            )
            if li_input:
                await li_input.fill("https://www.linkedin.com/in/siamhossain7722/")

            # 6. GitHub / Portfolio URL
            gh_input = await page.query_selector(
                "input[placeholder*='github' i], input[id*='github' i], input[placeholder*='portfolio' i], "
                "input[id*='portfolio' i], input[placeholder*='website' i], input[name*='website' i]"
            )
            if gh_input:
                await gh_input.fill("https://github.com/")

            # 7. Location / City
            city_input = await page.query_selector(
                "input[placeholder*='city' i], input[id*='city' i], input[placeholder*='location' i], input[id*='location' i]"
            )
            if city_input and not (await city_input.input_value()):
                await city_input.fill(location)

            # 8. Resume / CV File Upload
            if self.resume_path and Path(self.resume_path).exists():
                file_input = await page.query_selector("input[type='file']")
                if file_input:
                    await file_input.set_input_files(self.resume_path)
                    print(f"   📄 Uploaded CV on company ATS: {Path(self.resume_path).name}")

            # 9. Cover Letter / Notes
            cl_area = await page.query_selector(
                "textarea[id*='cover' i], textarea[name*='cover' i], textarea[placeholder*='cover' i], "
                "textarea[id*='message' i], textarea[placeholder*='message' i], textarea[id*='notes' i]"
            )
            if cl_area and not (await cl_area.input_value()):
                cover_letter = self.ai.generate_cover_letter(job.title, job.company, job.description)
                await cl_area.fill(cover_letter)
                print(f"   ✍️ Filled AI Cover Letter on company portal.")

            # 10. Consent / Agreement Checkboxes
            checkboxes = await page.query_selector_all("input[type='checkbox']")
            for chk in checkboxes:
                try:
                    await chk.check()
                except Exception:
                    pass

            await self.browser.human_delay(1500, 2500)

            # 11. Click Next / Continue / Submit
            action_btn = await page.query_selector(
                "button:has-text('Next'), button:has-text('Continue'), "
                "button:has-text('Submit Application'), button:has-text('Submit'), "
                "button:has-text('Apply Now'), button[type='submit'], input[type='submit']"
            )
            if action_btn:
                await action_btn.click()
                print(f"   🚀 Clicked '{await action_btn.inner_text()}' on company website!")
                await page.wait_for_timeout(3000)

                # Check if second step / final submit appeared
                final_btn = await page.query_selector(
                    "button:has-text('Submit Application'), button:has-text('Submit'), button:has-text('Finish'), button[type='submit']"
                )
                if final_btn and final_btn != action_btn:
                    await final_btn.click()
                    print(f"   🎉 Final submission clicked on company portal!")
                    await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"   ⚠️ External ATS field filling: {e}")

    async def _click_easy_apply(self) -> str:
        """
        Find and click the Easy Apply button.
        Returns:
            "clicked": Easy Apply modal was opened
            "already_applied": Position has already been applied to
            "not_found": Button not present or not an Easy Apply job
        """
        try:
            # 1. First check if page explicitly displays "Applied"
            applied_badge = await self.page.query_selector(
                ".artdeco-inline-feedback--success, .jobs-s-apply__applied-date, span:has-text('Applied on'), button:has-text('Applied')"
            )
            if applied_badge:
                badge_text = (await applied_badge.inner_text()).lower()
                if "applied" in badge_text:
                    print("   ℹ️ LinkedIn confirms: Already applied to this position.")
                    return "already_applied"

            # 2. Try strictly Easy Apply selectors
            selectors = [
                "button:has-text('Easy Apply')",
                "[aria-label*='Easy Apply']",
                ".jobs-apply-button--top-card button:has-text('Easy Apply')",
                ".jobs-s-apply button:has-text('Easy Apply')",
                "button.jobs-apply-button:has-text('Easy Apply')",
                "button.jobs-apply-button",
                ".jobs-apply-button--top-card button",
            ]

            for selector in selectors:
                try:
                    btn = await self.page.wait_for_selector(selector, timeout=2000)
                    if btn:
                        btn_text = (await btn.inner_text()).strip().lower()
                        if "applied" in btn_text:
                            return "already_applied"
                        elif "easy apply" in btn_text:
                            await btn.click()
                            await self.browser.human_delay(1500, 2500)
                            # Verify modal opened
                            modal = await self.page.wait_for_selector(
                                ".jobs-easy-apply-modal, div[role='dialog'], [data-test-modal]",
                                timeout=5000
                            )
                            if modal:
                                return "clicked"
                except PlaywrightTimeoutError:
                    continue

            return "not_found"
        except Exception as e:
            print(f"   ⚠️ Could not click Easy Apply: {e}")
            return "not_found"

    async def _handle_application_modal(self, job: JobListing) -> bool:
        """Walk through the multi-step Easy Apply modal."""
        max_steps = 10
        step = 0

        while step < max_steps:
            step += 1
            await self.browser.human_delay(1200, 2200)

            # Check if modal is still open
            modal = await self.page.query_selector(".jobs-easy-apply-modal, div[role='dialog'], [data-test-modal]")
            if not modal:
                print("   ℹ️ Modal closed.")
                return True

            # Scroll modal container to reveal all fields & footer buttons
            try:
                await self.page.evaluate(
                    "() => { const el = document.querySelector('.jobs-easy-apply-modal__content, .artdeco-modal__content, .jobs-easy-apply-modal'); if (el) el.scrollTop = el.scrollHeight; }"
                )
            except Exception:
                pass

            # Fill in form fields on current step
            await self._fill_current_step(job)
            await self.browser.human_delay(800, 1500)

            # Scroll down again after filling
            try:
                await self.page.evaluate(
                    "() => { const el = document.querySelector('.jobs-easy-apply-modal__content, .artdeco-modal__content, .jobs-easy-apply-modal'); if (el) el.scrollTop = el.scrollHeight; }"
                )
            except Exception:
                pass

            # 1. Check for Submit / Done button (last step)
            submit_btn = await self.page.query_selector(
                "button[aria-label='Submit application'], "
                "button[aria-label='Submit'], "
                "button:has-text('Submit application'), "
                "button:has-text('Submit'), "
                ".jobs-easy-apply-modal footer button.artdeco-button--primary:has-text('Submit')"
            )
            if submit_btn:
                # Uncheck follow company checkbox if present
                try:
                    follow_chk = await self.page.query_selector("label[for*='follow'], input[id*='follow-company']")
                    if follow_chk:
                        await follow_chk.click()
                except Exception:
                    pass

                await submit_btn.click()
                await self.browser.human_delay(2500, 4000)
                print(f"   🎉 Application submitted! (Step {step})")
                await self._close_modal()
                return True

            # 2. Check for Review button
            review_btn = await self.page.query_selector(
                "button[aria-label='Review your application'], "
                "button[aria-label='Review'], "
                "button:has-text('Review'), "
                ".jobs-easy-apply-modal footer button.artdeco-button--primary:has-text('Review')"
            )
            if review_btn:
                await review_btn.click()
                print(f"   ➡️ Reviewing application (Step {step + 1})...")
                continue

            # 3. Check for Next button
            next_btn = await self.page.query_selector(
                "button[aria-label='Continue to next step'], "
                "button[aria-label='Next'], "
                "button:has-text('Next'), "
                "button[data-easy-apply-next-button], "
                ".jobs-easy-apply-modal footer button.artdeco-button--primary:has-text('Next'), "
                "footer button.artdeco-button--primary"
            )
            if next_btn:
                await next_btn.click()
                print(f"   ➡️ Moving to step {step + 1}...")
            else:
                print(f"   ⚠️ No next/submit button found at step {step}.")
                await self._close_modal()
                return False

        return False

    async def _fill_current_step(self, job: JobListing):
        """Fill all visible form fields in the current application step."""
        # Upload resume if file input present
        await self._upload_resume()

        # Location / City (e.g. Dhaka, Bangladesh)
        await self._fill_location()

        # Phone number
        await self._fill_phone()

        # Cover letter / text areas (AI Generated)
        await self._fill_cover_letter_fields(job)

        # Answer screening questions (text and numeric)
        await self._answer_questions(job)

        # Handle radio buttons and checkboxes
        await self._handle_radio_buttons()

        # Handle dropdowns
        await self._handle_dropdowns()

    async def _fill_location(self):
        """Fill city / location field with auto-complete typeahead handling."""
        loc = self.applicant.get("location", "") or "Dhaka, Bangladesh"
        city_name = loc.split(",")[0].strip() if "," in loc else loc.strip()
        try:
            city_inputs = await self.page.query_selector_all(
                "input[id*='city'], input[name*='city'], input[aria-label*='City'], "
                "input[id*='location'], input[name*='location'], input[aria-label*='Location'], "
                "input[id*='address'], input[name*='address'], input[aria-label*='Address']"
            )
            for inp in city_inputs:
                current_val = (await inp.input_value() or "").strip()
                if not current_val:
                    await inp.click()
                    await self.page.keyboard.type(city_name, delay=40)
                    await asyncio.sleep(1.0)

                    # Look for typeahead auto-complete dropdown suggestion
                    suggestion = await self.page.query_selector(
                        ".basic-typeahead__selectable-list li, "
                        ".search-typeahead-v2__hit, "
                        "ul[role='listbox'] li, "
                        ".typeahead-results li, "
                        "div[role='option'], "
                        "li.basic-typeahead__selectable"
                    )
                    if suggestion:
                        await suggestion.click()
                        await asyncio.sleep(0.5)
                        print(f"   📍 Selected location: {loc}")
                    else:
                        await self.page.keyboard.press("ArrowDown")
                        await asyncio.sleep(0.3)
                        await self.page.keyboard.press("Enter")
        except Exception as e:
            print(f"   ⚠️ Location auto-complete: {e}")

    async def _fill_phone(self):
        """Fill phone number field if present."""
        phone = self.applicant.get("phone", "")
        if not phone:
            return
        try:
            phone_inputs = await self.page.query_selector_all(
                "input[id*='phone'], input[name*='phone'], input[aria-label*='Phone']"
            )
            for inp in phone_inputs:
                current_val = await inp.get_attribute("value") or ""
                if not current_val:
                    await self.browser.human_type(inp, phone)
        except Exception:
            pass

    async def _fill_cover_letter_fields(self, job: JobListing):
        """Fill any cover letter / additional info text areas with personalized AI cover letter."""
        try:
            textareas = await self.page.query_selector_all(
                "textarea[id*='cover'], textarea[name*='cover'], textarea[aria-label*='cover'], "
                "textarea[id*='additional'], textarea[name*='additional'], textarea[aria-label*='additional'], "
                "textarea[id*='summary'], textarea[aria-label*='summary'], textarea[id*='note'], "
                "textarea[aria-label*='note'], textarea[placeholder*='cover'], textarea[placeholder*='note']"
            )
            for textarea in textareas:
                current_val = await textarea.input_value() or ""
                if not current_val.strip():
                    cover_letter = self.ai.generate_cover_letter(
                        job.title, job.company, job.description
                    )
                    await textarea.fill(cover_letter)
                    print(f"   ✍️ AI Cover Letter generated & filled for {job.title} at {job.company}")
                    await asyncio.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️ Cover letter auto-fill: {e}")

    async def _answer_questions(self, job: JobListing):
        """Find and answer text and numeric screening questions."""
        try:
            inputs = await self.page.query_selector_all(
                ".jobs-easy-apply-modal input[type='text'], "
                ".jobs-easy-apply-modal input[type='number'], "
                ".jobs-easy-apply-modal textarea, "
                "div[role='dialog'] input[type='text'], "
                "div[role='dialog'] input[type='number'], "
                "div[role='dialog'] textarea"
            )
            for inp in inputs:
                try:
                    inp_id = await inp.get_attribute("id") or ""
                    inp_type = await inp.get_attribute("type") or "text"
                    current_val = (await inp.input_value() or "").strip()

                    # Find associated label / question text
                    label_text = ""
                    if inp_id:
                        label_el = await self.page.query_selector(f"label[for='{inp_id}']")
                        if label_el:
                            label_text = (await label_el.inner_text()).strip()

                    if not label_text:
                        aria_label = await inp.get_attribute("aria-label") or ""
                        if aria_label:
                            label_text = aria_label

                    if not label_text:
                        parent_group = await inp.query_selector("xpath=ancestor::*[contains(@class, 'fb-dash-form-element') or contains(@class, 'jobs-easy-apply-form-section__group')]")
                        if parent_group:
                            label_el = await parent_group.query_selector("label, span.fb-dash-form-element__label")
                            if label_el:
                                label_text = (await label_el.inner_text()).strip()

                    q_lower = label_text.lower()

                    # If numeric or asks about years of experience
                    if inp_type == "number" or "years" in q_lower or "how many" in q_lower:
                        years = str(self.applicant.get("years_of_experience", "3"))
                        if not current_val or current_val in ["0", "1"]:
                            await inp.fill(years)
                    elif not current_val:
                        answer = self.ai.answer_screening_question(label_text, is_numeric=False)
                        await self.browser.human_type(inp, answer)
                except Exception:
                    continue
        except Exception:
            pass

    async def _handle_radio_buttons(self):
        """Intelligently answer yes/no radio questions based on screening context."""
        try:
            # Query all radio group containers in the modal
            radio_groups = await self.page.query_selector_all(
                "fieldset[data-test-form-builder-radio-button-form-component], "
                "fieldset, .fb-radio-buttons, .jobs-easy-apply-form-section__group:has(input[type='radio']), "
                ".fb-dash-form-element:has(input[type='radio']), "
                "div:has(> input[type='radio'])"
            )
            for group in radio_groups:
                try:
                    # Get question text from legend or label
                    legend_el = await group.query_selector("legend, label, span.fb-dash-form-element__label")
                    legend_text = (await legend_el.inner_text()).lower() if legend_el else ""

                    # Determine optimal target choice:
                    # 1. Visa & sponsorship questions require "No"
                    if any(k in legend_text for k in ["sponsorship", "require visa", "require sponsorship", "visa status"]):
                        target_choice = "no"
                    # 2. Negative questions (conviction, termination) require "No"
                    elif any(k in legend_text for k in ["convict", "criminal", "terminated", "fired"]):
                        target_choice = "no"
                    # 3. Work authorization, remote, experience, driver's license, background check require "Yes"
                    else:
                        target_choice = "yes"

                    # Find options inside this group
                    options = await group.query_selector_all("label, input[type='radio']")
                    clicked = False
                    for opt in options:
                        opt_text = (await opt.inner_text()).strip().lower() if await opt.evaluate("el => el.tagName.toLowerCase()") == "label" else (await opt.get_attribute("value") or "").lower()
                        if (target_choice == "yes" and "yes" in opt_text) or (target_choice == "no" and "no" in opt_text):
                            await opt.click()
                            clicked = True
                            await asyncio.sleep(0.2)
                            break

                    # Fallback: if not clicked, click Yes option or first available radio option
                    if not clicked:
                        fallback_opt = await group.query_selector("label:has-text('Yes'), input[value='Yes'], input[value='yes']")
                        if fallback_opt:
                            await fallback_opt.click()
                        else:
                            first_radio = await group.query_selector("label, input[type='radio']")
                            if first_radio:
                                await first_radio.click()
                except Exception:
                    continue
        except Exception:
            pass

    async def _handle_dropdowns(self):
        """Handle select dropdown fields with intelligent persona choices."""
        try:
            selects = await self.page.query_selector_all(
                "select.fb-form-element__input, select[id*='select'], select, div[data-test-form-builder-select-form-component] select"
            )
            for sel in selects:
                try:
                    # Get question / label for context
                    sel_id = await sel.get_attribute("id") or ""
                    label_el = await self.page.query_selector(f"label[for='{sel_id}']") if sel_id else None
                    if not label_el:
                        label_el = await sel.query_selector("xpath=ancestor::*[contains(@class, 'fb-dash-form-element') or contains(@class, 'jobs-easy-apply-form-section__group')]//label")
                    label_text = (await label_el.inner_text()).lower() if label_el else ""

                    current_val = await sel.input_value()
                    options = await sel.query_selector_all("option")
                    if len(options) <= 1:
                        continue

                    # Extract all option values and texts
                    opt_data = []
                    for opt in options:
                        val = await opt.get_attribute("value") or ""
                        txt = (await opt.inner_text()).strip()
                        opt_data.append((val, txt, txt.lower()))

                    # 1. English / Language proficiency: Select highest proficiency (Professional / Fluent / Native)
                    if any(k in label_text for k in ["english", "proficiency", "language"]):
                        chosen_val = None
                        for pref in ["native", "fluent", "professional", "advanced", "conversational"]:
                            for val, txt, txt_lower in opt_data:
                                if pref in txt_lower and val and val != "Select an option":
                                    chosen_val = val
                                    break
                            if chosen_val:
                                break
                        if chosen_val:
                            await sel.select_option(value=chosen_val)
                            continue

                    # 2. Sponsorship / Visa: Select "No"
                    elif any(k in label_text for k in ["sponsorship", "visa"]):
                        for val, txt, txt_lower in opt_data:
                            if "no" in txt_lower and val and val != "Select an option":
                                await sel.select_option(value=val)
                                break
                        continue

                    # 3. Work authorization / Experience / Remote / Degree
                    elif any(k in label_text for k in ["authorized", "remote", "eligible", "experience", "degree", "education"]):
                        for val, txt, txt_lower in opt_data:
                            if any(w in txt_lower for w in ["yes", "bachelor", "master", "3", "4", "5"]) and val and val != "Select an option":
                                await sel.select_option(value=val)
                                break
                        continue

                    # Default fallback: pick first valid option if currently unselected or empty
                    if not current_val or current_val == "Select an option" or current_val == "":
                        for val, txt, txt_lower in opt_data[1:]:
                            if val and val != "Select an option":
                                await sel.select_option(value=val)
                                break
                except Exception:
                    continue
        except Exception:
            pass

    async def _close_modal(self):
        """Close the application modal after submission."""
        try:
            close_btn = await self.page.query_selector(
                "button[aria-label='Dismiss'], button[aria-label='Close']"
            )
            if close_btn:
                await close_btn.click()
        except Exception:
            pass

    async def _upload_resume(self):
        """Upload the active resume PDF if a file input is found on current step."""
        if not self.resume_path:
            return

        resume_file = Path(self.resume_path)
        if not resume_file.exists():
            print(f"   ⚠️ Resume file not found: {self.resume_path}")
            return

        try:
            # Look for file upload inputs in the modal
            file_inputs = await self.page.query_selector_all(
                ".jobs-easy-apply-modal input[type='file'], "
                "[data-test-modal] input[type='file']"
            )
            for file_input in file_inputs:
                # Only upload if no file is already attached
                is_visible = await file_input.is_visible()
                if not is_visible:
                    # Make visible to interact
                    await self.page.evaluate(
                        "el => { el.style.display = 'block'; el.style.opacity = '1'; }",
                        file_input
                    )
                await file_input.set_input_files(str(resume_file))
                await self.browser.human_delay(1000, 2000)
                print(f"   📄 Resume uploaded: {resume_file.name}")
                break  # Upload once per step
        except Exception as e:
            print(f"   ⚠️ Could not upload resume: {e}")

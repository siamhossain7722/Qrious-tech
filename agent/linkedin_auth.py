"""
LinkedIn Authentication Module
Handles login, session management, and persistent browser authentication.
Supports standard credentials, manual 2FA, and Google Sign-In.
"""
import os
import asyncio
from dotenv import load_dotenv
from playwright.async_api import Page

load_dotenv()

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_HOME_URL = "https://www.linkedin.com/feed/"


class LinkedInAuth:
    """Manages LinkedIn login and session state."""

    def __init__(self, browser_controller):
        self.browser = browser_controller
        self.page: Page = browser_controller.page
        self.email = os.getenv("LINKEDIN_EMAIL", "")
        self.password = os.getenv("LINKEDIN_PASSWORD", "")

    async def is_logged_in(self) -> bool:
        """Check if user is already logged in by verifying DOM and URL."""
        try:
            if not self.page or self.page.is_closed():
                return False

            url = self.page.url

            # If currently already on LinkedIn profile or feed
            if "/in/" in url or "/feed" in url or "/mynetwork" in url or "/jobs" in url:
                if not any(blocked in url for blocked in ["login", "checkpoint", "authwall", "challenge", "signup"]):
                    return True

            await self.page.goto(LINKEDIN_HOME_URL, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

            url = self.page.url
            if any(blocked in url for blocked in ["login", "checkpoint", "authwall", "challenge", "signup"]):
                return False

            # Verify actual logged-in user interface elements
            logged_in_el = await self.page.query_selector(
                ".global-nav__me, .global-nav__me-photo, button.global-nav__primary-link-me-menu-trigger, #global-nav-search, nav[aria-label='Primary Navigation'], .pv-top-card"
            )
            if logged_in_el or "/in/" in url or "/feed" in url:
                print("✅ Already logged in (session active).")
                return True

            return False
        except Exception:
            return False

    async def login(self) -> bool:
        """Perform LinkedIn login with fallback to user completion."""
        print("🔐 Logging in to LinkedIn...")

        # Check if already authenticated
        if await self.is_logged_in():
            return True

        await self.page.goto(LINKEDIN_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        await self.browser.human_delay(1500, 2500)

        if self.email and self.password:
            try:
                # Fill email
                email_field = self.page.locator("#username")
                if await email_field.is_visible():
                    await self.browser.human_type(email_field, self.email)
                    await self.browser.human_delay(300, 800)

                # Fill password
                password_field = self.page.locator("#password")
                if await password_field.is_visible():
                    await self.browser.human_type(password_field, self.password)
                    await self.browser.human_delay(500, 1000)

                # Click sign in
                submit_btn = self.page.locator('[type="submit"]')
                if await submit_btn.is_visible():
                    await submit_btn.click()
                    await self.browser.human_delay(3000, 5000)
            except Exception as e:
                print(f"⚠️ Auto-fill info: {e}")

        # Check if user needs to complete login / Google Sign In / 2FA manually
        return await self.wait_for_user_login(timeout_seconds=90)

    async def wait_for_user_login(self, timeout_seconds: int = 120) -> bool:
        """
        Wait for the user to complete login in the visible browser window.
        Supports standard login, 2FA, OTP, and Sign in with Google.
        """
        print(f"🌐 Waiting up to {timeout_seconds}s for LinkedIn / Google login in browser window...")
        for i in range(timeout_seconds // 2):
            try:
                if not self.page or self.page.is_closed():
                    return False

                url = self.page.url

                # If URL is NOT a login / challenge / authwall page
                if not any(blocked in url for blocked in ["login", "checkpoint", "authwall", "challenge", "signup"]):
                    logged_in_el = await self.page.query_selector(
                        ".global-nav__me, .global-nav__me-photo, #global-nav-search, button[aria-label*='Me'], nav.global-nav, .pv-top-card, div.ph5"
                    )
                    if logged_in_el or "/in/" in url or "/feed" in url or "/mynetwork" in url or "/jobs" in url:
                        print(f"🎉 Login completed successfully! (URL: {url})")
                        await self.browser.save_session()
                        return True

                await asyncio.sleep(2)
            except Exception:
                await asyncio.sleep(2)

        # Final verification
        return await self.is_logged_in()

    async def ensure_logged_in(self) -> bool:
        """Ensure user is logged in; trigger login flow if needed."""
        if await self.is_logged_in():
            return True
        return await self.login()

    async def logout(self):
        """Log out and clear session."""
        try:
            await self.page.goto("https://www.linkedin.com/m/logout/")
            await self.browser.clear_session()
            print("👋 Logged out from LinkedIn.")
        except Exception:
            pass

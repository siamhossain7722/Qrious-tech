"""
LinkedIn Job Application Agent - Browser Controller
Uses Playwright for anti-detection browser automation.
"""
import asyncio
import random
import os
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserController:
    """Manages a Playwright browser instance with persistent profile & anti-detection."""

    def __init__(self, headless: bool = False, slow_mo_ms: int = 800, profile_dir: Optional[str] = None):
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.profile_dir = Path(profile_dir) if profile_dir else Path("data/browser_profile")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.session_path = Path("data/linkedin_session.json")
        self.screenshot_dir = Path("data/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def launch(self):
        """Launch the persistent browser with anti-detection and Google Sign-In support."""
        self.playwright = await async_playwright().start()

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--start-maximized",
        ]

        # 1. Try launching with system Google Chrome for full Google Login & native bot bypass
        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir.resolve()),
                headless=self.headless,
                slow_mo=self.slow_mo_ms,
                channel="chrome",
                args=args,
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
        except Exception:
            # 2. Fallback to bundled Chromium
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir.resolve()),
                headless=self.headless,
                slow_mo=self.slow_mo_ms,
                args=args,
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )

        # Mask automation signals
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)

        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        print(f"✅ Browser launched successfully (Profile: {self.profile_dir.name}).")
        return self.page

    async def save_session(self):
        """Persist login cookies/session to disk."""
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        await self.context.storage_state(path=str(self.session_path))
        print("💾 Session saved.")

    async def clear_session(self):
        """Remove saved session (force fresh login)."""
        if self.session_path.exists():
            self.session_path.unlink()
            print("🗑️ Session cleared.")

    async def take_screenshot(self, name: str = "screenshot"):
        """Take a screenshot for debugging."""
        path = self.screenshot_dir / f"{name}.png"
        await self.page.screenshot(path=str(path))
        print(f"📸 Screenshot saved: {path}")
        return str(path)

    async def human_type(self, locator, text: str):
        """Type text with random delays to mimic human typing."""
        await locator.click()
        await locator.clear()
        for char in text:
            await locator.type(char, delay=random.randint(50, 150))

    async def human_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """Random human-like delay between actions."""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def scroll_slowly(self, pixels: int = 500):
        """Scroll page like a human."""
        try:
            if not self.page or self.page.is_closed():
                return
            steps = random.randint(3, 6)
            per_step = pixels // steps
            for _ in range(steps):
                if self.page and not self.page.is_closed():
                    await self.page.evaluate(f"window.scrollBy(0, {per_step})")
                    await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass

    async def close(self):
        """Close browser context and clean up."""
        try:
            if self.context:
                await self.context.close()
            elif self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        print("🔒 Browser closed.")

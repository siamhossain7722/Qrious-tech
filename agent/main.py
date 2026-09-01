"""
Main Agent Orchestrator
Coordinates browser, auth, search, and apply modules.
"""
import asyncio
import sys
import yaml
import json
from pathlib import Path
from typing import List, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from agent.browser import BrowserController
from agent.linkedin_auth import LinkedInAuth
from agent.job_search import JobSearcher, JobListing
from agent.job_apply import JobApplier
from agent.ai_helper import AIHelper
from agent.cv_matcher import CVMatcher


def load_config(config_path: str = "config/settings.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


class LinkedInAgent:
    """
    Main orchestrator for the LinkedIn Job Application Agent.
    
    Usage:
        agent = LinkedInAgent()
        asyncio.run(agent.run())
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = load_config(config_path)
        agent_cfg = self.config.get("agent", {})
        self.headless = agent_cfg.get("headless", False)
        self.slow_mo = agent_cfg.get("slow_mo_ms", 800)
        self.dry_run = agent_cfg.get("dry_run", True)

        self._resume_path = ""
        self._account_profile = {}
        self._workplace_type = ""
        self._min_match_score = 50
        self._custom_keywords = []
        self._profile_dir = ""
        self._location = ""
        self._max_applications = 30
        self._apply_type = "all"
        self._applied_companies = set()
        self._applicant_location = "Dhaka, Bangladesh"

        self.browser_ctrl = None
        self.results: List[dict] = []

    async def run(self) -> List[dict]:
        """Run the full agent: login → search → apply → return results."""
        print("=" * 60)
        print("🤖 LinkedIn Job Application Agent Starting...")
        print(f"   Mode: {'🔵 DRY RUN (no real applications)' if self.dry_run else '🟢 LIVE (will submit applications)'}")
        if self._workplace_type:
            print(f"   Workplace: {self._workplace_type.replace('_', ' ').title()}")
        if self._location:
            print(f"   Location Scope: {self._location.title()}")
        print(f"   Target Applications: {self._max_applications}")
        print(f"   Apply Scope: {'All Apply Types (Easy Apply + Direct Apply)' if self._apply_type == 'all' else 'Easy Apply Only'}")
        print("=" * 60)

        # Apply runtime overrides to search config
        if self._workplace_type:
            self.config.setdefault("job_search", {})["workplace_type"] = self._workplace_type
        if self._min_match_score:
            self.config.setdefault("job_search", {})["min_match_score"] = self._min_match_score
        if self._custom_keywords:
            self.config.setdefault("job_search", {})["keywords"] = self._custom_keywords
        if self._location:
            self.config.setdefault("job_search", {})["location"] = self._location
        if self._max_applications:
            self.config.setdefault("job_search", {})["max_applications_per_run"] = self._max_applications
        # Load database records of previously applied/processed jobs
        try:
            from dashboard.models import JobApplication
            for ja in JobApplication.objects.all():
                if ja.company:
                    self._applied_companies.add(ja.company.lower().strip())
        except Exception:
            pass

        if self._applied_companies:
            self.config.setdefault("job_search", {})["applied_companies"] = list(self._applied_companies)

        profile_dir = self._profile_dir or self.config.get("agent", {}).get("profile_dir", "data/browser_profile")
        self.browser_ctrl = BrowserController(
            headless=self.headless,
            slow_mo_ms=self.slow_mo,
            profile_dir=profile_dir,
        )

        try:
            page = await self.browser_ctrl.launch()

            # Authentication
            auth = LinkedInAuth(self.browser_ctrl)
            logged_in = await auth.ensure_logged_in()
            if not logged_in:
                print("❌ Could not log in to LinkedIn. Aborting.")
                return []

            # AI Helper initialized with Siam Hossain's account profile & skills
            ai = AIHelper(self.config, account_profile=self._account_profile)

            # Initialize CV Matcher
            cv_matcher = CVMatcher(
                resume_path=self._resume_path,
                account_profile=self._account_profile,
                config=self.config,
                ai_helper=ai,
            )

            # Job Search with CV matching
            searcher = JobSearcher(self.browser_ctrl, self.config, cv_matcher=cv_matcher)
            jobs = await searcher.search()

            if not jobs:
                print("📭 No jobs found matching your criteria.")
                return []

            print(f"\n🎯 Processing {len(jobs)} job(s)...")

            # Apply to jobs
            applier = JobApplier(
                browser_controller=self.browser_ctrl,
                ai_helper=ai,
                config=self.config,
                dry_run=self.dry_run,
                resume_path=self._resume_path,
                applied_companies=self._applied_companies,
                applicant_location=self._applicant_location,
            )

            for job in jobs:
                # Optionally fetch full job details for better cover letters and description
                job = await searcher.get_job_details(job)
                result = await applier.apply_to_job(job)
                self.results.append(result)
                # Human delay between applications
                await self.browser_ctrl.human_delay(2000, 4000)

            # Save results
            self._save_results()

            # Print summary
            self._print_summary()

        except Exception as e:
            print(f"\n❌ Agent error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.browser_ctrl:
                await self.browser_ctrl.close()

        return self.results

    def _save_results(self):
        """Save results to JSON log file."""
        Path("data").mkdir(exist_ok=True)
        results_path = Path("data/results.json")

        # Load existing results
        existing = []
        if results_path.exists():
            with open(results_path) as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []

        existing.extend(self.results)

        with open(results_path, "w") as f:
            json.dump(existing, f, indent=2, default=str)

        print(f"\n💾 Results saved to {results_path}")

    def _print_summary(self):
        """Print a summary of the run."""
        statuses = {}
        for r in self.results:
            s = r.get("status", "unknown")
            statuses[s] = statuses.get(s, 0) + 1

        print("\n" + "=" * 60)
        print("📊 RUN SUMMARY")
        print("=" * 60)
        for status, count in statuses.items():
            emoji = {
                "applied": "✅",
                "dry_run": "🔵",
                "skipped": "⏭️",
                "failed": "❌",
                "error": "💥",
                "already_applied": "ℹ️",
            }.get(status, "❓")
            print(f"   {emoji} {status.replace('_', ' ').title()}: {count}")
        print("=" * 60)


# CLI entry point
if __name__ == "__main__":
    agent = LinkedInAgent()
    asyncio.run(agent.run())

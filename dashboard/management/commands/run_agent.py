"""
Django management command to run the LinkedIn agent from CLI.

Usage:
    python manage.py run_agent               # Dry run (safe)
    python manage.py run_agent --live        # Actually apply to jobs
    python manage.py run_agent --config path/to/settings.yaml
"""
import asyncio
import json
from datetime import datetime
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError

from dashboard.models import JobApplication, AgentRun


class Command(BaseCommand):
    help = "Run the LinkedIn Job Application Agent"

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            default=False,
            help="Actually submit applications (default: dry run only)",
        )
        parser.add_argument(
            "--config",
            type=str,
            default="config/settings.yaml",
            help="Path to the agent config file (default: config/settings.yaml)",
        )

    def handle(self, *args, **options):
        dry_run = not options["live"]
        config_path = options["config"]

        mode = "DRY RUN" if dry_run else "LIVE"
        self.stdout.write(
            self.style.SUCCESS(f"\n🤖 Starting LinkedIn Agent [{mode} MODE]")
        )

        if not dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  LIVE MODE: This will submit real job applications!"
                )
            )
            confirm = input("Are you sure? Type 'yes' to continue: ")
            if confirm.lower() != "yes":
                self.stdout.write("Aborted.")
                return

        # Create run record
        run = AgentRun.objects.create(dry_run=dry_run, status="running")

        async def _run():
            from agent.main import LinkedInAgent
            agent = LinkedInAgent(config_path=config_path)
            agent.dry_run = dry_run
            return await agent.run()

        try:
            results = asyncio.run(_run())

            # Save results to database
            applied_count = 0
            for result in results:
                job_id = result.get("job_id", "")
                if job_id:
                    _, created = JobApplication.objects.update_or_create(
                        job_id=job_id,
                        defaults={
                            "title": result.get("title", ""),
                            "company": result.get("company", ""),
                            "url": result.get("url", ""),
                            "status": result.get("status", "pending"),
                            "notes": result.get("notes", ""),
                        },
                    )
                if result.get("status") == "applied":
                    applied_count += 1

            # Update run record
            run.status = "completed"
            run.finished_at = timezone.now()
            run.total_found = len(results)
            run.total_applied = applied_count
            run.total_skipped = sum(1 for r in results if r.get("status") == "skipped")
            run.total_failed = sum(1 for r in results if r.get("status") in ("failed", "error"))
            run.save()

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Done! Found: {len(results)} | Applied: {applied_count}"
            ))

        except Exception as e:
            run.status = "failed"
            run.log_output = str(e)
            run.finished_at = timezone.now()
            run.save()
            raise CommandError(f"Agent failed: {e}")

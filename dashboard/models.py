import json
import base64
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class JobApplication(models.Model):
    """Tracks every job the agent has processed."""

    STATUS_CHOICES = [
        ("applied", "Applied ✅"),
        ("dry_run", "Dry Run 🔵"),
        ("skipped", "Skipped ⏭️"),
        ("failed", "Failed ❌"),
        ("error", "Error 💥"),
        ("already_applied", "Already Applied ℹ️"),
        ("pending", "Pending ⏳"),
        ("interview", "Interview 🎉"),
        ("rejected", "Rejected 😔"),
        ("offer", "Offer Received 🏆"),
    ]

    job_id = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications', null=True, blank=True)
    title = models.CharField(max_length=300)
    company = models.CharField(max_length=300)
    location = models.CharField(max_length=200, blank=True)
    url = models.URLField(max_length=1000, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    cover_letter = models.TextField(blank=True)
    description = models.TextField(blank=True)
    applicant_count = models.CharField(max_length=100, blank=True)
    is_easy_apply = models.BooleanField(default=False)
    workplace_type = models.CharField(max_length=50, blank=True, default="", help_text="Remote / On-site / Hybrid")
    date_applied = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_applied"]

    def __str__(self):
        return f"{self.title} @ {self.company} [{self.status}] ({self.match_score}%)"

    @property
    def status_color(self):
        colors = {
            "applied": "success",
            "dry_run": "info",
            "skipped": "secondary",
            "failed": "danger",
            "error": "danger",
            "already_applied": "warning",
            "pending": "warning",
            "interview": "success",
            "rejected": "danger",
            "offer": "success",
        }
        return colors.get(self.status, "secondary")


class AgentRun(models.Model):
    """Records each agent run session."""

    STATUS_CHOICES = [
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_runs', null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    dry_run = models.BooleanField(default=True)
    keywords = models.CharField(max_length=500, blank=True)
    total_found = models.IntegerField(default=0)
    total_applied = models.IntegerField(default=0)
    total_skipped = models.IntegerField(default=0)
    total_failed = models.IntegerField(default=0)
    log_output = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Run {self.id} - {self.started_at.strftime('%Y-%m-%d %H:%M')} [{self.status}]"


def _obfuscate(text: str) -> str:
    """Simple reversible obfuscation for dashboard display (NOT encryption)."""
    return base64.b64encode(text.encode()).decode()


def _deobfuscate(token: str) -> str:
    try:
        return base64.b64decode(token.encode()).decode()
    except Exception:
        return token


class LinkedInAccount(models.Model):
    """Stores LinkedIn account credentials and scraped profile data."""

    STATUS_CHOICES = [
        ("active", "Active ✅"),
        ("needs_verification", "Needs Verification ⚠️"),
        ("inactive", "Inactive ❌"),
        ("syncing", "Syncing 🔄"),
    ]

    # Credentials
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='linkedin_accounts', null=True, blank=True)
    email = models.EmailField()
    _password_token = models.TextField(db_column="password_token")  # obfuscated
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="active")


    # Scraped profile data
    full_name = models.CharField(max_length=300, blank=True)
    headline = models.CharField(max_length=500, blank=True)
    location = models.CharField(max_length=200, blank=True)
    profile_url = models.URLField(max_length=500, blank=True)
    profile_photo_url = models.URLField(max_length=1000, blank=True)
    about = models.TextField(blank=True)
    skills = models.TextField(blank=True)          # JSON list of skill names
    experience = models.TextField(blank=True)      # JSON list of experience dicts
    education = models.TextField(blank=True)       # JSON list of education dicts
    connections = models.CharField(max_length=50, blank=True)

    # Session file path (for persistent login)
    session_file = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name or self.email} ({self.status})"

    @property
    def password(self) -> str:
        return _deobfuscate(self._password_token)

    @password.setter
    def password(self, raw_password: str):
        self._password_token = _obfuscate(raw_password)

    def get_skills_list(self) -> list:
        if self.skills:
            try:
                return json.loads(self.skills)
            except Exception:
                return []
        return []

    def get_experience_list(self) -> list:
        if self.experience:
            try:
                return json.loads(self.experience)
            except Exception:
                return []
        return []

    def get_education_list(self) -> list:
        if self.education:
            try:
                return json.loads(self.education)
            except Exception:
                return []
        return []

    @property
    def display_skills(self) -> str:
        return ", ".join(self.get_skills_list()[:10])


def resume_upload_path(instance, filename):
    """Store resumes in media/resumes/<user_id>/<filename>."""
    uid = instance.user_id if instance.user_id else 'general'
    return f"resumes/{uid}/{filename}"


class Resume(models.Model):
    """Uploaded CV/Resume PDF files."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes', null=True, blank=True)
    account = models.ForeignKey(
        LinkedInAccount,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="resumes",
        help_text="LinkedIn account this resume belongs to (optional)",
    )
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to=resume_upload_path)
    is_active = models.BooleanField(default=False)
    file_size_kb = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        active = " [ACTIVE]" if self.is_active else ""
        return f"{self.name}{active}"

    def save(self, *args, **kwargs):
        # Compute file size on save
        if self.file:
            try:
                self.file_size_kb = self.file.size // 1024
            except Exception:
                pass

        # Only one resume can be active at a time
        if self.is_active:
            Resume.objects.exclude(pk=self.pk).update(is_active=False)

        super().save(*args, **kwargs)

    @property
    def filename(self):
        import os
        return os.path.basename(self.file.name) if self.file else ""

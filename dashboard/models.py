import json
import base64
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


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
    uid = getattr(instance, 'user_id', 'general')
    return f"resumes/{uid}/{filename}"


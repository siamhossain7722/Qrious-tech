from django.contrib import admin
from .models import JobApplication, AgentRun, LinkedInAccount, Resume


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "status", "is_easy_apply", "date_applied"]
    list_filter = ["status", "is_easy_apply"]
    search_fields = ["title", "company", "location"]
    list_editable = ["status"]
    readonly_fields = ["date_applied", "date_updated"]
    ordering = ["-date_applied"]


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ["id", "started_at", "status", "dry_run", "total_found", "total_applied"]
    list_filter = ["status", "dry_run"]
    readonly_fields = ["started_at", "finished_at"]
    ordering = ["-started_at"]


@admin.register(LinkedInAccount)
class LinkedInAccountAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "status", "last_synced", "created_at"]
    list_filter = ["status", "is_active"]
    search_fields = ["email", "full_name", "headline"]
    readonly_fields = ["created_at", "last_synced", "_password_token"]
    ordering = ["-created_at"]


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["name", "account", "is_active", "file_size_kb", "uploaded_at"]
    list_filter = ["is_active"]
    list_editable = ["is_active"]
    ordering = ["-uploaded_at"]


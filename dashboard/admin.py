from django.contrib import admin
from .models import LinkedInAccount


@admin.register(LinkedInAccount)
class LinkedInAccountAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "status", "last_synced", "created_at"]
    list_filter = ["status", "is_active"]
    search_fields = ["email", "full_name", "headline"]
    readonly_fields = ["created_at", "last_synced", "_password_token"]
    ordering = ["-created_at"]



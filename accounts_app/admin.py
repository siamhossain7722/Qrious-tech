from django.contrib import admin
from .models import UserProfile, Subscription, UsageLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'company', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'company']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'cancel_at_period_end', 'created_at']
    list_filter = ['plan', 'status']
    list_editable = ['plan', 'status']
    search_fields = ['user__email']


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'created_at']
    list_filter = ['event']
    search_fields = ['user__email']

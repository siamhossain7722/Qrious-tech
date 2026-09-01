"""
accounts_app signals — create profile & subscription on user creation.
"""
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile, Subscription


@receiver(post_save, sender=User)
def create_user_profile_and_subscription(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        Subscription.objects.get_or_create(
            user=instance,
            defaults={'plan': 'free', 'status': 'active'}
        )

        try:
            from .views import create_notification
            # Send Welcome notification to the new user
            create_notification(
                user=instance,
                title="👋 Welcome to Qrious Tech Academy!",
                message="Welcome aboard! Access your student dashboard, video classroom, tuition payment history, and AI job automation tools.",
                notification_type="system",
                category="success",
                link="/student/dashboard/"
            )

            # Send registration alert to Super Admins
            create_notification(
                user=None,
                title=f"👤 New User Registered: {instance.email}",
                message=f"New user '{instance.get_full_name() or instance.email}' has joined Qrious Tech Academy.",
                notification_type="system",
                category="info",
                link="/admin-users/"
            )
        except Exception as e:
            print(f"Error sending signup notification: {e}")

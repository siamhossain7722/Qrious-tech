import os
from django.contrib.auth.models import User
from django.core.management import call_command

_setup_done = False

class AutoSetupMiddleware:
    """Middleware that automatically runs database migrations and seeds Super Admin on first request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global _setup_done
        if not _setup_done:
            _setup_done = True
            try:
                # Automatically run database migrations to create any missing tables (e.g. accounts_app_courseassignment) on Vercel remote MySQL DB
                call_command('migrate', interactive=False)
            except Exception as ex:
                print(f"AutoSetupMiddleware migration notice: {ex}")

            try:
                # Seed Superuser and Default CourseBatch if no superuser exists
                if not User.objects.filter(is_superuser=True).exists():
                    self._seed_superusers()
            except Exception as ex:
                print(f"AutoSetupMiddleware seed notice: {ex}")

        return self.get_response(request)

    def _seed_superusers(self):
        from accounts_app.models import UserProfile

        admin_email = os.getenv('ADMIN_EMAIL', 'mdsiamh77@gmail.com')
        admin_pass = os.getenv('ADMIN_PASSWORD', 'Admin123456!')

        for uname in ['admin', admin_email]:
            u = User.objects.filter(username=uname).first()
            if not u:
                u = User.objects.create_superuser(
                    username=uname,
                    email=admin_email,
                    password=admin_pass,
                    first_name='Super',
                    last_name='Admin'
                )
            else:
                u.is_superuser = True
                u.is_staff = True
                u.email = admin_email
                u.set_password(admin_pass)
                u.save()

            profile, _ = UserProfile.objects.get_or_create(user=u)
            profile.role = 'super_admin'
            profile.plan = 'enterprise'
            profile.save()

            try:
                from accounts_app.models import CourseBatch
                CourseBatch.objects.get_or_create(name="Batch - 01", defaults={"description": "Default Batch 01"})
            except Exception:
                pass

            try:
                from allauth.account.models import EmailAddress
                ea, _ = EmailAddress.objects.get_or_create(user=u, email=admin_email)
                ea.verified = True
                ea.primary = True
                ea.save()
            except Exception:
                pass

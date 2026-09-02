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
                self._seed_superusers()
            except Exception as ex:
                print(f"AutoSetupMiddleware notice: {ex}")

        return self.get_response(request)

    def _seed_superusers(self):
        from accounts_app.models import UserProfile, Subscription

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

            Subscription.objects.get_or_create(user=u, defaults={'plan': 'enterprise', 'status': 'active'})

            try:
                from allauth.account.models import EmailAddress
                ea, _ = EmailAddress.objects.get_or_create(user=u, email=admin_email)
                ea.verified = True
                ea.primary = True
                ea.save()
            except Exception:
                pass

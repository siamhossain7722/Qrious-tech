import os
import sys

# Insert project root directory at index 0 of sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linkedin_agent.settings')

# Ensure staticfiles directory exists and contains all static assets on serverless startup
staticfiles_dir = os.path.join(root_dir, 'staticfiles')
static_dir = os.path.join(root_dir, 'static')
if not os.path.exists(staticfiles_dir) and os.path.exists(static_dir):
    try:
        import shutil
        shutil.copytree(static_dir, staticfiles_dir)
    except Exception:
        pass

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

_db_initialized = False

def ensure_db_and_admin():
    global _db_initialized
    if _db_initialized:
        return
    _db_initialized = True
    try:
        call_command('migrate', '--fake-initial', interactive=False)
        from django.contrib.auth.models import User
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

    except Exception as e:
        print(f"Auto DB/Admin setup info: {e}")

try:
    ensure_db_and_admin()
except Exception:
    pass

app = get_wsgi_application()
application = app

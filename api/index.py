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

# Auto-migrate database tables on Vercel deployment startup
try:
    call_command('migrate', interactive=False)
except Exception as e:
    print(f"Auto-migration check: {e}")

app = get_wsgi_application()
application = app

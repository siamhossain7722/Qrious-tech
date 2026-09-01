import os
import sys

# Insert project root at the very front of sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linkedin_agent.settings')

try:
    from django.core.wsgi import get_wsgi_application
    app = get_wsgi_application()
except Exception as e:
    import traceback
    print("Vercel Startup Error:", e, file=sys.stderr)
    traceback.print_exc()
    raise e

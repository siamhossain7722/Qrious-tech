import os
import sys

# Add project root directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linkedin_agent.settings')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
application = app

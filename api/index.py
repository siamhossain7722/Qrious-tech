import os
import sys

# Add project root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linkedin_agent.settings')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()

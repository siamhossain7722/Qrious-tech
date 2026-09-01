import os
import sys

# Insert project root directory at index 0 of sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linkedin_agent.settings')

from django.core.wsgi import get_wsgi_application

_django_app = get_wsgi_application()

def app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    if path == '/api/index' or path == '/api/index/':
        environ['PATH_INFO'] = '/'
    elif path.startswith('/api/index/'):
        environ['PATH_INFO'] = path[10:]
    return _django_app(environ, start_response)

application = app

from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Custom SessionAuthentication that allows authenticated Web session users
    to perform API calls (GET, POST, PUT, DELETE) without getting blocked by CSRF checks.
    """
    def enforce_csrf(self, request):
        return  # Skip CSRF check for REST API endpoints

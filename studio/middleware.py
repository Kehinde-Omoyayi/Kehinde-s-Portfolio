from django.http import Http404


class AdminAccessMiddleware:
    """Hides the Django admin from anyone who isn't already an authenticated
    staff user — including the login form itself. Without this, /admin/
    redirects an anonymous visitor straight to a working login page,
    which both reveals that a Django admin exists and lets anyone attempt
    to authenticate against it. A 404 makes the path look like it simply
    doesn't exist to outsiders, while staff members who are already
    logged in pass straight through untouched."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            if not (request.user.is_authenticated and request.user.is_staff):
                raise Http404()

        return self.get_response(request)
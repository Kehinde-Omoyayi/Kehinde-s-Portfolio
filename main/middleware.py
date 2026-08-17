"""
main/middleware.py
Adds security response headers and basic IP rate-limiting for the
studio login endpoint.
"""
import time
from collections import defaultdict
from django.http import HttpResponse


# ── In-memory rate limiter (per-process; good enough for single-worker dev/prod)
_login_attempts: dict[str, list[float]] = defaultdict(list)
_WINDOW     = 60   # seconds
_MAX_HITS   = 10   # max attempts per window per IP


class SecurityHeadersMiddleware:
    """Add security headers to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Rate-limit studio login
        if request.path.startswith('/studio/login') and request.method == 'POST':
            ip = self._get_ip(request)
            now = time.time()
            hits = _login_attempts[ip]
            # Drop hits outside the window
            _login_attempts[ip] = [t for t in hits if now - t < _WINDOW]
            _login_attempts[ip].append(now)
            if len(_login_attempts[ip]) > _MAX_HITS:
                return HttpResponse(
                    'Too many requests. Please wait a minute.',
                    status=429,
                    content_type='text/plain',
                )

        response = self.get_response(request)

        # Security headers
        response['X-Content-Type-Options']  = 'nosniff'
        response['Referrer-Policy']          = 'strict-origin-when-cross-origin'
        response['Permissions-Policy']       = 'geolocation=(), microphone=(), camera=()'
        response['X-Frame-Options']          = 'SAMEORIGIN'
        return response

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

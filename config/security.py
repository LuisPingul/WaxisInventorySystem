"""
VibeSec Security Hardening Middleware & Account Lifecycle Helpers
=================================================================
Implements the VibeSec-Skill controls for INVENTIQ (WaxisInventorySystem):
  - Security Headers Checklist (CSP, X-Content-Type-Options, X-Frame-Options,
    Referrer-Policy, Permissions-Policy, Cache-Control: no-store on sensitive pages)
  - Account Lifecycle Handling (immediate session revocation when an account is
    deactivated or removed)
  - Output / CSV Sanitization against CSV Formula Injection
"""

from django.contrib.sessions.models import Session
from django.utils import timezone


DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self' https://cdn.jsdelivr.net; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


class VibeSecHeadersMiddleware:
    """
    Applies VibeSec security headers across all responses and enforces
    `Cache-Control: no-store` on authenticated HTML pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        response.setdefault("Content-Security-Policy", DEFAULT_CSP)

        # VibeSec Checklist: Cache-Control: no-store for sensitive/authenticated pages
        user = getattr(request, "user", None)
        content_type = response.get("Content-Type", "")
        if (
            user is not None
            and getattr(user, "is_authenticated", False)
            and "text/html" in content_type
            and "Cache-Control" not in response
        ):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"

        return response


def invalidate_user_sessions(user_id) -> int:
    """
    VibeSec Account Lifecycle Handling:
    When an account is deactivated or privilege-revoked, immediately delete
    all active sessions belonging to that user.
    """
    target_uid = str(user_id)
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    revoked_count = 0
    for session in active_sessions:
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if str(data.get("_auth_user_id")) == target_uid:
            session.delete()
            revoked_count += 1
    return revoked_count


def sanitize_csv_cell(value):
    """
    Neutralizes CSV Formula / DDE Injection payloads in user-controlled strings
    starting with '=', '+', '-', '@', tab, or carriage return.
    """
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{value}"
    return value

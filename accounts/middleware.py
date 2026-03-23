"""
accounts/middleware.py

Security middleware stack for MentorMatch.

SessionFingerprintMiddleware
    Binds each session to the IP + User-Agent that created it.
    If the fingerprint changes mid-session (token theft / session hijacking),
    the session is immediately invalidated and the user is logged out.

IdleTimeoutMiddleware
    Logs out users who have been inactive for longer than
    SESSION_IDLE_TIMEOUT_SECONDS (default: 30 min).
    This is separate from SESSION_COOKIE_AGE (which is the hard ceiling).

Both middlewares write to the security audit log when they take action.
"""
import hashlib
import time
import logging

from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger('mentormatch.security')


class PermissionsPolicyMiddleware:
    """
    Emits the Permissions-Policy response header.

    django-csp does not handle this header. We read the value from
    settings.PERMISSIONS_POLICY_HEADER and attach it to every response.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        from django.conf import settings
        self._header = getattr(settings, 'PERMISSIONS_POLICY_HEADER', '')

    def __call__(self, request):
        response = self.get_response(request)
        if self._header:
            response['Permissions-Policy'] = self._header
        return response

# How long (seconds) a user may be idle before being forced out.
# Override in settings.py: SESSION_IDLE_TIMEOUT_SECONDS = 1800
IDLE_TIMEOUT = getattr(settings, 'SESSION_IDLE_TIMEOUT_SECONDS', 1800)  # 30 min

# Paths that are always allowed through without session checks
_EXEMPT_PATHS = frozenset([
    '/',
    '/accounts/student/login/',
    '/accounts/guide/login/',
    '/accounts/logout/',
    '/students/register/',
    '/allocation/about/',
])


def _fingerprint(request) -> str:
    """
    Derive a session fingerprint from IP + User-Agent.
    We hash these so we don't store raw PII in the session.
    """
    raw = f"{request.META.get('REMOTE_ADDR', '')}|{request.META.get('HTTP_USER_AGENT', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()


class SessionFingerprintMiddleware:
    """
    Bind sessions to the client fingerprint that created them.

    On login:  store the fingerprint in the session.
    On each request: verify the fingerprint matches.
    On mismatch: invalidate session → prevents session token theft.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path not in _EXEMPT_PATHS:
            stored = request.session.get('_sec_fingerprint')
            current = _fingerprint(request)

            if stored is None:
                # First request after login — store it
                request.session['_sec_fingerprint'] = current
            elif stored != current:
                # Fingerprint mismatch — possible session hijack
                from accounts.security_logger import sec_log
                sec_log.session_fingerprint_mismatch(request)
                logout(request)
                messages.warning(
                    request,
                    "Your session was invalidated for security reasons. Please log in again."
                )
                return redirect(settings.LOGIN_URL)

        response = self.get_response(request)
        return response


class IdleTimeoutMiddleware:
    """
    Force logout after IDLE_TIMEOUT seconds of inactivity.

    We store `_sec_last_activity` (Unix timestamp) in the session
    and update it on every authenticated request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path not in _EXEMPT_PATHS:
            now = int(time.time())
            last = request.session.get('_sec_last_activity')

            if last is not None and (now - last) > IDLE_TIMEOUT:
                from accounts.security_logger import sec_log
                sec_log.session_idle_expired(request)
                logout(request)
                messages.info(
                    request,
                    "You were logged out due to inactivity. Please log in again."
                )
                return redirect(settings.LOGIN_URL)

            request.session['_sec_last_activity'] = now

        response = self.get_response(request)
        return response

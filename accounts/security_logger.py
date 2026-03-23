"""
accounts/security_logger.py

Structured security audit log.

Every security-relevant event is written via Python's standard logging framework
to the 'mentormatch.security' logger.  In production, configure this logger to
write to a separate file, a SIEM, or a log aggregator (Datadog, Sentry, etc.).

Usage:
    from accounts.security_logger import sec_log
    sec_log.login_success(request, user)
    sec_log.login_failed(request, username)
    sec_log.permission_denied(request, reason)

All events include: timestamp (UTC), event type, IP, user-agent, user (if any),
and a free-form detail string.  Emitted as JSON so log-aggregators can parse
them without regex.
"""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger('mentormatch.security')


def _ip(request) -> str:
    """Client IP from REMOTE_ADDR only — never trusts X-Forwarded-For header."""
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _ua(request) -> str:
    return request.META.get('HTTP_USER_AGENT', '')[:256]


def _username(request) -> str:
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user.username
    return ''


def _emit(event_type: str, request, detail: str = '', extra: dict = None, level: int = logging.INFO):
    record = {
        'ts':         datetime.now(timezone.utc).isoformat(),
        'event':      event_type,
        'ip':         _ip(request),
        'user':       _username(request),
        'user_agent': _ua(request),
        'path':       request.path,
        'method':     request.method,
        'detail':     detail,
    }
    if extra:
        record.update(extra)
    logger.log(level, json.dumps(record))


class SecurityLog:
    """Convenience wrapper — one method per security event type."""

    # ── Authentication ────────────────────────────────────────────────────────

    def login_success(self, request, user):
        _emit('AUTH_LOGIN_SUCCESS', request, detail=user.username)

    def login_failed(self, request, username: str):
        _emit('AUTH_LOGIN_FAILED', request, detail=username, level=logging.WARNING)

    def login_blocked(self, request, username: str):
        _emit('AUTH_LOGIN_BLOCKED', request, detail=username, level=logging.WARNING)

    def logout(self, request):
        _emit('AUTH_LOGOUT', request)

    def password_changed(self, request):
        _emit('AUTH_PASSWORD_CHANGED', request)

    def registration(self, request, username: str):
        _emit('AUTH_REGISTRATION', request, detail=username)

    # ── Authorisation ─────────────────────────────────────────────────────────

    def permission_denied(self, request, reason: str):
        _emit('AUTHZ_PERMISSION_DENIED', request, detail=reason, level=logging.WARNING)

    def invalid_method(self, request):
        _emit('AUTHZ_INVALID_METHOD', request,
              detail=f'{request.method} not allowed on {request.path}',
              level=logging.WARNING)

    # ── Session ───────────────────────────────────────────────────────────────

    def session_fingerprint_mismatch(self, request):
        _emit('SESSION_FINGERPRINT_MISMATCH', request, level=logging.WARNING)

    def session_idle_expired(self, request):
        _emit('SESSION_IDLE_EXPIRED', request)

    # ── Data mutations ────────────────────────────────────────────────────────

    def group_created(self, request, group_id: str, title: str):
        _emit('GROUP_CREATED', request, extra={'group_id': group_id, 'title': title})

    def group_submitted(self, request, group_id: str):
        _emit('GROUP_SUBMITTED', request, extra={'group_id': group_id})

    def group_assigned(self, request, group_id: str, guide: str):
        _emit('GROUP_ASSIGNED', request, extra={'group_id': group_id, 'guide': guide})

    def group_rejected(self, request, group_id: str):
        _emit('GROUP_REJECTED', request, extra={'group_id': group_id})

    def file_uploaded(self, request, group_id: str, file_type: str, filename: str):
        _emit('FILE_UPLOADED', request,
              extra={'group_id': group_id, 'file_type': file_type, 'filename': filename})

    def file_rejected(self, request, field: str, reason: str):
        _emit('FILE_REJECTED', request,
              detail=reason, extra={'field': field}, level=logging.WARNING)

    def todo_added(self, request, todo_id: str, group_id: str):
        _emit('TODO_ADDED', request, extra={'todo_id': todo_id, 'group_id': group_id})

    def todo_deleted(self, request, todo_id: str):
        _emit('TODO_DELETED', request, extra={'todo_id': todo_id})


# Singleton — import and use everywhere
sec_log = SecurityLog()

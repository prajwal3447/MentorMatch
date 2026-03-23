"""
accounts/rate_limiter.py

Dual-key login rate limiter: locks on both IP address AND username.

Why dual-key?
  - IP-only: an attacker distributing attempts across many IPs (botnet) can still
    brute-force a single account without ever triggering the IP lockout.
  - Username-only: a single attacker can hammer many accounts from one IP.
  - Dual-key: catches both attack patterns.

Exponential backoff:
  After the first lockout, subsequent lockouts get progressively longer:
  5 min → 15 min → 45 min → 2 h → 6 h (capped).
  This makes automated brute-force attacks impractical.

Uses Django's cache framework — set CACHE_BACKEND to Redis in production
so lockouts survive server restarts and are shared across workers.
"""
from django.core.cache import cache

MAX_ATTEMPTS = 5         # Failures before first lockout
BASE_LOCKOUT  = 300      # 5 min (seconds) — first lockout window
MAX_LOCKOUT   = 21600    # 6 hours — maximum lockout window

# Set this to True ONLY when running behind a trusted reverse proxy (e.g. Nginx).
# When False (default), X-Forwarded-For is ignored to prevent IP spoofing.
TRUST_PROXY_HEADERS = False


# ── IP extraction ──────────────────────────────────────────────────────────────

def get_client_ip(request) -> str:
    """
    Extract the real client IP.

    When running behind a trusted reverse proxy the LAST entry of
    X-Forwarded-For is the one appended by your proxy and is trustworthy.
    The FIRST entry is controlled by the client and must never be trusted.

    In direct mode (TRUST_PROXY_HEADERS=False) we ignore X-Forwarded-For.
    """
    if TRUST_PROXY_HEADERS:
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            return xff.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


# ── Cache key helpers ──────────────────────────────────────────────────────────

def _ip_attempt_key(ip: str, form: str) -> str:
    return f'login:ip_attempts:{form}:{ip}'

def _user_attempt_key(username: str, form: str) -> str:
    return f'login:user_attempts:{form}:{username}'

def _ip_lockout_key(ip: str, form: str) -> str:
    return f'login:ip_lock:{form}:{ip}'

def _user_lockout_key(username: str, form: str) -> str:
    return f'login:user_lock:{form}:{username}'

def _ip_lockout_count_key(ip: str, form: str) -> str:
    return f'login:ip_lockcount:{form}:{ip}'

def _user_lockout_count_key(username: str, form: str) -> str:
    return f'login:user_lockcount:{form}:{username}'


# ── Backoff calculation ────────────────────────────────────────────────────────

def _lockout_duration(lockout_count: int) -> int:
    """Exponential backoff: 5m, 15m, 45m, 135m (2.25h), capped at MAX_LOCKOUT."""
    duration = BASE_LOCKOUT * (3 ** lockout_count)
    return min(duration, MAX_LOCKOUT)


# ── Public API ─────────────────────────────────────────────────────────────────

def is_locked_out(request, form_name: str, username: str = '') -> bool:
    """Return True if this IP OR this username is currently locked out."""
    ip = get_client_ip(request)
    ip_locked   = cache.get(_ip_lockout_key(ip, form_name)) is not None
    user_locked = bool(username) and cache.get(_user_lockout_key(username, form_name)) is not None
    return ip_locked or user_locked


def record_failed_attempt(request, form_name: str, username: str = ''):
    """
    Increment failure counters for both IP and username.
    Triggers a lockout (with exponential backoff) when MAX_ATTEMPTS is reached.
    """
    ip = get_client_ip(request)
    _increment_and_maybe_lock(ip, form_name, _ip_attempt_key, _ip_lockout_key, _ip_lockout_count_key)
    if username:
        _increment_and_maybe_lock(
            username, form_name,
            _user_attempt_key, _user_lockout_key, _user_lockout_count_key
        )


def _increment_and_maybe_lock(key_val, form, attempt_fn, lock_fn, count_fn):
    attempt_key = attempt_fn(key_val, form)
    attempts = (cache.get(attempt_key) or 0) + 1
    cache.set(attempt_key, attempts, timeout=BASE_LOCKOUT)

    if attempts >= MAX_ATTEMPTS:
        count_key   = count_fn(key_val, form)
        lock_count  = cache.get(count_key) or 0
        duration    = _lockout_duration(lock_count)
        cache.set(lock_fn(key_val, form), True, timeout=duration)
        cache.set(count_key, lock_count + 1, timeout=MAX_LOCKOUT * 10)
        cache.delete(attempt_key)


def clear_attempts(request, form_name: str, username: str = ''):
    """Clear all counters on successful login."""
    ip = get_client_ip(request)
    cache.delete(_ip_attempt_key(ip, form_name))
    cache.delete(_ip_lockout_key(ip, form_name))
    if username:
        cache.delete(_user_attempt_key(username, form_name))
        cache.delete(_user_lockout_key(username, form_name))


def remaining_attempts(request, form_name: str, username: str = '') -> int:
    """How many attempts remain before the next IP-based lockout."""
    ip = get_client_ip(request)
    attempts = cache.get(_ip_attempt_key(ip, form_name)) or 0
    return max(0, MAX_ATTEMPTS - attempts)

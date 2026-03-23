from pathlib import Path
import os
import logging.handlers  # noqa — imported so RotatingFileHandler is available

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Load .env ──────────────────────────────────────────────────────────────────
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip())

# ── Core ───────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    import sys
    if 'runserver' in sys.argv or 'gunicorn' in ' '.join(sys.argv):
        raise RuntimeError(
            "DJANGO_SECRET_KEY is not set. "
            "Generate one with: python -c \"from django.utils.crypto import get_random_string; "
            "print(get_random_string(50))\" and set it in your .env file."
        )
    SECRET_KEY = 'ci-placeholder-not-used-in-requests'

DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1'
).split(',')

# ── Installed apps ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'csp',                              # django-csp >= 4.0: Content-Security-Policy
    'students.apps.StudentsConfig',
    'guides.apps.GuidesConfig',
    'allocation.apps.AllocationConfig',
    'accounts.apps.AccountsConfig',
]

# ── Middleware ─────────────────────────────────────────────────────────────────
# Order matters:
#   SecurityMiddleware first (adds HTTPS redirect, HSTS, etc.)
#   Sessions before Auth (auth reads from session)
#   Our security middlewares after Auth (they need request.user)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise: only active in production (DEBUG=False).
    # In dev, Django's runserver serves static files from STATICFILES_DIRS directly.
    *(['whitenoise.middleware.WhiteNoiseMiddleware'] if not DEBUG else []),
    'csp.middleware.CSPMiddleware',                        # Content-Security-Policy header
    'accounts.middleware.PermissionsPolicyMiddleware',     # Permissions-Policy header
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.SessionFingerprintMiddleware',    # session hijack prevention
    'accounts.middleware.IdleTimeoutMiddleware',           # force-logout idle sessions
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Database ───────────────────────────────────────────────────────────────────
_DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3')

if _DB_ENGINE == 'django.db.backends.postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'mentormatch'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {'options': '-c timezone=UTC'},
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Cache ──────────────────────────────────────────────────────────────────────
# Used by the rate limiter. LocMemCache in dev, Redis in production.
# To use Redis: set CACHE_BACKEND=django.core.cache.backends.redis.RedisCache
#               and CACHE_LOCATION=redis://127.0.0.1:6379/1 in .env
_CACHE_BACKEND = os.environ.get('CACHE_BACKEND', 'django.core.cache.backends.locmem.LocMemCache')
CACHES = {
    'default': {
        'BACKEND': _CACHE_BACKEND,
        'LOCATION': os.environ.get('CACHE_LOCATION', 'mentormatch-cache'),
    }
}

# ── Password hashing — Argon2 (winner of Password Hashing Competition) ────────
# pip install argon2-cffi bcrypt
# Argon2 is the primary hasher. Existing PBKDF2 hashes are transparently
# re-hashed to Argon2 on next login (Django does this automatically).
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',        # strongest — primary
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',  # fallback
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',        # legacy re-hash fallback
]

# ── Password validation ────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ───────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ── Static & Media ─────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'core' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
# In dev (DEBUG=True) Django serves from STATICFILES_DIRS automatically.
# In prod: pip install whitenoise, run collectstatic, then WhiteNoise takes over.
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Auth redirects ─────────────────────────────────────────────────────────────
LOGIN_URL = '/accounts/student/login/'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ── Session security ───────────────────────────────────────────────────────────
SESSION_EXPIRE_AT_BROWSER_CLOSE = True       # session dies when browser closes
SESSION_COOKIE_AGE = 8 * 60 * 60             # hard ceiling: 8 hours
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True               # JS cannot read session cookie
SESSION_COOKIE_SAMESITE = 'Lax'             # blocks CSRF via cross-site links
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
SESSION_COOKIE_NAME = 'mm_sid'              # non-default name reduces fingerprinting

# Idle timeout (seconds) — force-logout after inactivity (enforced by middleware)
# Default: 30 minutes. Override with SESSION_IDLE_TIMEOUT in .env.
SESSION_IDLE_TIMEOUT_SECONDS = int(os.environ.get('SESSION_IDLE_TIMEOUT', '1800'))

# ── CSRF security ──────────────────────────────────────────────────────────────
CSRF_COOKIE_HTTPONLY = False        # must be False for JS to read it
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_NAME = 'mm_csrf'        # non-default name

# ── Security headers (Django SecurityMiddleware) ───────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True   # no MIME sniffing
SECURE_BROWSER_XSS_FILTER = True     # legacy XSS filter (harmless on modern browsers)
X_FRAME_OPTIONS = 'DENY'             # clickjacking protection
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False') == 'True'
SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', 'False') == 'True'
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ── Content Security Policy (django-csp >= 4.0 format) ────────────────────────
# pip install django-csp
# CSP restricts which sources the browser may load scripts/styles/fonts from.
# 'unsafe-inline' on style-src is required because templates use inline styles.
# To tighten further: move all inline styles to CSS classes and remove it.
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src':     ("'self'",),
        # 'unsafe-inline' is required because templates use inline <script> blocks
        # and inline style= attributes throughout. To remove it in future, move all
        # inline JS to external .js files and use nonces.
        'script-src':      ("'self'", "'unsafe-inline'"),
        'style-src':       ("'self'", 'https://fonts.googleapis.com', "'unsafe-inline'"),
        'font-src':        ("'self'", 'https://fonts.gstatic.com'),
        'img-src':         ("'self'", 'data:'),
        'object-src':      ("'none'",),
        'frame-ancestors': ("'none'",),
        'form-action':     ("'self'",),
        'base-uri':        ("'none'",),
    },
}

# ── Permissions Policy ─────────────────────────────────────────────────────────
# Disables browser APIs this app never uses.
# Sent as the Permissions-Policy response header via a custom middleware shim.
# This is set as a plain dict and emitted by SecurityHeadersMiddleware below.
PERMISSIONS_POLICY_HEADER = (
    "camera=(), microphone=(), geolocation=(), payment=(), "
    "usb=(), display-capture=(), fullscreen=(self)"
)

# ── File upload limits ─────────────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE  = 20 * 1024 * 1024   # 20 MB
FILE_UPLOAD_MAX_MEMORY_SIZE  = 20 * 1024 * 1024   # 20 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100               # prevent hash-flood DoS

# ── Security audit logging ─────────────────────────────────────────────────────
# Security events go to logs/security.log (JSON, one event per line).
# In production, tail this file into your SIEM / log aggregator.
_LOG_DIR = BASE_DIR / 'logs'
_LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} — {message}',
            'style': '{',
        },
        'raw': {
            # Security events are already JSON — emit the message unchanged
            'format': '{message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(_LOG_DIR / 'security.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB per file
            'backupCount': 10,              # 100 MB total retention
            'encoding': 'utf-8',
            'formatter': 'raw',
        },
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(_LOG_DIR / 'app.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # Security audit log — every auth / authz / session / mutation event
        'mentormatch.security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django request logger — catches 4xx/5xx
        'django.request': {
            'handlers': ['app_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        # General app logger
        'django': {
            'handlers': ['app_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

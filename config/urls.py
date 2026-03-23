import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Admin URL is randomised via .env to prevent bot-targeting of /admin/.
# Set DJANGO_ADMIN_URL in your .env to a secret path (no leading/trailing slash).
# Example: DJANGO_ADMIN_URL=nm-staff-9f3a2
_ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'nm-admin-panel').strip('/') + '/'

urlpatterns = [
    path(_ADMIN_URL, admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('students.urls')),
    path('', include('guides.urls')),
    path('', include('allocation.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

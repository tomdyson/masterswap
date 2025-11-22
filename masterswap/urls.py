"""
URL configuration for masterswap project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.api import api

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API
    path('api/', api.urls),

    # Frontend pages
    path('', include('core.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

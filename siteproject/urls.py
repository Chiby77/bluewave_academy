"""
URL configuration for siteproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from siteapp.views import handler400, handler403, handler404, handler500


def health_check(request):
    """Lightweight health check endpoint for Railway and load balancers."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("", include("siteapp.urls")),
]

# Serve media files locally in development.
# In production, media is served directly from Supabase Storage.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Error handling pages
handler400 = handler400
handler403 = handler403
handler404 = handler404
handler500 = handler500

admin.site.site_header = "Bluewave Academy Administration"
admin.site.site_title = "Bluewave Academy Admin"
admin.site.index_title = "Welcome to Bluewave Academy Admin Portal"

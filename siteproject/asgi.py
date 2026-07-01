"""
ASGI config for siteproject project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "siteproject.settings")

django_asgi_app = get_asgi_application()

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    import siteapp.routing

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                siteapp.routing.websocket_urlpatterns
            )
        ),
    })
except ImportError as e:
    print(f"Warning: Channels not available, falling back to HTTP only. Error: {e}")
    application = django_asgi_app


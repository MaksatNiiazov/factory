import os

from django.core.asgi import get_asgi_application
from django.urls import re_path

from kernel.consumers import FakeQueryCookieMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
os.environ.setdefault('PSYCOPG_IMPL', 'binary')  # NOQA
django_asgi_app = get_asgi_application()  # NOQA

from channels.auth import AuthMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddleware

from kernel import consumers

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': FakeQueryCookieMiddleware(SessionMiddleware(AuthMiddleware(
        URLRouter([
            re_path(r'^api/ws/$', consumers.WSConsumer.as_asgi()),
        ])
    ))),
})

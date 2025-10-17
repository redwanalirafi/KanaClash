from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<room_code>[0-9a-f-]+)/$', consumers.GameConsumer.as_asgi()),
]

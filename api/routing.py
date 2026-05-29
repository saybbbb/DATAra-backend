from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/predictions/', consumers.PredictionConsumer.as_asgi()),
]

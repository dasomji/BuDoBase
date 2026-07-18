from django.urls import path

from budo_app.happy_cleaning_consumers import HappyCleaningInvalidationConsumer


websocket_urlpatterns = [
    path(
        "ws/happy-cleaning/events/<int:event_id>/",
        HappyCleaningInvalidationConsumer.as_asgi(),
    ),
]

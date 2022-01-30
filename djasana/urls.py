from django.urls import include, re_path
from djasana.settings import settings

from .views import WebhookView

urlpatterns = [
    re_path(
        settings.DJASANA_WEBHOOK_PATTERN or r"^",
        include(
            [
                re_path(
                    r"^project/(?P<remote_id>\d+)/$",
                    view=WebhookView.as_view(),
                    name="djasana_webhook",
                ),
            ]
        ),
    )
]

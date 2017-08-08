from django.conf.urls import url

from .views import WebhookView
from .settings import settings

urlpatterns = [
    url(
        regex=r'^{0}project/(?P<remote_id>\d+)/$'.format(settings.DJASANA_WEBHOOK_URL),
        view=WebhookView.as_view(),
        name='djasana_webhook'
    ),
]

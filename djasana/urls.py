from django.conf.urls import url, include
from djasana.settings import settings

from .views import WebhookView

urlpatterns = [
    url(settings.DJASANA_WEBHOOK_PATTERN or r'^', include([
        url(r'^project/(?P<remote_id>\d+)/$', view=WebhookView.as_view(), name='djasana_webhook'),
    ]))]

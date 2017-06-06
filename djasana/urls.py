from django.conf.urls import url

from .views import WebhookView

urlpatterns = [
    url(r'^project/(?P<remote_id>\d+)/$', WebhookView.as_view(), name='djasana_webhook'),
]

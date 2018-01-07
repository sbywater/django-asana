from django.conf.urls import url

from .views import WebhookView

urlpatterns = [
    url(
        regex=r'^project/(?P<remote_id>\d+)/$',
        view=WebhookView.as_view(),
        name='djasana_webhook'
    ),
]

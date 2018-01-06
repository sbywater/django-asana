from django.conf import settings
from django.conf.urls import include, url

urlpatterns = [
    url(settings.DJASANA_WEBHOOK_PATTERN, include('djasana.urls')),
]

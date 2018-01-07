from django.conf.urls import include, url
from djasana import settings

urlpatterns = [
    url(settings.DJASANA_WEBHOOK_PATTERN, include('djasana.urls')),
]

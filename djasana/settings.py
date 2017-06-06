from django.conf import settings

DJASANA_WEBHOOK_URL = getattr(settings, 'DJASANA_WEBHOOK_URL', None)

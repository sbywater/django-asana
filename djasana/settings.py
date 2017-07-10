from django.conf import settings

settings.DJASANA_WEBHOOK_URL = getattr(settings, 'DJASANA_WEBHOOK_URL', None)
settings.ASANA_WORKSPACE = getattr(settings, 'ASANA_WORKSPACE', None)

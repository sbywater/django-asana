from django.conf import settings

settings.DJASANA_WEBHOOK_URL = getattr(settings, 'DJASANA_WEBHOOK_URL', None)
settings.DJASANA_WEBHOOK_PATTERN = getattr(
    settings, 'DJASANA_WEBHOOK_PATTERN', r'^djasana/webhooks/')
settings.ASANA_WORKSPACE = getattr(settings, 'ASANA_WORKSPACE', None)

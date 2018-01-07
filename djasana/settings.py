from django.conf import settings

DJASANA_WEBHOOK_URL = getattr(settings, 'DJASANA_WEBHOOK_URL', None)
DJASANA_WEBHOOK_PATTERN = getattr(
    settings, 'DJASANA_WEBHOOK_PATTERN', r'^djasana/webhooks/')
ASANA_WORKSPACE = getattr(settings, 'ASANA_WORKSPACE', None)

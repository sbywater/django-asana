from django.conf import settings

settings.configure(DJASANA_WEBHOOK_URL=None)
settings.configure(DJASANA_WEBHOOK_PATTERN=r'^djasana/webhooks/')
settings.configure(ASANA_WORKSPACE=None)

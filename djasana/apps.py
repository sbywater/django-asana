from django.apps import AppConfig


class DjsanaConfig(AppConfig):
    name = 'djasana'
    verbose_name = 'Asana'

    def ready(self):
        pass

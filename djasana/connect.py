import logging

import asana
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class Client(asana.Client, object):

    def request(self, method, path, **options):
        logging.debug('%s, %s', method, path)
        return super(Client, self).request(method, path, **options)


def client_connect():
    if hasattr(settings, 'ASANA_ACCESS_TOKEN'):
        client = Client.access_token(settings.ASANA_ACCESS_TOKEN)
    elif hasattr(settings, 'ASANA_CLIENT_ID') and hasattr(settings, 'ASANA_CLIENT_SECRET') and \
            hasattr(settings, 'ASANA_OAUTH_REDIRECT_URI'):
        client = Client.oauth(
            client_id=settings.ASANA_CLIENT_ID,
            client_secret=settings.ASANA_CLIENT_SECRET,
            redirect_uri=settings.ASANA_OAUTH_REDIRECT_URI
        )
    else:
        return ImproperlyConfigured(
            'It is required to set the ASANA_ACCESS_TOKEN or the three OAuth2 settings ' +
            'ASANA_CLIENT_ID, ASANA_CLIENT_SECRET, and ASANA_OAUTH_REDIRECT_URI.')

    if hasattr(settings, 'ASANA_WORKSPACE'):
        workspaces = client.workspaces.find_all()
        for workspace in workspaces:
            if settings.ASANA_WORKSPACE == workspace['name']:
                client.options['workspace_id'] = workspace['id']

    return client

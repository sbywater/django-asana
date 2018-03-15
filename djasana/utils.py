import hashlib
import hmac
import logging

import django
from asana.error import InvalidRequestError
from django.conf import settings
if django.VERSION >= (2, 0, 0):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse

logger = logging.getLogger(__name__)


def sign_sha256_hmac(secret, message):
    if type(message) != bytes:
        message = bytes(message.encode('utf-8'))
    if type(secret) != bytes:
        secret = bytes(secret.encode('utf-8'))
    return hmac.new(secret, message, digestmod=hashlib.sha256).hexdigest()


def set_webhook(client, project_id):
    target = '{}{}'.format(
        settings.DJASANA_WEBHOOK_URL,
        reverse('djasana_webhook', kwargs={'remote_id': project_id}))
    logger.debug('Setting webhook at %s', target)
    try:
        client.webhooks.create({
            'resource': project_id,
            'target': target,
        })
    except InvalidRequestError as error:
        logger.warning(error)
        logger.warning('Target url: %s', target)

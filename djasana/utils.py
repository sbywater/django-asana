import base64
import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def sign_sha256_hmac(secret, message):
    if type(message) != bytes:
        message = bytes(message.encode('utf-8'))
    if type(secret) != bytes:
        secret = bytes(secret.encode('utf-8'))
    return base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest())

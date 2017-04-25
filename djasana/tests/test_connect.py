import unittest

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from asana.error import NoAuthorizationError
from djasana.connect import client_connect


class ClientConnectTestCase(unittest.TestCase):
    @override_settings(ASANA_ACCESS_TOKEN=None, ASANA_CLIENT_ID=None)
    def test_settings_required(self):
        with self.assertRaises(ImproperlyConfigured):
            client_connect()

    @override_settings(ASANA_ACCESS_TOKEN='foo')
    def test_connect_access_token(self):
        with self.assertRaises(NoAuthorizationError):
            client_connect()

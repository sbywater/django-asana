"""Django Asana integration project"""
# :copyright: (c) 2017 by Stephen Bywater.
# :license:   MIT, see LICENSE for more details.

VERSION = (0, 4, 1)
__version__ = '.'.join(map(str, VERSION[0:3])) + ''.join(VERSION[3:])
__author__ = 'Steve Bywater'
__contact__ = 'steve@regionalhelpwanted.com'
__homepage__ = 'https://github.com/sbywater/django-asana'
__docformat__ = 'restructuredtext'
__license__ = 'MIT'

# -eof meta-
default_app_config = 'djasana.apps.DjsanaConfig'

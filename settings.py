INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'djasana',
]

SECRET_KEY = 'not a secret'
ROOT_URLCONF = 'urls'

DATABASES = {
    'default': {
        'NAME': ':memory:',
        'ENGINE': 'django.db.backends.sqlite3',
    },
}

MIDDLEWARE = []

DJASANA_WEBHOOK_URL = ''

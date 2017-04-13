=====
django-asana
=====

django-asana leverages python-asana, the official python client library for Asana. To this, django-asana adds
django models and commands for importing data from Asana into these models.

Detailed documentation is in the "docs" directory.

Installation
------------

This will also install [python-asana](https://github.com/Asana/python-asana)

 $ pip install django-asana -e git+git://github.com/sbywater/django-asana.git#egg=django-asana

Quick start
-----------

1. Configure your django settings file. Asana allows two different connection methods.
For Oauth2, provide values for the following settings: ASANA_CLIENT_ID, ASANA_CLIENT_SECRET, and ASANA_OAUTH_REDIRECT_URI.
To use an access token, provide a value for ASANA_ACCESS_TOKEN.
Then add "django-asana" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'djasana',
    ]

2. Run `python manage.py migrate` to create the Asana models.


Other Settings
--------------

To restrict your project to a single workspace, add the setting ASANA_WORKSPACE.

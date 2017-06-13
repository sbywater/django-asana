============
django-asana
============

:License: MIT

django-asana leverages python-asana, the official python client library for Asana. To this, django-asana adds
django models and commands for importing data from Asana into these models.

Detailed documentation is in the "docs" directory.

About
=====

``django-asana`` aims to allow for rich interaction between Django projects and Asana projects. The vision is to allow automated processes done in Django to interact with human Asana users toward project completion. For example, an Asana project might include a workflow of ten tasks that must all be completed in order. This tool will monitor the Asana project status, complete the automated steps when they are ready to be done, and report completion bask to Asana so the workflow may continue.

For now, this tool can do a one time sync from Asana, storing the current status of workspaces, projects, and tasks in Django models. Depending on the size of the Asana workspaces, this initial sync may take some time. Successive syncs are faster if they are performed within the hour, which is the timeout for Asana's sync token. Webhook receivers are registered so the Django project will remain synced to Asana in real-time. Task.sync_to_asana() can be used to update Asana to reflect local changes, like task completion.


Requirements
============

#. Python 3+
#. `Django 1.8+ <https://www.djangoproject.com/>`_
#. `python-asana 0.6.2+ <https://github.com/Asana/python-asana>`_
#. `django-braces 1.10+ <https://django-braces.readthedocs.io/en/latest/index.html>`_ for JsonRequestResponseMixin


Installation
============

This will also install `python-asana <https://github.com/Asana/python-asana>`_.

 $ pip install django-asana

Quick start
===========

#. Configure your django settings file. Asana allows two different connection methods. For Oauth2, provide values for the following settings: ASANA_CLIENT_ID, ASANA_CLIENT_SECRET, and ASANA_OAUTH_REDIRECT_URI. To use an access token, provide a value for ASANA_ACCESS_TOKEN. Then add "django-asana" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'djasana',
    ]

#. To enable webhooks so Asana can keep your data in sync, add the following to your base urls.py

    urlpatterns += [
        url(r'^', include('djasana.urls')),
    ]

In the production version of your settings, set a base url for the webhooks. It must be reachable by Asana and secured by SSL. In your dev environment it is fine to leave this setting out; your project will be synced whenever you run the management command.

    DJASANA_WEBHOOK_URL = 'https://mysite.com/djasana/webhooks/'

With that value, your webhook urls will be something like this: https://mysite.com/djasana/webhooks/project/1337/



#. Run `python manage.py migrate` to create the Asana models.
#. Run the command to synchronize data from Asana to Django:

 $ python manage.py sync_from_asasa


Command line options
====================

===================     ======================================================
``--workspace, -w``     Restrict work to the named Asana workspace. Can be used
                        multiple times. By default, all workspaces will used.

                        Ex: python manage.py sync_from_asana -w 'Private Projects'`

``--project, -p``       Restrict work to the named Asana project. Can be used
                        multiple times. By default, all projects will used.

                        Ex: python manage.py sync_from_asana -p 'Sample Project'`

``--model, -m``         Restrict work to the named model. Can be used
                        multiple times. By default, all models will used.
                        Capitalization is ignored.

                        Ex: python manage.py sync_from_asana -m Workspace -m Project -m Task

``--archive, -a``       Sync task, attachments, etc. of projects even if those projects are
                        archived. The default behavior is to skip these, saving a lot of processing
                        for larger data sets.

``--nocommit``          Connects to Asana and outputs work in debug log but does not commit any
                        database changes.

``--noinput``           Skip the warning that running this process will make data changes.
===================     ======================================================



See also `python manage.py sync_from_asana --help`


Other Settings
--------------

To restrict your project to a single workspace, add the setting ASANA_WORKSPACE.

    ASANA_WORKSPACE = 'Personal Projects'


Limitations
-----------

django-asana does not support updating user photo data. It will read user photo data from Asana, if available, but only the path to the 128x128 version of the photo.

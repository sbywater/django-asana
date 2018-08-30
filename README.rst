============
django-asana
============

:License: MIT

.. image:: https://travis-ci.org/sbywater/django-asana.svg?branch=master
    :target: https://travis-ci.org/sbywater/django-asana
    :alt: Build Status
.. image:: https://coveralls.io/repos/github/sbywater/django-asana/badge.svg
    :target: https://coveralls.io/github/sbywater/django-asana
    :alt: Coverage Status
.. image:: https://badge.fury.io/py/django-asana.svg
    :target: https://badge.fury.io/py/django-asana
    :alt: Pypi Package
.. image:: https://readthedocs.org/projects/django-asana/badge/?version=latest
    :target: https://django-asana.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. inclusion-marker-do-not-remove

django-asana leverages python-asana, the official python client library for Asana. To this, django-asana adds
django models and commands for importing data from Asana into these models, and for keeping a django project in sync with related Asana data.

* Documentation: https://django-asana.readthedocs.io/en/latest/

About
=====

``django-asana`` aims to allow for rich interaction between Django projects and Asana projects. The vision is to allow automated processes done in Django to interact with human Asana users toward project completion. For example, an Asana project might include a workflow of ten tasks that must all be completed in order. This tool will monitor the Asana project status, complete the automated steps when they are ready to be done, and report completion back to Asana so the workflow may continue.

This tool can do a one time sync from Asana, storing the current status of workspaces, projects, tasks, users, teams and tags in Django models. Depending on the size of the Asana workspaces, this initial sync may take some time. Successive syncs are faster if they are performed within the hour, which is the timeout for Asana's sync token. You may specify to sync only specific workspaces, projects or models.

Optionally, Webhook receivers are registered so the Django project will remain synced to Asana in real-time. The Asana API only supports webhooks for projects and tasks, so even if you use django-asana webhooks to keep your projects in sync in real-time you will still periodically want to run the sync-from-asana task to get new projects and reflect additions and changes to workspaces, users, etc.

Task.sync_to_asana() can be used to update Asana to reflect local changes, like task completion. Task.add_comment() can be used to add a comment to a task in Asana.


Requirements
============

#. Python 3+
#. `Django 1.9 - 2.1+ <https://www.djangoproject.com/>`_
#. `python-asana 0.8.0+ <https://github.com/Asana/python-asana>`_
#. `django-braces 1.11+ <https://django-braces.readthedocs.io/en/latest/index.html>`_ for JsonRequestResponseMixin


Installation
============

This will also install `python-asana <https://github.com/Asana/python-asana>`_.

.. code:: bash

    pip install django-asana

Quick start
===========

1. Configure your django settings file. Asana allows two different connection methods. For Oauth2, provide values for the following settings: ASANA_CLIENT_ID, ASANA_CLIENT_SECRET, and ASANA_OAUTH_REDIRECT_URI. To use an access token, provide a value for ASANA_ACCESS_TOKEN. Then add "django-asana" to your INSTALLED_APPS setting.

.. code:: python

    INSTALLED_APPS = [
        ...
        'djasana',
    ]

If you have multiple Asana workspaces but only ever need to sync one with Django, specify it.

.. code:: python

    ASANA_WORKSPACE = 'This Workspace'

In the production version of your settings, set a base url and pattern for the webhooks. It must be reachable by Asana and secured by SSL. In your dev environment it is fine to leave this setting out; your project will be synced whenever you run the management command.

.. code:: python

    DJASANA_WEBHOOK_URL = 'https://mysite.com'
    DJASANA_WEBHOOK_PATTERN = r'^djasana/webhooks/'

With that value, your webhook urls will be something like this: https://mysite.com/djasana/webhooks/project/1337/


2. If your project is "live" and has a webserver to which Asana can send requests, you can enable webhooks. To enable webhooks so Asana can keep your data in sync, add the following to your base urls.py

.. code:: python

    urlpatterns += [
        url(settings.DJASANA_WEBHOOK_PATTERN, include('djasana.urls')),
    ]

3. Run `python manage.py migrate` to create the Asana models.
4. Run the command to synchronize data from Asana to Django:

.. code:: python

    python manage.py sync_from_asasa


Command line options
====================

========================    =======================================================================
``--workspace, -w``         Restrict work to the specified Asana workspace, by id or name. Can be
                            used multiple times. By default, all workspaces will used.

                            Ex: `python manage.py sync_from_asana -w 1234567890`

``--project, -p``           Restrict work to the specified Asana project, by id or name. Can be
                            used multiple times. By default, all projects will used. If you specify
                            a project and have multiple workspaces and have not set
                            ASANA_WORKSPACE, also specify the workspace.

                            Ex: `python manage.py sync_from_asana -p MyProject.com`
                            `python manage.py sync_from_asana -w 1234567890 -p MyProject.com`

``--model, -m``             Restrict work to the named model. Can be used
                            multiple times. By default, all models will used.
                            Capitalization is ignored.

                            Ex: `python manage.py sync_from_asana -m Workspace -m Project -m Task`

``--model-exclude, -mx``    Exclude the named model. Can be used
                            multiple times. Capitalization is ignored.

                            Ex: `python manage.py sync_from_asana -mx Story -mx Attachment -mx Tag`

``--archive, -a``           Sync task, attachments, etc. of projects even if those projects are
                            archived. The default behavior is to skip archived projects, saving a
                            lot of processing for larger data sets.

``--nocommit``              Connects to Asana and outputs work in debug log but does not commit any
                            database changes.

``--noinput``               Skip the warning that running this process will make data changes.
========================    =======================================================================

Note that due to option parsing limitations, it is less error prone to pass in the id of the object
rather than the name. The easiest way to find the id of a project or task in Asana is to examine the url.
The list view in Asana is like `https://app.asana.com/0/{project_id}/list` and for a specific task `https://app.asana.com/0/{project_id}/{task_id}`.

Good example:

.. code:: bash

    python manage.py sync_from_asana -w 123456

Bad example:

.. warning::

    python manage.py sync_from_asana -w="Personal Projects"

    ``python manage.py sync_from_asana: error: unrecognized arguments: Projects``

Further note that when including a model, the models it depends on will also be included. You cannot sync tasks without syncing the projects those tasks belong to.

The dependency chain for models it this, from the bottom up:

    | Story --> Task --> Project --> Workspace
    | Tags --> Task
    | Attachment --> Task
    | Project --> Team
    | Task --> User --> Workspace

Effectively, this means you can explicitly include models from the top down or exclude models from the bottom up:

.. code:: bash

    python manage.py sync_from_asana -mx=Story -mx=Attachment -mx=Tag --noinput


See also `python manage.py sync_from_asana --help`


Other Settings
--------------

To restrict your project to a single workspace, add the setting ASANA_WORKSPACE.

    ASANA_WORKSPACE = 'Personal Projects'


Asana id versus gid
-------------------

Asana has begun migrating from `numeric ids to string gids <https://community.asana.com/t/asana-is-moving-to-string-ids/29340>`_. django-asana populates both of these fields, and will follow the migration path Asana has established.


Limitations
-----------

django-asana support for custom fields is not well tested. If you use custom fields with django-asana, please `report any bugs you find <https://github.com/sbywater/girlsworldexpo/issues>`_.

django-asana does not support updating user photo data. It will read user photo data from Asana, if available, but only the path to the 128x128 version of the photo.

If a project or task that has been synced to Django is deleted in Asana, and webhooks are not used, it is not deleted in Django with the sync_from_asana command. This is forthcoming functionality.

Running tests
=============

After installing django-asana and adding it to your project, run tests against it as you would any other app:

.. code:: bash

    python manage.py test djasana

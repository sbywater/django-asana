============
django-asana
============

:License: MIT

django-asana leverages python-asana, the official python client library for Asana. To this, django-asana adds
django models and commands for importing data from Asana into these models.

Detailed documentation is in the "docs" directory.

Requirements
============

This project requires Python 3.


Installation
============

This will also install `python-asana <https://github.com/Asana/python-asana>`_.

 $ pip install django-asana

Quick start
===========

1. Configure your django settings file. Asana allows two different connection methods. For Oauth2, provide values for the following settings: ASANA_CLIENT_ID, ASANA_CLIENT_SECRET, and ASANA_OAUTH_REDIRECT_URI. To use an access token, provide a value for ASANA_ACCESS_TOKEN. Then add "django-asana" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'djasana',
    ]

2. Run `python manage.py migrate` to create the Asana models.
3. Run the command to synchronize data from Asana to the default Django database:

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

``--nocommit``          Connects to Asana and outputs work in debug log but does to commit any
                        database changes.

``--noinput``           Skip the warning that running this process will make data changes.
===================     ======================================================



See also `python manage.py sync_from_asana --help`


Other Settings
--------------

To restrict your project to a single workspace, add the setting ASANA_WORKSPACE.


Limitations
-----------

django-asana does not support updating user photo data. It will read user photo data from Asana, if available, but only the path to the 128x128 version of the photo.

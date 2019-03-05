=========
Changelog
=========

All notable changes to this project will be documented in this file.


Unreleased
---------------
Added
~~~~~

1.4.0 (2019-03-05)
----------------
Added
~~~~~
- Improves forward compatibility with Asana API changes by popping unexpected fields before update_or_create. In the past, undocumented and unannounced changes to the Asana API would often break django-asana.

1.3.6 (2018-12-04)
------------------
Added
~~~~~
- Support task dependencies

1.3.5 (2018-11-20)
------------------
Added
~~~~~
- Added missing migration

1.3.4 (2018-11-08)
------------------
Changed
~~~~~~~
- Setup requires python ~=3.5

1.3.3 (2018-10-23)
------------------
Added
~~~~~
- Added support for tags
- Improved support for resource_type, resource_subtype

1.3.2 (2018-10-02)
------------------
Added
~~~~~
- Added support for resource_type, resource_subtype

1.3.1 (2018-09-27)
------------------
Added
~~~~~
- Pop unused field "resource_type"

Changed
~~~~~~~
- Fixed syncing of child task of task without a project. `Pull request 3 <https://github.com/sbywater/django-asana/pull/3>`_.



1.3.0 (2018-09-30)
------------------
Added
~~~~~
- Adds field gid.
- Added admin for Webhook

1.2.0 (2018-09-23)
------------------
Added
~~~~~
- Begins supprt for `gid field <https://community.asana.com/t/asana-is-moving-to-string-ids/29340>`_.
- Adds initial support for custom fields.

1.1.2 (2018-09-15)
------------------
Added
~~~~~
- Adds model fields for updated Asana API.

Changed
~~~~~~~
- Required updated python-asana.


1.1.1 (2018-07-12)
------------------
Added
~~~~~
- Added Task.delete_from_asana

1.1.0 (2018-07-12)
------------------
Added
~~~~~
- After sync, delete local tasks no longer in Asana.
- Added Python 3.7 to test matrix

Changed
~~~~~~~
- When a webhook receive a task changed event, no longer proactively sync stories of the task as those are sent as their own events.


1.0.0 (2018-06-21)
------------------
Added
~~~~~
- Configured travis.yml

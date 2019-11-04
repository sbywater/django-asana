Creating Data in Asana
======================

There are two methods on Task for writing to Asana: sync_to_asana() and add_comment().


Task.sync_to_asana(fields=None)
-------------------------------

With no arguments, can be used to update the 'completed' status of a Task:

.. code:: python

        task.completed = True
        task.save()
        task.sync_to_asana()

Optionally, a sequence of fields can be passed:

.. code:: python

        task.notes = 'Get it done!'
        task.due_on = today
        task.save()
        task.sync_to_asana(fields=('notes', 'due_on'))


Task.add_comment(text)
----------------------

.. code:: python

    task.add_comment('Email sent to 123 users.')


Everything else
---------------

Other than those use cases, to create data in Asana, use the client provided by django-asana but beyond that use `python-asana <https://github.com/Asana/python-asana>`_ directly.

.. code:: python

    from dateutil.parser import parse
    from django.db import IntegrityError
    from djasana.connect import client_connect
    from djasana.models import Task

    def create_task():
        client = client_connect()
        workspace_id = 123456  # A djasana.models.Workspace.remote_id,
        owner_id = 567890,  # Maybe your own id at Asana
        project = {  # A dict of values you want to create
            'name': 'A test project',
            'workspace': workspace_id,
            'owner': owner_id,
        }
        # projects.create is a method provided by python-asana:
        project_response = client.projects.create(data)
        project_remote_id = project_response['gid']
        for key in (
                'followers', 'members', 'owner', 'team', 'workspace'):
            project_response.pop(key, None)
        # Convert string to boolean:
        response['archived'] = response['archived'] == 'true'
        Project.objects.create(
            remote_id=project_remote_id,
            owner_id=owner_id,
            workspace_id=workspace_id,
            **project_response
            )
        task = {'name': 'A test task', projects: [project_remote_id]}
        # tasks.create is a method provided by python-asana:
        task_response = client.tasks.create(workspace=workspace_id, **task)
        task_response['remote_id'] = task_response['gid']
        task_response['assignee_id'] = task_response.pop('assignee')['gid']
        if 'due_on' in task_response and isinstance(task_response['due_on'], str):
            task_response['due_on'] = parse(task_response['due_on'])
        if 'parent' in task_response and task_response['parent']:
            task_response['parent_id'] = task_response.pop('parent')['gid']
        for key in (
                'followers', 'hearts', 'liked', 'likes', 'num_likes', 'num_hearts',
                'memberships', 'projects', 'tags', 'workspace'):
            task_response.pop(key, None)
        Task.objects.create(**task_response)

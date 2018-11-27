Creating Data in Asana
======================

To create data in Asana, use the client provided by django-asana but beyond that use python-asana directly.

.. code:: python

    from dateutil.parser import parse
    from django.db import IntegrityError
    from djasana.connect import client_connect
    from djasana.models import Task

    def create_task():
        client = client_connect()
        workspace_id  # A djasana.models.Workspace.remote_id
        task = {}  # A dict of values you want to create
        task_response = client.tasks.create(workspace=workspace_id, **task)
        task_response['remote_id'] = task_response.pop('id', None)
        task_response.pop('gid', None)
        task_response.pop('resource_type', None)
        task_response.pop('resource_subtype', None)
        task_response['assignee_id'] = task_response.pop('assignee')['id']
        if 'due_on' in task_response and isinstance(task_response['due_on'], str):
            task_response['due_on'] = parse(task_response['due_on'])
        if 'parent' in task_response and task_response['parent']:
            task_response['parent_id'] = task_response.pop('parent')['id']
        for key in (
                'followers', 'hearts', 'liked', 'likes', 'num_likes', 'num_hearts',
                'memberships', 'projects', 'tags', 'workspace'):
            task_response.pop(key, None)
                try:
            task_ = Task.objects.create(**task_response)
        except IntegrityError:
            # This task already got created by webhook!
            pass

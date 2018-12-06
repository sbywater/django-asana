from collections import defaultdict

from django.utils import timezone


def fake_response(**kwargs):
    response = defaultdict(lambda: None, **kwargs)
    # https://community.asana.com/t/asana-is-moving-to-string-ids/29340
    response['gid'] = response['id']
    response['id'] = str(response['id'])
    return response


def attachment(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Attachment',
        'parent': task(),
        'resource_type': 'attachment',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def custom_field(**kwargs):
    defaults = {
        'id': 1,
        'description': 'Priority',
        'enum_options': '''[
            {
              "id": 789,
              "gid": "789",
              "name": "Low",
              "enabled": true,
              "color": "blue",
              "resource_type": "enum_option"
            },
            {
              "id": 790,
              "gid": "790",
              "name": "Medium",
              "enabled": true,
              "color": "yellow",
              "resource_type": "enum_option"
            },
            {
              "id": 791,
              "gid": "791",
              "name": "High",
              "enabled": true,
              "color": "red",
              "resource_type": "enum_option"
            }
          ]''',
        'name': 'Test Custom Field',
        'resource_type': 'custom_field',
        'resource_subtype': 'enum',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def project(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Project',
        'archived': 'false',
        'custom_fields': [],
        'current_status': None,
        'followers': [user()],
        'owner': user(),
        'team': team(),
        'members': [user()],
        'modified_at': timezone.now(),
        'public': True,
        'workspace': workspace(),
        'resource_type': 'project',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def project_status(**kwargs):
    defaults = {
        'id': 1,
        'color': 'green',
        'created_at': None,
        'created_by': None,
        'html_text': '<body>Test</body>',
        'resource_type': 'project_status',
        'text': 'Test',
        'title': 'Project Status',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def story(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Story',
        'created_by': user(),
        'previews': [],
        'target': task(),
        'resource_type': 'story',
        'resource_subtype': 'default_story',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def tag(**kwargs):
    defaults = {
        'id': 1,
        'followers': [user()],
        'name': 'Test Tag',
        'resource_type': 'tag',
        'workspace': workspace(),
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def task(*dummy, **kwargs):
    """When called as a mock side effect, this will have a positional argument"""
    defaults = {
        'id': 1,
        'name': 'Test Task',
        'assignee': user(),
        'completed': False,
        'dependencies': None,
        'dependents': None,
        'followers': [user()],
        'html_notes': '<body>A note.</body>',
        'memberships': None,
        'modified_at': timezone.now(),
        'notes': 'A note.',
        'parent': None,
        'projects': [project()],
        'tags': [tag()],
        'workspace': workspace(),
        'resource_type': 'task',
        'resource_subtype': 'default_task',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def team(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Team',
        'organization': {
            'id': 1,
            'name': 'Test Organization',
        },
        'resource_type': 'team',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def user(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test User',
        'workspaces': [workspace()],
        'resource_type': 'user',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def webhook(**kwargs):
    defaults = {
        'id': 1,
        'resource': project(),
        'target': 'https://example.com/receive-webhook/7654',
        'active': True,
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def workspace(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Workspace',
        'email_domains': None,
        'is_organization': False,
        'resource_type': 'workspace',
    }
    defaults.update(kwargs)
    return fake_response(**defaults)

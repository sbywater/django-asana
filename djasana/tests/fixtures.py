from collections import defaultdict

from django.utils import timezone


def fake_response(**kwargs):
    response = defaultdict(lambda: None, **kwargs)
    return response


def attachment(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Attachment',
        'parent': task(),
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def project(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Project',
        'archived': 'false',
        'followers': [user()],
        'owner': user(),
        'team': team(),
        'members': [user()],
        'modified_at': timezone.now(),
        'public': True,
        'workspace': workspace(),
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def story(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Story',
        'created_by': user(),
        'target': task(),
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def tag(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Tag',
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
        'followers': [user()],
        'memberships': None,
        'modified_at': timezone.now(),
        'parent': None,
        'projects': [project()],
        'tags': [tag()],
        'workspace': workspace(),
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
        }
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def user(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test User',
        'workspaces': [workspace()],
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
    }
    defaults.update(kwargs)
    return fake_response(**defaults)

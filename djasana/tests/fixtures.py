from __future__ import unicode_literals
from collections import defaultdict

from django.utils import timezone


def fake_response(**kwargs):
    response = defaultdict(lambda: None, **kwargs)
    return response


def project(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test Project',
        'archived': False,
        'followers': [user()],
        'team': team(),
        'members': [user()],
        'modified_at': timezone.now(),
        'public': True,
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


def task(**kwargs):
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
    }
    defaults.update(kwargs)
    return fake_response(**defaults)


def user(**kwargs):
    defaults = {
        'id': 1,
        'name': 'Test User',
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

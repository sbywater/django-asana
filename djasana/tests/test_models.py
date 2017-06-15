import unittest

from djasana import models
from djasana.tests import fixtures
from django.test import TestCase, override_settings
from django.utils import timezone


class TaskModelTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.workspace = models.Workspace.objects.create(remote_id=1, name='New Workspace')
        cls.team = models.Team.objects.create(remote_id=2, name='New Team')
        cls.project = models.Project.objects.create(
            remote_id=3, name='New Project', public=True, team=cls.team, workspace=cls.workspace)
        cls.now = timezone.now()
        cls.task = models.Task.objects.create(
            remote_id=4, name='New Task', completed=False, due_at=cls.now)
        cls.task.projects.add(cls.project)

    def test_asana_url(self):
        self.assertEqual('https://app.asana.com/0/1/4/list', self.task.asana_url())

    def test_asana_url_with_project(self):
        self.assertEqual('https://app.asana.com/0/1/4/list', self.task.asana_url(self.project))

    def test_asana_url_multiple_projects(self):
        project = models.Project.objects.create(
            remote_id=5, name='New Project', public=True, team=self.team, workspace=self.workspace)
        self.task.projects.add(project)
        self.assertEqual('https://app.asana.com/0/4', self.task.asana_url())

    def test_due(self):
        self.assertEqual(self.now, self.task.due())

    @override_settings(ASANA_ACCESS_TOKEN='foo')
    @unittest.mock.patch('djasana.models.client_connect')
    def test_refresh_from_asana(self, mock_connect):
        mock_client = mock_connect.return_value
        task = fixtures.task()
        mock_client.tasks.find_by_id.return_value = task
        self.task.refresh_from_asana()
        self.assertTrue(mock_client.tasks.find_by_id.called)
        self.task.refresh_from_db()
        self.assertEqual(task['name'], self.task.name)


class UserModelTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = models.User.objects.create(remote_id=6, name='New User')

    @override_settings(ASANA_ACCESS_TOKEN='foo')
    @unittest.mock.patch('djasana.models.client_connect')
    def test_refresh_from_asana(self, mock_connect):
        mock_client = mock_connect.return_value
        user = fixtures.user()
        mock_client.users.find_by_id.return_value = user
        self.user.refresh_from_asana()
        self.assertTrue(mock_client.users.find_by_id.called)
        self.user.refresh_from_db()
        self.assertEqual(user['name'], self.user.name)

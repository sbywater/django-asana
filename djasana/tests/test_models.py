from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from djasana import models
from djasana.tests import fixtures


LOCAL_MEMORY_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


class ProjectColorTestCase(SimpleTestCase):

    @staticmethod
    def cycle_colors():
        colors = []
        for dummy in range(len(models.Project.colors)):
            colors.append(models.get_next_color())
        return colors

    @override_settings()
    def test_get_next_color_cycles_no_cache(self):
        cache.delete('LAST_ASANA_COLOR')
        colors = self.cycle_colors()
        self.assertSequenceEqual(models.Project.colors, colors)

    @override_settings(CACHES=LOCAL_MEMORY_CACHE)
    def test_cached_color_cycles(self):
        cache.set('LAST_ASANA_COLOR', models.Project.colors[3])
        colors = self.cycle_colors()
        self.assertNotEqual(models.Project.colors, colors)
        self.assertSetEqual(set(models.Project.colors), set(colors))


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
    @patch('djasana.models.client_connect')
    def test_refresh_from_asana(self, mock_connect):
        mock_client = mock_connect.return_value
        task = fixtures.task(id=4)
        mock_client.tasks.find_by_id.return_value = task
        self.task.refresh_from_asana()
        self.assertTrue(mock_client.tasks.find_by_id.called)
        self.task.refresh_from_db()
        self.assertEqual(task['name'], self.task.name)

    @override_settings(ASANA_ACCESS_TOKEN='foo')
    @patch('djasana.models.client_connect')
    def test_add_comment(self, mock_connect):
        mock_client = mock_connect.return_value
        mock_client.tasks.add_comment.return_value = fixtures.story()
        self.task.add_comment(text='Test comment')
        self.assertTrue(mock_client.tasks.add_comment.called)


class UserModelTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = models.User.objects.create(remote_id=6, name='New User')

    @override_settings(ASANA_ACCESS_TOKEN='foo')
    @patch('djasana.models.client_connect')
    def test_refresh_from_asana(self, mock_connect):
        mock_client = mock_connect.return_value
        user = fixtures.user()
        mock_client.users.find_by_id.return_value = user
        self.user.refresh_from_asana()
        self.assertTrue(mock_client.users.find_by_id.called)
        self.user.refresh_from_db()
        self.assertEqual(user['name'], self.user.name)

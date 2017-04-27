import unittest
from django.test import override_settings, TestCase

from djasana.management.commands.sync_from_asana import Command
from djasana.models import Project, Task, Workspace, User
from djasana.tests.fixtures import project, task, workspace


def mock_connect():
    return unittest.mock.Mock()


@override_settings(ASANA_ACCESS_TOKEN='foo')
@override_settings(ASANA_WORKSPACE=None)
class SyncFromAsanaTestCase(TestCase):

    def setUp(self):
        self.command = Command()
        self.command.client = unittest.mock.MagicMock()
        self.command.client.workspaces.find_all.return_value = [workspace()]
        self.command.client.workspaces.find_by_id.return_value = workspace()
        self.command.client.projects.find_all.return_value = [project()]
        self.command.client.projects.find_by_id.return_value = project()
        self.command.client.tasks.find_all.return_value = [task()]
        self.command.client.tasks.find_by_id.return_value = task()

    def test_noinput_argument_only(self):
        self.command.handle(interactive=False)
        self.assertEqual(1, Workspace.objects.count())
        self.assertEqual(1, Project.objects.count())
        self.assertEqual(1, Task.objects.count())
        self.assertEqual(1, User.objects.count())

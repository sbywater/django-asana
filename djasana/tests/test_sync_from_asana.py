import unittest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings, TestCase

from djasana.management.commands.sync_from_asana import Command
from djasana.models import Attachment, Project, Story, Tag, Task, Team, Workspace, User
from djasana.tests.fixtures import attachment, project, story, tag, task, team, user, workspace


def mock_connect():
    return unittest.mock.Mock()


@override_settings(ASANA_ACCESS_TOKEN='foo')
@override_settings(ASANA_WORKSPACE=None)
class CommandArgumentsTestCase(TestCase):
    """Tests of command argument handling, that do not call Asana
    
    (adds coverage to add_arguments)
    """

    def test_bad_model(self):
        args = ['--noinput']
        options = {'model': ['foo']}
        with self.assertRaises(CommandError):
            call_command('sync_from_asana', *args, **options)


@override_settings(ASANA_ACCESS_TOKEN='foo')
@override_settings(ASANA_WORKSPACE=None)
class SyncFromAsanaTestCase(TestCase):
    """Tests that use mock returns from Asana"""

    def setUp(self):
        self.command = Command()
        self.command.client = unittest.mock.MagicMock()
        self.command.client.workspaces.find_all.return_value = [workspace()]
        self.command.client.workspaces.find_by_id.return_value = workspace()
        self.command.client.projects.find_all.return_value = [project()]
        self.command.client.projects.find_by_id.return_value = project()
        self.command.client.tasks.find_all.return_value = [task()]
        self.command.client.tasks.find_by_id.return_value = task()

    def test_good_sync(self):
        self.command.client.attachments.find_by_task.return_value = [attachment()]
        self.command.client.attachments.find_by_id.return_value = attachment()
        self.command.client.stories.find_by_task.return_value = [story()]
        self.command.client.stories.find_by_id.return_value = story()
        self.command.handle(interactive=False)
        self.assertEqual(1, Workspace.objects.count())
        self.assertEqual(1, Project.objects.count())
        self.assertEqual(1, Task.objects.count())
        self.assertEqual(1, User.objects.count())
        self.assertEqual(1, Attachment.objects.count())
        self.assertEqual(1, Story.objects.count())

    def test_good_workspace(self):
        self.command.handle(interactive=False, workspace=['Test Workspace'])
        self.assertEqual(1, Workspace.objects.count())

    def test_bad_workspace(self):
        with self.assertRaises(CommandError):
            self.command.handle(interactive=False, workspace=['foo'])

    def test_bad_workspaces(self):
        with self.assertRaises(CommandError):
            self.command.handle(interactive=False, workspace=['foo', 'bar'])

    def test_good_project(self):
        self.command.handle(interactive=False, project=['Test Project'])
        self.assertEqual(1, Project.objects.count())
        self.assertEqual(1, Task.objects.count())

    def test_bad_project(self):
        with self.assertRaises(CommandError):
            self.command.handle(interactive=False, project=['foo'])

    def test_bad_projects(self):
        with self.assertRaises(CommandError):
            self.command.handle(interactive=False, project=['foo', 'bar'])

    def test_skip_archived_project(self):
        self.command.client.projects.find_by_id.return_value = project(archived='true')
        self.command.handle(interactive=False)
        self.assertEqual(1, Project.objects.count())
        self.assertEqual(0, Task.objects.count())

    def test_sync_users(self):
        self.command.client.users.find_all.return_value = [user()]
        self.command.client.users.find_by_id.return_value = user()
        self.command.handle(interactive=False, model=['Workspace', 'User'])
        self.assertEqual(1, User.objects.count())

    def test_sync_tags(self):
        self.command.client.tags.find_by_workspace.return_value = [tag()]
        self.command.client.tags.find_by_id.return_value = tag()
        self.command.handle(interactive=False, model=['Workspace', 'Tag'])
        self.assertEqual(1, Tag.objects.count())

    def test_sync_teams(self):
        self.command.client.teams.find_by_organization.return_value = [team()]
        self.command.client.teams.find_by_id.return_value = team()
        self.command.handle(interactive=False, model=['Workspace', 'Team'])
        self.assertEqual(1, Team.objects.count())

    def test_no_commit(self):
        self.command.handle(interactive=False, nocommit=True)
        self.assertFalse(Workspace.objects.exists())
        self.assertFalse(Project.objects.exists())
        self.assertFalse(Task.objects.exists())
        self.assertFalse(User.objects.exists())

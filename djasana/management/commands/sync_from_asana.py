import logging

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils import six

from djasana.connect import client_connect
from djasana import models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import data from Asana and insert/update/delete model instances'
    client = client_connect()

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', action='store_false', dest='interactive', default=True,
            help='If provided, no prompts will be issued to the user and the data will be synced.'
        )
        parser.add_argument(
            "-w", "--workspace", action="append", default=[],
            help='Sync only the named workspace (can be used multiple times). '
                 'By default all workspaces will be updated from Asana.'
        )
        parser.add_argument(
            "-p", "--project", action="append", default=[],
            help='Sync only the named project (can be used multiple times). '
                 'By default all projects will be updated from Asana.'
        )
        parser.add_argument(
            "-m", "--model", action="append", default=[],
            help='Sync only the named model (can be used multiple times). '
                 'By default all models will be updated from Asana.'
        )
        parser.add_argument(
            '--nocommit', action='store_false', dest='commit',
            default=True, help='Will pass commit=False to the backend.'
        )

    def handle(self, *args, **options):
        if options.get('interactive', True):
            self.stdout.write(
                'WARNING: This will irreparably syncronize your local database from Asana.')
            yes_or_no = six.moves.input("Are you sure you wish to continue? [y/N] ")
            if not yes_or_no.lower().startswith('y'):
                self.stdout.write("No action taken.")
                return
        commit = not options.get('nocommit')
        models_ = options.get('model')
        if models_:
            app_models = list(apps.get_app_config('djasana').get_models())
            model_names = [model_.__name__.lower() for model_ in app_models]
            for model in models_:
                if model.lower() not in model_names:
                    raise CommandError('{} is not an Asana model'.format(model))

        if options.get('verbosity') >= 1:
            self.stdout.write("Syncronizing data from Asana.")
        workspaces = options.get('workspace')
        workspace_ids = self._get_workspace_ids(workspaces)

        host_choices = set()
        status_choices = set()
        layout_choices = set()
        type_choices = set()
        assignee_status_choices = set()

        for workspace_id in workspace_ids:

            workspace_dict = self.client.workspaces.find_by_id(workspace_id)
            logger.debug('Sync workspace %s', workspace_dict['name'])
            logger.debug(workspace_dict)
            remote_id = workspace_dict.pop('id')
            if commit:
                workspace_dict.pop('email_domains')
                models.Workspace.objects.update_or_create(
                    remote_id=remote_id, defaults=workspace_dict)
            projects = options.get('project')
            project_ids = self._get_project_ids(projects, workspace_id)
            if workspace_id != self.client.options['workspace_id']:
                self.client.options['workspace_id'] = workspace_id

            for project_id in project_ids:

                project_dict = self.client.projects.find_by_id(project_id)
                logger.debug('Sync project %s', project_dict['name'])
                logger.debug(project_dict)
                remote_id = project_dict.pop('id')
                if commit:
                    models.Project.objects.update_or_create(
                        remote_id=remote_id, defaults=project_dict)
                status_choices.add(project_dict['current_status'])
                layout_choices.add(project_dict['layout'])

                for task in self.client.tasks.find_all({'project': project_id}):

                    task_dict = self.client.tasks.find_by_id(task['id'])
                    logger.debug('Sync task %s', task_dict['name'])
                    logger.debug(task_dict)
                    assignee_status_choices.add(task_dict['assignee_status'])

                    if models.Attachment in models_:
                        for attachment in self.client.attachments.find_by_task(task['id']):
                            attachment_dict = self.client.attachments.find_by_id(attachment['id'])
                            logger.debug(attachment_dict)
                            host_choices.add(attachment_dict['host'])
                    if models.Story in models_:
                        for story in self.client.stories.find_by_task(task['id']):
                            story_dict = self.client.stories.find_by_id(story['id'])
                            logger.debug(story_dict)
                            type_choices.add(story_dict['type'])

            if models.User in models_:

                for user in self.client.users.find_all({'workspace': workspace_id}):

                    user_dict = self.client.user.find_by_id(user['id'])
                    logger.debug(user_dict)

            if models.Tag in models_:
                for tag in self.client.tags.find_by_worspace(workspace_id):

                    tag_dict = self.client.tag.find_by_id(tag['id'])
                    logger.debug(tag_dict)

            if models.Team in models_:
                for team in self.client.teams.find_by_organization(workspace_id):
                    team_dict = self.client.teams.find_by_id(team['id'])
                    logger.debug(team_dict)
            logger.debug('Unique host choices: %s', host_choices)
            logger.debug('Unique status choices: %s', status_choices)
            logger.debug('Unique layout choices: %s', layout_choices)
            logger.debug('Unique type choices: %s', type_choices)
            logger.debug('Unique assignee status choices: %s', assignee_status_choices)

    def _get_workspace_ids(self, workspaces):
        workspace_ids = []
        bad_list = []
        for workspace in self.client.workspaces.find_all():
            if workspaces:
                if workspace['name'] in workspaces:
                    workspace_ids.append(workspace['id'])
                else:
                    bad_list.append(workspace)
            else:
                workspace_ids.append(workspace['id'])
        if bad_list:
            if len(bad_list) == 1:
                raise CommandError('{} is not an Asana workspace'.format(bad_list[0]))
            else:
                raise CommandError('Specified workspaces are not valid: {}'.format(
                    ', '.join(bad_list)))
        return workspace_ids

    @staticmethod
    def _save_workspace(workspace, workspace_ids):
        logger.debug(workspace)
        workspace_ids.append(workspace['id'])

    def _get_project_ids(self, projects, workspace_id):
        project_ids = []
        bad_list = []
        for project in self.client.projects.find_all({'workspace': workspace_id}):
            if projects:
                if project['name'] in projects:
                    project_ids.append(project['id'])
                else:
                    bad_list.append(project)
            else:
                project_ids.append(project['id'])
        if bad_list:
            if len(bad_list) == 1:
                raise CommandError('{} is not an Asana project'.format(bad_list[0]))
            else:
                raise CommandError('Specified projects are not valid: {}'.format(
                    ', '.join(bad_list)))
        return project_ids

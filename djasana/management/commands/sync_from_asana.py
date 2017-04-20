"""The django management command sync_from_asana"""
import logging

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils import six

from djasana.connect import client_connect
from djasana.models import Attachment, Project, Story, Tag, Task, Team, User, Workspace

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Sync data from Asana to the database"""
    help = 'Import data from Asana and insert/update model instances'
    client = client_connect()
    commit = True

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
        self.commit = not options.get('nocommit')
        models = self._get_models(options)

        if options.get('verbosity') >= 1:
            self.stdout.write("Syncronizing data from Asana.")
        workspaces = options.get('workspace')
        workspace_ids = self._get_workspace_ids(workspaces)
        projects = options.get('project')

        choices = {  # collect unique values for choices; output in debug logging
            'host': set(),
            'status': set(),
            'layout': set(),
            'type': set(),
            'assignee_status': set(),
        }
        for workspace_id in workspace_ids:
            self._sync_workspace_id(workspace_id, projects, models, choices)

        for key, value in choices.items():
            logger.debug('Unique %s choices: %s', key, value)

    @staticmethod
    def _get_models(options):
        """Returns a list of models to sync"""
        models = options.get('model')
        app_models = list(apps.get_app_config('djasana').get_models())
        if models:
            model_names = [model_.__name__.lower() for model_ in app_models]
            for model in models:
                if model.lower() not in model_names:
                    raise CommandError('{} is not an Asana model'.format(model))
        else:
            models = app_models
        return models

    def _get_workspace_ids(self, workspaces):
        workspace_ids = []
        bad_list = []

        workspaces_ = self.client.workspaces.find_all()
        if workspaces:
            for workspace in workspaces:
                for wks in workspaces_:
                    if workspace == wks['name']:
                        workspace_ids.append(wks['id'])
                        break
                else:
                    bad_list.append(workspace)
        else:
            workspace_ids = [wks['id'] for wks in workspaces_]
        if bad_list:
            if len(bad_list) == 1:
                raise CommandError('{} is not an Asana workspace'.format(workspaces[0]))
            else:
                raise CommandError('Specified workspaces are not valid: {}'.format(
                    ', '.join(bad_list)))
        return workspace_ids

    def _get_project_ids(self, projects, workspace_id):
        project_ids = []
        bad_list = []

        projects_ = self.client.projects.find_all({'workspace': workspace_id})
        if projects:
            for project in projects:
                for prj in projects_:
                    if project == prj['name']:
                        project_ids.append(prj['id'])
                        break
                else:
                    bad_list.append(project)
        else:
            project_ids = [prj['id'] for prj in projects_]
        if bad_list:
            if len(bad_list) == 1:
                raise CommandError('{} is not an Asana project'.format(bad_list[0]))
            else:
                raise CommandError('Specified projects are not valid: {}'.format(
                    ', '.join(bad_list)))
        return project_ids

    @staticmethod
    def _save_workspace(workspace, workspace_ids):
        logger.debug(workspace)
        workspace_ids.append(workspace['id'])

    def _sync_project_id(self, project_id, workspace, models, choices):
        project_dict = self.client.projects.find_by_id(project_id)
        logger.debug('Sync project %s', project_dict['name'])
        logger.debug(project_dict)
        if self.commit:
            remote_id = project_dict.pop('id')
            if project_dict['owner']:
                user = User.objects.get_or_create(
                    remote_id=project_dict['owner']['id'],
                    defaults={'name': project_dict['owner']['name']})[0]
                project_dict['owner'] = user
            team = Team.objects.get_or_create(
                remote_id=project_dict['team']['id'],
                defaults={'name': project_dict['team']['name']})[0]
            project_dict['team'] = team
            project_dict['workspace'] = workspace
            members_dict = project_dict.pop('members')
            followers_dict = project_dict.pop('followers')
            project = Project.objects.update_or_create(
                remote_id=remote_id, defaults=project_dict)[0]
            member_ids = [member['id'] for member in members_dict]
            members = User.objects.filter(id__in=member_ids)
            project.members.set(members)
            follower_ids = [follower['id'] for follower in followers_dict]
            followers = User.objects.filter(id__in=follower_ids)
            project.followers.set(followers)

        choices['status'].add(project_dict['current_status'])
        choices['layout'].add(project_dict['layout'])

        for task in self.client.tasks.find_all({'project': project_id}):
            self._sync_task(task, project, models, choices)

        self.stdout.write(
            self.style.SUCCESS('Successfully synced project {}.'.format(project.name)))

    def _sync_tag(self, tag):
        tag_dict = self.client.tags.find_by_id(tag['id'])
        logger.debug(tag_dict)
        if self.commit:
            remote_id = tag_dict.pop('id')
            Tag.objects.get_or_create(
                remote_id=remote_id,
                defaults=tag_dict)

    def _sync_task(self, task, project, models, choices):
        task_dict = self.client.tasks.find_by_id(task['id'])
        logger.debug('Sync task %s', task_dict['name'])
        logger.debug(task_dict)
        choices['assignee_status'].add(task_dict['assignee_status'])

        if Attachment in models:
            for attachment in self.client.attachments.find_by_task(task['id']):
                attachment_dict = self.client.attachments.find_by_id(attachment['id'])
                logger.debug(attachment_dict)
                remote_id = attachment_dict.pop('id')
                Attachment.objects.get_or_create(remote_id=remote_id, defaults=attachment_dict)
                choices['host_choices'].add(attachment_dict['host'])
        if Task in models and self.commit:
            remote_id = task_dict.pop('id')
            if task_dict['assignee']:
                user = User.objects.get_or_create(
                    remote_id=task_dict['assignee']['id'],
                    defaults={'name': task_dict['assignee']['name']})[0]
                task_dict['assignee'] = user
            task_dict.pop('hearts', None)
            task_dict.pop('memberships')
            task_dict.pop('projects')
            task_dict.pop('workspace')
            followers_dict = task_dict.pop('followers')
            tags_dict = task_dict.pop('tags')
            task_ = Task.objects.update_or_create(
                remote_id=remote_id, defaults=task_dict)[0]
            follower_ids = [follower['id'] for follower in followers_dict]
            followers = User.objects.filter(id__in=follower_ids)
            task_.followers.set(followers)
            for tag_ in tags_dict:
                tag = Tag.objects.get_or_create(
                    remote_id=tag_['id'],
                    defaults={'name': tag_['name']})[0]
                task_.tags.add(tag)
            task_.projects.add(project)
        if Story in models:
            for story in self.client.stories.find_by_task(task['id']):
                story_dict = self.client.stories.find_by_id(story['id'])
                logger.debug(story_dict)
                remote_id = story_dict.pop('id')
                if story_dict['created_by']:
                    user = User.objects.get_or_create(
                        remote_id=story_dict['created_by']['id'],
                        defaults={'name': story_dict['created_by']['name']})[0]
                    story_dict['created_by'] = user
                story_dict.pop('hearts', None)
                story_dict['target_id'] = story_dict['target']['id']
                story_dict.pop('target')
                import pdb; pdb.set_trace()
                Story.objects.get_or_create(remote_id=remote_id, defaults=story_dict)
                choices['type'].add(story_dict['type'])

    def _sync_team(self, team):
        team_dict = self.client.teams.find_by_id(team['id'])
        logger.debug(team_dict)
        if self.commit:
            remote_id = team_dict.pop('id')
            organization = team_dict.pop('organization')
            team_dict['organization_id'] = organization['id']
            team_dict['organization_name'] = organization['name']
            Team.objects.get_or_create(
                remote_id=remote_id,
                defaults=team_dict)

    def _sync_user(self, user, workspace):
        user_dict = self.client.users.find_by_id(user['id'])
        logger.debug(user_dict)
        if self.commit:
            remote_id = user_dict.pop('id')
            user_dict.pop('workspaces')
            if user_dict['photo']:
                user_dict['photo'] = user_dict['photo']['image_128x128']
            user = User.objects.get_or_create(
                remote_id=remote_id,
                defaults=user_dict)[0]
            user.workspaces.add(workspace)

    def _sync_workspace_id(self, workspace_id, projects, models, choices):
        workspace_dict = self.client.workspaces.find_by_id(workspace_id)
        logger.debug('Sync workspace %s', workspace_dict['name'])
        logger.debug(workspace_dict)
        if Workspace in models and self.commit:
            remote_id = workspace_dict.pop('id')
            workspace_dict.pop('email_domains')
            workspace = Workspace.objects.update_or_create(
                remote_id=remote_id, defaults=workspace_dict)[0]
        else:
            workspace = None
        project_ids = self._get_project_ids(projects, workspace_id)
        if workspace_id != self.client.options['workspace_id']:
            self.client.options['workspace_id'] = workspace_id

        if User in models:
            for user in self.client.users.find_all({'workspace': workspace_id}):
                self._sync_user(user, workspace)

        if Tag in models:
            for tag in self.client.tags.find_by_workspace(workspace_id):
                self._sync_tag(tag)

        if Team in models:
            for team in self.client.teams.find_by_organization(workspace_id):
                self._sync_team(team)

        if Project in models:
            for project_id in project_ids:
                self._sync_project_id(project_id, workspace, models, choices)

        if workspace:
            self.stdout.write(
                self.style.SUCCESS('Successfully synced workspace {}.'.format(workspace.name)))

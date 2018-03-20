"""The django management command sync_from_asana"""
import logging

from asana.error import NotFoundError, InvalidTokenError, ForbiddenError
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils import six

from djasana.connect import client_connect
from djasana.models import (
    Attachment, Project, Story, SyncToken, Tag, Task, Team, User, Webhook, Workspace)
from djasana.settings import settings
from djasana.utils import set_webhook

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Sync data from Asana to the database"""
    help = 'Import data from Asana and insert/update model instances'
    commit = True
    client = None
    process_archived = False

    @staticmethod
    def get_client():
        return client_connect()

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
            "-mx", "--model-exclude", action="append", default=[],
            help='Exclude the named model (can be used multiple times).'
        )
        parser.add_argument(
            "-a", "--archive", action="store_false", dest='archive',
            help='Sync project tasks etc. even if the project is archived. '
                 'By default, only tasks of unarchived projects are updated from Asana. '
                 'Regardless of this setting, the project itself will be updated, '
                 'perhaps becoming marked as archived. '
        )
        parser.add_argument(
            '--nocommit', action='store_false', dest='commit',
            default=True, help='Will not commit changes to the database.'
        )

    def handle(self, *args, **options):
        self.commit = not options.get('nocommit')
        if self.commit and options.get('interactive', True):
            self.stdout.write(
                'WARNING: This will irreparably synchronize your local database from Asana.')
            if not self._confirm():
                self.stdout.write("No action taken.")
                return
        self.process_archived = options.get('archive')
        models = self._get_models(options)
        if options.get('verbosity', 0) >= 1:
            message = "Synchronizing data from Asana."
            self.stdout.write(message)
            logger.info(message)
        workspaces = options.get('workspace') or []
        if settings.ASANA_WORKSPACE:
            workspaces.append(settings.ASANA_WORKSPACE)
        # Allow client to be mocked:
        self.client = self.client or self.get_client()
        workspace_ids = self._get_workspace_ids(workspaces)
        projects = options.get('project')

        for workspace_id in workspace_ids:
            self._sync_workspace_id(workspace_id, projects, models)

    @staticmethod
    def _confirm():
        yes_or_no = six.moves.input("Are you sure you wish to continue? [y/N] ")
        return yes_or_no.lower().startswith('y')

    @staticmethod
    def _get_models(options):
        """Returns a list of models to sync"""
        models = options.get('model')
        models_exclude = options.get('model_exclude')
        app_models = list(apps.get_app_config('djasana').get_models())
        if models:
            good_models = []
            model_names = [model_.__name__.lower() for model_ in app_models]
            for model in models:
                try:
                    index = model_names.index(model.lower())
                except ValueError:
                    raise CommandError('{} is not an Asana model'.format(model))
                else:
                    good_models.append(app_models[index])
            models = good_models
        else:
            models = app_models
        if models_exclude:
            models = [model
                      for model in models
                      if model.__name__.lower() not in [m.lower() for m in models_exclude]]
        return models

    def _check_sync_project_id(self, project_id, workspace, models):
        """If we have a valid sync token for this project sync new events else sync the project"""
        new_sync = False
        try:
            sync_token = SyncToken.objects.get(project_id=project_id)
            try:
                events = self.client.events.get({'resource': project_id, 'sync': sync_token.sync})
                self._process_events(project_id, events, workspace, models)
                self._set_webhook(workspace, project_id)
                return
            except InvalidTokenError as error:
                sync_token.sync = error.sync
                sync_token.save()
        except SyncToken.DoesNotExist:
            try:
                self.client.events.get({'resource': project_id})
            except InvalidTokenError as error:
                new_sync = error.sync
        is_archived = self._sync_project_id(project_id, workspace, models)
        if not is_archived:
            self._set_webhook(workspace, project_id)
        if new_sync:
            SyncToken.objects.create(project_id=project_id, sync=new_sync)

    def _get_workspace_ids(self, workspaces):
        workspace_ids = []
        bad_list = []
        workspaces_ = self.client.workspaces.find_all()
        if workspaces:
            for workspace in workspaces:
                for wks in workspaces_:
                    if workspace == str(wks['id']) or workspace == wks['name']:
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
        # Return newer projects first so they get synced earlier
        return sorted(workspace_ids, reverse=True)

    def _get_project_ids(self, projects, workspace_id):
        project_ids = []
        bad_list = []

        projects_ = self.client.projects.find_all({'workspace': workspace_id})
        if projects:
            for project in projects:
                for prj in projects_:
                    if project == str(prj['id']) or project == prj['name']:
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
        # Return newer projects first so they get synced earlier
        return sorted(project_ids, reverse=True)

    def _set_webhook(self, workspace, project_id):
        """Sets a webhook if the setting is configured and a webhook does not currently exist"""
        if self.commit and settings.DJASANA_WEBHOOK_URL:
            webhooks = [webhook for webhook in self.client.webhooks.get_all({
                'workspace': workspace.remote_id, 'resource': project_id})]
            if webhooks:
                # If there is exactly one, and it is active, we are good to go,
                # else delete them and start a new one.
                webhooks_ = Webhook.objects.filter(project_id=project_id)
                if len(webhooks) == webhooks_.count() == 1:
                    if webhooks[0]['active']:
                        return
                for webhook in webhooks:
                    self.client.webhooks.delete_by_id(webhook['id'])
                Webhook.objects.filter(id__in=webhooks_.values_list('id', flat=True)[1:]).delete()
            set_webhook(self.client, project_id)

    def _process_events(self, project_id, events, workspace, models):
        project = Project.objects.get(remote_id=project_id)
        ignored_tasks = 0
        for event in events['data']:
            if event['type'] == 'project':
                if Project in models:
                    if event['action'] == 'removed':
                        Project.objects.get(remote_id=event['resource']['id']).delete()
                    else:
                        self._sync_project_id(project_id, workspace, models)
                else:
                    ignored_tasks += 1
            elif event['type'] == 'task':
                if Task in models:
                    if event['action'] == 'removed':
                        Task.objects.get(remote_id=event['resource']['id']).delete()
                    else:
                        self._sync_task(event['resource'], project, models)
                else:
                    ignored_tasks += 1
            elif event['type'] == 'story':
                if Story in models:
                    self._sync_story(event['resource'])
                else:
                    ignored_tasks += 1
        tasks_done = len(events['data']) - ignored_tasks
        message = 'Successfully synced {0} events for project {1}.'.format(
            tasks_done, project.name)
        if ignored_tasks:
            message += ' {0} events ignored for excluded models.'.format(ignored_tasks)
        self.stdout.write(self.style.SUCCESS(message))
        logger.info(message)

    def _sync_project_id(self, project_id, workspace, models):
        """Sync this project by polling it. Returns boolean 'is archived?'"""
        project_dict = self.client.projects.find_by_id(project_id)
        logger.debug('Sync project %s', project_dict['name'])
        logger.debug(project_dict)
        if self.commit:
            remote_id = project_dict.pop('id')
            if project_dict['owner']:
                owner = project_dict.pop('owner')
                User.objects.get_or_create(remote_id=owner['id'], defaults={'name': owner['name']})
                project_dict['owner_id'] = owner['id']
            team = project_dict.pop('team')
            Team.objects.get_or_create(remote_id=team['id'], defaults={'name': team['name']})
            project_dict['team_id'] = team['id']
            project_dict['workspace'] = workspace
            # Convert string to boolean:
            project_dict['archived'] = project_dict['archived'] == 'true'
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
        else:
            project = None

        if Task in models and not project_dict['archived'] or self.process_archived:
            for task in self.client.tasks.find_all({'project': project_id}):
                self._sync_task(task, project, models)

        if project:
            message = 'Successfully synced project {}.'.format(project.name)
            self.stdout.write(self.style.SUCCESS(message))
            logger.info(message)
        return project_dict['archived']

    def _sync_story(self, story):
        try:
            story_dict = self.client.stories.find_by_id(story['id'])
        except NotFoundError as error:
            logger.info(error.response)
            return
        logger.debug(story_dict)
        remote_id = story_dict.pop('id')
        if story_dict['created_by']:
            user = User.objects.get_or_create(
                remote_id=story_dict['created_by']['id'],
                defaults={'name': story_dict['created_by']['name']})[0]
            story_dict['created_by'] = user
        if story_dict['target']:
            story_dict['target'] = story_dict['target']['id']
        for key in ('hearts', 'liked', 'likes', 'num_likes'):
            story_dict.pop(key, None)
        if 'text' in story_dict:
            story_dict['text'] = story_dict['text'][:1024]  # Truncate text if too long
        Story.objects.get_or_create(remote_id=remote_id, defaults=story_dict)

    def _sync_tag(self, tag):
        tag_dict = self.client.tags.find_by_id(tag['id'])
        logger.debug(tag_dict)
        if self.commit:
            remote_id = tag_dict.pop('id')
            Tag.objects.get_or_create(
                remote_id=remote_id,
                defaults=tag_dict)

    def _sync_task(self, task, project, models, skip_subtasks=False):
        """Sync this task and parent its subtasks

        For parents and subtasks, this method is called recursively, so skip_subtasks True is
        passed when syncing a parent task from a subtask.
        """
        try:
            task_dict = self.client.tasks.find_by_id(task['id'])
        except (ForbiddenError, NotFoundError):
            try:
                Task.objects.get(remote_id=task['id']).delete()
            except Task.DoesNotExist:
                pass
            return
        logger.debug('Sync task %s', task_dict['name'])
        logger.debug(task_dict)

        if Task in models and self.commit:
            remote_id = task_dict.pop('id')
            if task_dict['assignee']:
                user = User.objects.get_or_create(
                    remote_id=task_dict['assignee']['id'],
                    defaults={'name': task_dict['assignee']['name']})[0]
                task_dict['assignee'] = user
            for key in (
                    'hearts', 'liked', 'likes', 'num_likes',
                    'memberships', 'projects', 'workspace'):
                task_dict.pop(key, None)
            parent = task_dict.pop('parent', None)
            if parent:
                # If this is a task we already know about, assume it was just synced.
                parent_id = parent['id']
                if not Task.objects.filter(remote_id=parent_id).exists():
                    self._sync_task(parent, project, models, skip_subtasks=True)
                task_dict['parent_id'] = parent_id
            followers_dict = task_dict.pop('followers')
            tags_dict = task_dict.pop('tags')
            task_ = Task.objects.update_or_create(
                remote_id=remote_id, defaults=task_dict)[0]
            if not skip_subtasks:
                subtasks = self.client.tasks.subtasks(task['id'])
                for subtask in subtasks:
                    self._sync_task(subtask, project, models)
            follower_ids = [follower['id'] for follower in followers_dict]
            followers = User.objects.filter(id__in=follower_ids)
            task_.followers.set(followers)
            if Tag in models:
                for tag_ in tags_dict:
                    tag = Tag.objects.get_or_create(
                        remote_id=tag_['id'],
                        defaults={'name': tag_['name']})[0]
                    task_.tags.add(tag)
            task_.projects.add(project)
        if Attachment in models and self.commit:
            for attachment in self.client.attachments.find_by_task(task['id']):
                attachment_dict = self.client.attachments.find_by_id(attachment['id'])
                logger.debug(attachment_dict)
                remote_id = attachment_dict.pop('id')
                if attachment_dict['parent']:
                    attachment_dict['parent'] = task_
                Attachment.objects.get_or_create(remote_id=remote_id, defaults=attachment_dict)
        if Story in models and self.commit:
            for story in self.client.stories.find_by_task(task['id']):
                self._sync_story(story)

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
            user = User.objects.update_or_create(
                remote_id=remote_id,
                defaults=user_dict)[0]
            if workspace:
                user.workspaces.add(workspace)

    def _sync_workspace_id(self, workspace_id, projects, models):
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
                self._check_sync_project_id(project_id, workspace, models)

        if workspace:
            message = 'Successfully synced workspace {}.'.format(workspace.name)
            self.stdout.write(self.style.SUCCESS(message))
            logger.info(message)

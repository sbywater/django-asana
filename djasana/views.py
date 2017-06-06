import logging

from asana.error import ForbiddenError, NotFoundError
from braces.views import JSONRequestResponseMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.generic import View

from .connect import client_connect
from .models import Attachment, Project, Story, Tag, Task, Team, User, Webhook
from .utils import sign_sha256_hmac

logger = logging.getLogger(__name__)


class WebhookView(JSONRequestResponseMixin, View):
    client = None

    def post(self, request, *_, **kwargs):
        remote_id = kwargs.pop('remote_id')
        project = get_object_or_404(Project, remote_id=remote_id)
        if 'X-Hook-Secret' in request.META:
            return self._process_secret(request, request.META['X-Hook-Secret'], remote_id)
        if 'X-Hook-Signature' not in request.META:
            return HttpResponseForbidden
        signature = request.META['X-Hook-Signature']
        if len(signature) != 44 or not self.request_json:
            return HttpResponseForbidden
        try:
            webhook = Webhook.objects.get(project_id=remote_id)
        except Webhook.DoesNotExist:
            return HttpResponseForbidden
        target_signature = sign_sha256_hmac(webhook.secret, self.request.body)
        if signature != target_signature:
            return HttpResponseForbidden
        if self.request_json['events']:
            self._process_events(self.request_json['events'], project)
        return HttpResponse()

    @staticmethod
    def _process_secret(request, secret, remote_id):
        """Process a request from Asana to establish a web hook"""
        if len(secret) != 64:
            return HttpResponseForbidden
        try:
            webhook = Webhook.objects.get(project_id=remote_id)
        except Webhook.DoesNotExist:
            Webhook.objects.create(project_id=remote_id, secret=secret)
        else:
            if webhook.secret != secret:
                return HttpResponseForbidden
        response = HttpResponse()
        response['X-Hook-Secret'] = secret
        return response

    def _process_events(self, events, project):
        self.client = client_connect()
        for event in events:
            if event['type'] == 'project':
                if event['action'] == 'removed':
                    Project.objects.get(remote_id=event['resource']['id']).delete()
                else:
                    self._sync_project(project)
            elif event['type'] == 'task':
                if event['action'] == 'removed':
                    Task.objects.get(remote_id=event['resource']['id']).delete()
                else:
                    self._sync_task_id(event['resource'], project)
            elif event['type'] == 'story':
                self._sync_story_id(event['resource'])

    def _sync_project(self, project):
        project_dict = self.client.projects.find_by_id(project.remote_id)
        logger.debug('Sync project %s', project_dict['name'])
        logger.debug(project_dict)
        project_dict.pop('id')
        if project_dict['owner']:
            owner = project_dict.pop('owner')
            User.objects.get_or_create(remote_id=owner['id'], defaults={'name': owner['name']})[0]
            project_dict['owner_id'] = owner['id']
        team = project_dict.pop('team')
        Team.objects.get_or_create(remote_id=team['id'], defaults={'name': team['name']})
        project_dict['team_id'] = team['id']
        # Convert string to boolean:
        project_dict['archived'] = project_dict['archived'] == 'true'
        members_dict = project_dict.pop('members')
        followers_dict = project_dict.pop('followers')
        Project.objects.update_or_create(
            remote_id=project.remote_id, defaults=project_dict)
        member_ids = [member['id'] for member in members_dict]
        members = User.objects.filter(id__in=member_ids)
        project.members.set(members)
        follower_ids = [follower['id'] for follower in followers_dict]
        followers = User.objects.filter(id__in=follower_ids)
        project.followers.set(followers)

    def _sync_story_id(self, story_id):
        try:
            story_dict = self.client.stories.find_by_id(story_id)
        except NotFoundError as error:
            logger.error('This is probably a temporary connection issue; please resync')
            raise error
        logger.debug(story_dict)
        story_dict.pop('id')
        if story_dict['created_by']:
            user = User.objects.get_or_create(
                remote_id=story_dict['created_by']['id'],
                defaults={'name': story_dict['created_by']['name']})[0]
            story_dict['created_by'] = user
        story_dict.pop('hearts', None)
        story_dict['target'] = story_dict['target']['id']
        Story.objects.get_or_create(remote_id=story_id, defaults=story_dict)

    def _sync_task_id(self, task_id, project):
        try:
            task_dict = self.client.tasks.find_by_id(task_id)
        except ForbiddenError:
            try:
                Task.objects.get(remote_id=task_id).delete()
            except Task.DoesNotExist:
                pass
            return
        logger.debug('Sync task %s', task_dict['name'])
        logger.debug(task_dict)

        task_dict.pop('id')
        if task_dict['assignee']:
            user = User.objects.get_or_create(
                remote_id=task_dict['assignee']['id'],
                defaults={'name': task_dict['assignee']['name']})[0]
            task_dict['assignee'] = user
        task_dict.pop('hearts', None)
        task_dict.pop('memberships')
        task_dict.pop('projects')
        task_dict.pop('workspace')
        if task_dict['parent']:
            self._sync_task_id(task_dict['parent']['id'], project)
        followers_dict = task_dict.pop('followers')
        tags_dict = task_dict.pop('tags')
        task = Task.objects.update_or_create(
            remote_id=task_id, defaults=task_dict)[0]
        follower_ids = [follower['id'] for follower in followers_dict]
        followers = User.objects.filter(id__in=follower_ids)
        task.followers.set(followers)
        for tag_ in tags_dict:
            tag = Tag.objects.get_or_create(
                remote_id=tag_['id'],
                defaults={'name': tag_['name']})[0]
            task.tags.add(tag)
        task.projects.add(project)

        for attachment in self.client.attachments.find_by_task(task_id):
            attachment_dict = self.client.attachments.find_by_id(attachment['id'])
            logger.debug(attachment_dict)
            remote_id = attachment_dict.pop('id')
            if attachment_dict['parent']:
                attachment_dict['parent'] = task
            Attachment.objects.get_or_create(remote_id=remote_id, defaults=attachment_dict)
        for story in self.client.stories.find_by_task(task_id):
            self._sync_story_id(story['id'])

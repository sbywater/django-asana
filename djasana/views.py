import logging

from asana.error import ForbiddenError, NotFoundError
from braces.views import JSONRequestResponseMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from requests.packages.urllib3.exceptions import RequestError

from .connect import client_connect
from .models import Attachment, Project, Task, Team, User, Webhook
from .utils import sign_sha256_hmac, sync_story, sync_task

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(JSONRequestResponseMixin, View):
    """Receives authenticated webhooks from Asana on changes to projects, tasks, and stories."""
    client = None

    def post(self, request, *_, **kwargs):
        """Authenticates a request and processes a collection of events."""
        remote_id = kwargs.pop('remote_id')
        project = get_object_or_404(Project, remote_id=remote_id)
        secret = request.META.get('X-Hook-Secret', request.META.get('HTTP_X_HOOK_SECRET'))
        if secret:
            return self._process_secret(request, secret, remote_id)
        signature = request.META.get('X-Hook-Signature', request.META.get('HTTP_X_HOOK_SIGNATURE'))
        if not signature:
            logger.debug('No signature')
            return HttpResponseForbidden()
        if len(signature) != 64:
            logger.debug('Signature of length %s not allowed', len(signature))
        if not self.request_json:
            logger.debug('No json payload')
            return HttpResponseForbidden()
        logger.debug(self.request_json)
        webhook = Webhook.objects.filter(project_id=remote_id).order_by('id').last()
        if not webhook:
            logger.debug('No matching webhook')
            return HttpResponseForbidden()
        target_signature = sign_sha256_hmac(webhook.secret, self.request.body)
        if signature != target_signature:
            logger.debug('Signature mismatch')
            return HttpResponseForbidden()
        else:
            logger.debug('Signatures match!!')
        if self.request_json['events']:
            self._process_events(self.request_json['events'], project)
        return HttpResponse()

    @staticmethod
    def _process_secret(request, secret, remote_id):
        """Process a request from Asana to establish a web hook"""
        logger.debug('Processing secret')
        if len(secret) not in (64, 32):
            logger.debug('Secret of length %s not allowed', len(secret))
            return HttpResponseForbidden()
        webhook = Webhook.objects.filter(project_id=remote_id).last()
        if not webhook:
            Webhook.objects.create(project_id=remote_id, secret=secret)
        else:
            if webhook.secret != secret:
                webhook.secret = secret
                webhook.save()
        response = HttpResponse()
        response['X-Hook-Secret'] = secret
        logger.debug('Secret accepted')
        return response

    def _process_events(self, events, project):
        logger.debug('Processing events')
        self.client = client_connect()
        for event in events:
            if event['action'] == 'sync_error':
                logger.warning(event['message'])
            elif event['type'] == 'project':
                if event['action'] == 'removed':
                    Project.objects.get(remote_id=event['resource']).delete()
                else:
                    self._sync_project(project)
            elif event['type'] == 'task':
                if event['action'] == 'removed':
                    Task.objects.get(remote_id=event['resource']).delete()
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
            User.objects.get_or_create(remote_id=owner['id'], defaults={'name': owner['name']})
            project_dict['owner_id'] = owner['id']
        team = project_dict.pop('team')
        Team.objects.get_or_create(remote_id=team['id'], defaults={'name': team['name']})
        project_dict['workspace_id'] = project_dict.pop('workspace')['id']
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
        except (RequestError, NotFoundError) as error:
            logger.warning('This is probably a temporary connection issue; please sync: %s', error)
            return
        except ForbiddenError:
            return
        logger.debug(story_dict)
        story_dict.pop('id')
        sync_story(story_id, story_dict)

    def _sync_task_id(self, task_id, project):
        try:
            task_dict = self.client.tasks.find_by_id(task_id)
        except (ForbiddenError, NotFoundError):
            try:
                Task.objects.get(remote_id=task_id).delete()
            except Task.DoesNotExist:
                pass
            return
        logger.debug('Sync task %s', task_dict['name'])
        logger.debug(task_dict)
        task_dict.pop('id')
        if task_dict['parent']:
            self._sync_task_id(task_dict['parent']['id'], project)
            task_dict['parent_id'] = task_dict.pop('parent')['id']
        task = sync_task(task_id, task_dict, project, sync_tags=True)
        for attachment in self.client.attachments.find_by_task(task_id):
            attachment_dict = self.client.attachments.find_by_id(attachment['id'])
            logger.debug(attachment_dict)
            remote_id = attachment_dict.pop('id')
            if attachment_dict['parent']:
                attachment_dict['parent'] = task
            Attachment.objects.get_or_create(remote_id=remote_id, defaults=attachment_dict)

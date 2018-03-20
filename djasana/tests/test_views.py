import json
from unittest.mock import patch

import django
from asana.error import ForbiddenError
from django.http import Http404
from django.test import override_settings, TestCase, RequestFactory
if django.VERSION >= (2, 0, 0):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse

from djasana import models, views
from djasana.tests.fixtures import attachment, project, story, task, user
from djasana.utils import sign_sha256_hmac


@override_settings(
    ASANA_ACCESS_TOKEN='foo', ASANA_WORKSPACE=None,
    DJASANA_WEBHOOK_URL='https://example.com/hooks/', ROOT_URLCONF='djasana.urls')
class WebhookViewTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.workspace = models.Workspace.objects.create(remote_id=1, name='New Workspace')
        cls.team = models.Team.objects.create(remote_id=2, name='New Team')
        cls.project = models.Project.objects.create(
            remote_id=3, name='New Project', public=True, team=cls.team, workspace=cls.workspace)
        cls.user = models.User.objects.create(remote_id=4, name='New User')
        cls.url = reverse('djasana_webhook', kwargs={'remote_id': 3})
        cls.secret = '1d6207f8818f063890758a32d3833914754ba788cb8993e644701bac7257f59e'
        cls.data = {
            'events': [
                {
                  'action': 'changed',
                  'created_at': '2017-08-21T18:20:37.972Z',
                  'parent': None,
                  'resource': 1337,
                  'type': 'task',
                  'user': 1123
                },
            ]
        }

    def _get_mock_response(self, mock_client, data):
        message = json.dumps(data)
        signature = sign_sha256_hmac(self.secret, message)
        mock_client.access_token().projects.find_by_id.return_value = project()
        mock_client.access_token().tasks.find_by_id.return_value = task()
        request = self.factory.post(
            '', content_type='application/json', data=message,
            **{'X-Hook-Signature': signature})
        return views.WebhookView.as_view()(request, remote_id=3)

    def test_webhook_created(self):
        """Asserts a webhook is established"""
        request = self.factory.post(
            '', content_type='application/json', **{'X-Hook-Secret': self.secret})
        response = views.WebhookView.as_view()(request, remote_id=self.project.remote_id)
        self.assertEqual(200, response.status_code)
        self.assertTrue('x-hook-secret' in response)
        self.assertEqual(self.secret, response['x-hook-secret'])
        try:
            webhook = models.Webhook.objects.get(project=self.project)
        except models.Webhook.DoesNotExist:
            self.fail('Webhook not created')
        self.assertEqual(self.secret, webhook.secret)

    def test_alternative_webhook_meta_key(self):
        """Asserts a webhook is established with an alternative META tag"""
        request = self.factory.post(
            '', content_type='application/json', **{'HTTP_X_HOOK_SECRET': self.secret})
        response = views.WebhookView.as_view()(request, remote_id=self.project.remote_id)
        self.assertEqual(200, response.status_code)
        self.assertTrue('x-hook-secret' in response)
        self.assertEqual(self.secret, response['x-hook-secret'])

    def test_short_secret(self):
        """Asserts a secret that is 32 chars is accepted"""
        request = self.factory.post(
            '', content_type='application/json', data=json.dumps(self.data),
            **{'X-Hook-Secret': self.secret[:32]})
        response = views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(200, response.status_code)
        self.assertEqual(self.secret[:32], response['x-hook-secret'])

    def test_bad_short_secret(self):
        """Asserts a malicious endpoint posts a wrong secret that is not 64 chars"""
        request = self.factory.post(
            '', content_type='application/json', data=json.dumps(self.data),
            **{'X-Hook-Secret': 'foo'})
        response = views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(403, response.status_code)

    def test_bad_short_signature(self):
        """Asserts a malicious endpoint posts a wrong signature that is not 64 chars"""
        request = self.factory.post(
            '', content_type='application/json', data=json.dumps(self.data),
            **{'X-Hook-Signature': 'foo'})
        response = views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(403, response.status_code)

    def test_bad_signature(self):
        """Asserts a malicious endpoint posts a wrong signature"""
        models.Webhook.objects.create(project=self.project, secret=self.secret)
        request = self.factory.post(
            '', content_type='application/json', data=json.dumps(self.data),
            **{'X-Hook-Signature': 'x' * 64})
        response = views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(403, response.status_code)

    def test_bad_project_id(self):
        """Asserts a malicious endpoint posts a wrong project id"""
        request = self.factory.post(
            '', content_type='application/json', data=json.dumps(self.data),
            **{'X-Hook-Secret': self.secret})
        with self.assertRaises(Http404):
            views.WebhookView.as_view()(request, remote_id=99)

    @patch('djasana.connect.Client')
    def test_valid_request(self, mock_client):
        models.Webhook.objects.create(project=self.project, secret=self.secret)
        task_ = models.Task.objects.create(remote_id=99, name='Old task Name')
        mock_client.access_token().tasks.find_by_id.return_value = task(id=99)
        mock_client.access_token().attachments.find_by_task.return_value = [attachment()]
        mock_client.access_token().attachments.find_by_id.return_value = attachment()
        mock_client.access_token().stories.find_by_task.return_value = [story()]
        mock_client.access_token().stories.find_by_id.return_value = story()
        data = {
            'events': [
                {
                    'action': 'changed',
                    'created_at': '2017-08-21T18:20:37.972Z',
                    'parent': None,
                    'resource': 99,
                    'type': 'task',
                    'user': 1123
                },
            ]
        }
        response = self._get_mock_response(mock_client, data)
        self.assertEqual(200, response.status_code)
        self.assertFalse('x-hook-secret' in response)
        task_.refresh_from_db()
        self.assertEqual('Test Task', task_.name)
        try:
            models.Attachment.objects.get(remote_id=1)
        except models.Attachment.DoesNotExist:
            self.fail('Attachment not created')
        try:
            models.Story.objects.get(remote_id=1)
        except models.Story.DoesNotExist:
            self.fail('Story not created')

    @patch('djasana.connect.Client')
    def test_bad_task_id(self, mock_client):
        """Asserts an event is received for a task that is now deleted in Asana"""
        mock_client.access_token().tasks.find_by_id.side_effect = ForbiddenError
        request = self.factory.post(
            '', content_type='application/json', data=json.dumps(self.data),
            **{'X-Hook-Secret': self.secret})
        response = views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(200, response.status_code)

    @patch('djasana.connect.Client')
    def test_task_with_parent(self, mock_client):
        models.Webhook.objects.create(project=self.project, secret=self.secret)
        parent_task = task(id=10, assignee=user())
        child_task = task(id=11, assignee=user(), parent=parent_task.copy())
        mock_client.access_token().tasks.find_all.return_value = [child_task]
        mock_client.access_token().tasks.find_by_id.side_effect = [child_task, parent_task]
        data = {
            'events': [
                {
                    'action': 'added',
                    'created_at': '2017-08-21T18:20:37.972Z',
                    'parent': {'id': 10},
                    'resource': 1337,
                    'type': 'task',
                    'user': 1123
                },
            ]
        }
        message = json.dumps(data)
        signature = sign_sha256_hmac(self.secret, message)
        request = self.factory.post(
            '', content_type='application/json', data=message,
            **{'X-Hook-Signature': signature})
        views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(2, models.Task.objects.count())
        parent, child = tuple(models.Task.objects.order_by('remote_id'))
        self.assertEqual(parent, child.parent)

    @patch('djasana.connect.Client')
    def test_task_deleted(self, mock_client):
        models.Webhook.objects.create(project=self.project, secret=self.secret)
        task_ = models.Task.objects.create(remote_id=1337, name='Old task Name')
        mock_client.access_token().tasks.find_by_id.return_value = task()
        mock_client.access_token().attachments.find_by_task.return_value = [attachment()]
        mock_client.access_token().attachments.find_by_id.return_value = attachment()
        mock_client.access_token().stories.find_by_task.return_value = [story()]
        mock_client.access_token().stories.find_by_id.return_value = story()
        data = self.data.copy()
        data['events'][0]['action'] = 'removed'
        response = self._get_mock_response(mock_client, data)
        self.assertEqual(200, response.status_code)
        self.assertFalse('x-hook-secret' in response)
        with self.assertRaises(models.Task.DoesNotExist):
            models.Task.objects.get(pk=task_.pk)

    @patch('djasana.connect.Client')
    def test_project_updated(self, mock_client):
        models.Webhook.objects.create(project=self.project, secret=self.secret)
        data = {
            'events': [
                {
                  'action': 'changed',
                  'created_at': '2017-08-21T18:20:37.972Z',
                  'parent': None,
                  'resource': 3,
                  'type': 'project',
                  'user': 1123
                },
            ]
        }
        response = self._get_mock_response(mock_client, data)
        self.assertEqual(200, response.status_code)
        self.assertFalse('x-hook-secret' in response)
        self.project.refresh_from_db()
        self.assertEqual('Test Project', self.project.name)

    @patch('djasana.connect.Client')
    def test_project_deleted(self, mock_client):
        models.Webhook.objects.create(project=self.project, secret=self.secret)
        data = {
            'events': [
                {
                    'action': 'removed',
                    'created_at': '2017-08-21T18:20:37.972Z',
                    'parent': None,
                    'resource': 3,
                    'type': 'project',
                    'user': 1123
                },
            ]
        }
        mock_client.access_token().projects.find_by_id.return_value = project()
        mock_client.access_token().tasks.find_by_id.return_value = task(parent=task())
        response = self._get_mock_response(mock_client, data)
        self.assertEqual(200, response.status_code)
        self.assertFalse('x-hook-secret' in response)
        with self.assertRaises(models.Project.DoesNotExist):
            models.Project.objects.get(pk=self.project.pk)

    @patch('djasana.connect.Client')
    def test_new_story(self, mock_client):
        models.Webhook.objects.create(project=self.project, secret=self.secret)
        data = {
            'events': [
                {
                    'action': 'added',
                    'created_at': '2017-08-21T18:20:37.972Z',
                    'parent': None,
                    'resource': 12,
                    'type': 'story',
                    'user': 1123
                },
            ]
        }
        mock_client.access_token().projects.find_by_id.return_value = project()
        mock_client.access_token().stories.find_by_id.return_value = story()
        response = self._get_mock_response(mock_client, data)
        self.assertEqual(200, response.status_code)
        try:
            models.Story.objects.get(remote_id=12)
        except models.Story.DoesNotExist:
            self.fail('Story not created')

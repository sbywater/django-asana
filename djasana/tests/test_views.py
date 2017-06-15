import json
import unittest

from asana.error import ForbiddenError
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import override_settings, TestCase, RequestFactory

from djasana import models, views
from djasana.tests.fixtures import attachment, project, story, task
from djasana.utils import sign_sha256_hmac


@override_settings(ASANA_ACCESS_TOKEN='foo')
@override_settings(ASANA_WORKSPACE=None)
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

    @unittest.mock.patch('djasana.connect.Client')
    def test_valid_request(self, mock_client):
        models.Webhook.objects.create(project=self.project, secret=self.secret)
        message = json.dumps(self.data)
        signature = sign_sha256_hmac(self.secret, message)
        task_ = models.Task.objects.create(remote_id=1337, name='Old task Name')
        mock_client.access_token().tasks.find_by_id.return_value = task()
        mock_client.access_token().attachments.find_by_task.return_value = [attachment()]
        mock_client.access_token().attachments.find_by_id.return_value = attachment()
        mock_client.access_token().stories.find_by_task.return_value = [story()]
        mock_client.access_token().stories.find_by_id.return_value = story()
        request = self.factory.post(
            '', content_type='application/json', data=message,
            **{'X-Hook-Signature': signature})
        response = views.WebhookView.as_view()(request, remote_id=3)
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

    @unittest.mock.patch('djasana.connect.Client')
    def test_bad_task_id(self, mock_client):
        """Asserts an event is received for a task that is now deleted in Asana"""
        mock_client.access_token().tasks.find_by_id.side_effect = ForbiddenError
        request = self.factory.post(
            '', content_type='application/json', data=json.dumps(self.data),
            **{'X-Hook-Secret': self.secret})
        response = views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(200, response.status_code)

    @unittest.mock.patch('djasana.connect.Client')
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
        message = json.dumps(data)
        signature = sign_sha256_hmac(self.secret, message)
        mock_client.access_token().projects.find_by_id.return_value = project()
        mock_client.access_token().tasks.find_by_id.return_value = task()
        request = self.factory.post(
            '', content_type='application/json', data=message,
            **{'X-Hook-Signature': signature})
        response = views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(200, response.status_code)
        self.assertFalse('x-hook-secret' in response)
        self.project.refresh_from_db()
        self.assertEqual('Test Project', self.project.name)

    @unittest.mock.patch('djasana.connect.Client')
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
        message = json.dumps(data)
        signature = sign_sha256_hmac(self.secret, message)
        mock_client.access_token().projects.find_by_id.return_value = project()
        mock_client.access_token().stories.find_by_id.return_value = story()
        request = self.factory.post(
            '', content_type='application/json', data=message,
            **{'X-Hook-Signature': signature})
        response = views.WebhookView.as_view()(request, remote_id=3)
        self.assertEqual(200, response.status_code)
        try:
            models.Story.objects.get(remote_id=12)
        except models.Story.DoesNotExist:
            self.fail('Story not created')

import hashlib
import hmac
import logging

from asana.error import InvalidRequestError
import django
from django.conf import settings

from djasana.models import Story, Tag, Task, User

if django.VERSION >= (2, 0, 0):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse

logger = logging.getLogger(__name__)


def sign_sha256_hmac(secret, message):
    if not isinstance(message, bytes):
        message = bytes(message.encode('utf-8'))
    if not isinstance(secret, bytes):
        secret = bytes(secret.encode('utf-8'))
    return hmac.new(secret, message, digestmod=hashlib.sha256).hexdigest()


def set_webhook(client, project_id):
    target = '{}{}'.format(
        settings.DJASANA_WEBHOOK_URL,
        reverse('djasana_webhook', kwargs={'remote_id': project_id}))
    logger.debug('Setting webhook at %s', target)
    try:
        client.webhooks.create({
            'resource': project_id,
            'target': target,
        })
    except InvalidRequestError as error:
        logger.warning(error)
        logger.warning('Target url: %s', target)


def sync_story(remote_id, story_dict):
    story_dict.pop('gid', None)
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


def sync_task(remote_id, task_dict, project, sync_tags=False):
    task_dict.pop('gid', None)
    if task_dict['assignee']:
        user = User.objects.get_or_create(
            remote_id=task_dict['assignee']['id'],
            defaults={'name': task_dict['assignee']['name']})[0]
        task_dict['assignee'] = user
    for key in (
            'hearts', 'liked', 'likes', 'num_likes',
            'memberships', 'projects', 'workspace'):
        task_dict.pop(key, None)
    followers_dict = task_dict.pop('followers')
    tags_dict = task_dict.pop('tags')
    task = Task.objects.update_or_create(
        remote_id=remote_id, defaults=task_dict)[0]
    follower_ids = [follower['id'] for follower in followers_dict]
    followers = User.objects.filter(id__in=follower_ids)
    task.followers.set(followers)
    if sync_tags:
        for tag_ in tags_dict:
            tag = Tag.objects.get_or_create(
                remote_id=tag_['id'],
                defaults={'name': tag_['name']})[0]
            task.tags.add(tag)
    task.projects.add(project)
    return task

import hashlib
import hmac
import logging

from asana.error import InvalidRequestError
import django
from django.conf import settings

from djasana.models import (
    Attachment, CustomField, CustomFieldSetting, Project, ProjectStatus,
    Story, Tag, Task, Team, User)

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


def pop_unsupported_fields(instance_dict, model):
    """Pops unsupported fields from a dict that is to be used in get_or_create.

    Provides forward compatibility, so when Asana API includes a new field, things do not break
    until the model gains support for it. Known unsupported fields should be explicitly popped
    before reaching here.
    """
    supported_fields = []
    for field in model._meta.get_fields():
        if field.is_relation:
            if not field.many_to_many:
                supported_fields.append(field.name)
                if hasattr(field, 'attname'):
                    supported_fields.append(field.attname)
        else:
            supported_fields.append(field.name)
    unsupported_fields = instance_dict.keys() - supported_fields
    for field in unsupported_fields:
        instance_dict.pop(field)


def sync_attachment(client, task, attachment_id):
    attachment_dict = client.attachments.find_by_id(attachment_id)
    logger.debug(attachment_dict)
    remote_id = attachment_dict.pop('id')
    attachment_dict.pop('num_annotations', None)
    attachment_dict.pop('num_incomplete_annotations', None)
    if attachment_dict['parent']:
        attachment_dict['parent'] = task
    pop_unsupported_fields(attachment_dict, Attachment)
    Attachment.objects.get_or_create(remote_id=remote_id, defaults=attachment_dict)


def sync_project(client, project_dict):
    remote_id = project_dict.pop('id')
    if project_dict['owner']:
        owner = project_dict.pop('owner')
        User.objects.get_or_create(remote_id=owner['id'], defaults={'name': owner['name']})
        project_dict['owner_id'] = owner['id']
    team = project_dict.pop('team')
    Team.objects.get_or_create(remote_id=team['id'], defaults={'name': team['name']})
    project_dict['team_id'] = team['id']
    project_dict['workspace_id'] = project_dict.pop('workspace')['id']
    custom_field_settings = project_dict.pop('custom_field_settings', None)
    # Convert string to boolean:
    project_dict['archived'] = project_dict['archived'] == 'true'
    members_dict = project_dict.pop('members')
    followers_dict = project_dict.pop('followers')
    project_status_dict = project_dict.pop('current_status', None)
    pop_unsupported_fields(project_dict, Project)
    project = Project.objects.update_or_create(
        remote_id=remote_id, defaults=project_dict)[0]
    member_ids = [member['id'] for member in members_dict]
    members = User.objects.filter(id__in=member_ids)
    project.members.set(members)
    follower_ids = [follower['id'] for follower in followers_dict]
    followers = User.objects.filter(id__in=follower_ids)
    project.followers.set(followers)
    if project_status_dict:
        current_status_id = project_status_dict.pop('id')
        project_status = ProjectStatus.objects.update_or_create(
            remote_id=current_status_id, defaults=project_status_dict)[0]
        project.current_status = project_status
        project.save(update_fields=['current_status'])
    if custom_field_settings:
        sync_custom_fields(
            client, custom_field_settings, project_dict['workspace_id'], project.remote_id)
    return project


def sync_story(remote_id, story_dict):
    if story_dict['created_by']:
        user = User.objects.get_or_create(
            remote_id=story_dict['created_by']['id'],
            defaults={'name': story_dict['created_by']['name']})[0]
        story_dict['created_by'] = user
    if story_dict['target']:
        story_dict['target'] = story_dict['target']['id']
    pop_unsupported_fields(story_dict, Story)
    if 'text' in story_dict:
        story_dict['text'] = story_dict['text'][:1024]  # Truncate text if too long
    Story.objects.get_or_create(remote_id=remote_id, defaults=story_dict)


def sync_task(remote_id, task_dict, project, sync_tags=False):
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
    pop_unsupported_fields(task_dict, Task)
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


def sync_custom_fields(client, custom_field_settings, workspace_id, project_id):
    synced_ids = []
    for setting in custom_field_settings:
        custom_field_mini_dict = setting.pop('custom_field')
        setting.pop('project')
        custom_field_remote_id = custom_field_mini_dict.pop('id')
        if custom_field_remote_id not in synced_ids:
            custom_field_dict = client.custom_fields.find_by_id(custom_field_remote_id)
            CustomField.objects.update_or_create(
                remote_id=custom_field_remote_id, defaults=custom_field_dict)
            synced_ids.append(custom_field_remote_id)
        setting_remote_id = setting.pop('id')
        pop_unsupported_fields(setting, CustomFieldSetting)
        setting['custom_field_id'] = custom_field_remote_id
        setting['project_id'] = project_id
        CustomFieldSetting.objects.update_or_create(
            remote_id=setting_remote_id, workspace_id=workspace_id, defaults=setting)

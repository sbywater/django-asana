import json
import logging

from django.core.cache import cache
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .connect import client_connect

logger = logging.getLogger(__name__)


ASANA_BASE_URL = 'https://app.asana.com/0/'
COLORS = [
    'dark-pink', 'dark-green', 'dark-blue', 'dark-red', 'dark-teal', 'dark-brown',
    'dark-orange', 'dark-purple', 'dark-warm-gray', 'light-pink', 'light-green',
    'light-blue', 'light-red', 'light-teal', 'light-yellow', 'light-orange',
    'light-purple', 'light-warm-gray']
COLOR_CHOICES = ((choice, _(choice)) for choice in COLORS)


class BaseModel(models.Model):
    """An abstract base class for Asana models."""
    remote_id = models.BigIntegerField(
        unique=True, db_index=True,
        help_text=_('The id of this object in Asana.'))
    gid = models.CharField(
        max_length=31,
        unique=True, db_index=True,
        null=True,
        help_text=_('The gid of this object in Asana.'))

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.remote_id)

    def save(self, *args, **kwargs):
        self.gid = self.gid or str(self.remote_id)
        super(BaseModel, self).save(*args, **kwargs)

    def asana_url(self, *args, **kwargs):
        return '{}{}'.format(ASANA_BASE_URL, self.remote_id)

    def get_absolute_url(self):
        return self.asana_url()


class NamedModel(BaseModel):
    """An abstract base class for Asana models with names."""
    name = models.CharField(_('name'), max_length=1024)

    class Meta:
        abstract = True
        ordering = ('name',)

    def __str__(self):
        return self.name[:50] or str(self.remote_id)


class Hearted(models.Model):
    """A record that a user has liked a thing."""
    hearted = models.BooleanField(default=False)
    hearts = models.ManyToManyField('User', related_name='%(class)s_hearted')
    num_hearts = models.SmallIntegerField(default=0)

    class Meta:
        abstract = True


class Attachment(NamedModel):
    """A remote file."""
    host_choices = (
        ('asana', 'asana'),
    )
    type_choices = (
        ('image', 'image'),
        ('other', 'other'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    download_url = models.URLField(max_length=1024)
    host = models.CharField(choices=host_choices, max_length=24)
    parent = models.ForeignKey('Task', to_field='remote_id', on_delete=models.CASCADE)
    permanent_url = models.URLField(max_length=1024)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='attachment')
    type = models.CharField(choices=type_choices, max_length=24, null=True, blank=True)
    view_url = models.URLField(max_length=1024)

    def asana_url(self, project=None):
        return self.permanent_url


class CustomField(NamedModel):
    """Metadata for adding custom data to a task"""
    subtype_choices = (
        ('enum', 'enum'),
        ('number', 'number'),
        ('text', 'text'),
    )
    precision_choices = [(num, num) for num in range(0, 7)]

    description = models.CharField(max_length=1024, null=True, blank=True)
    enum_options = models.CharField(max_length=1024, null=True, blank=True)
    precision = models.SmallIntegerField(choices=precision_choices, null=True, blank=True)
    resource_subtype = models.CharField(
        choices=subtype_choices, max_length=24, null=True, blank=True)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='custom_field')
    type = models.CharField(  # Deprecated; use resource_subtype
        choices=subtype_choices, max_length=24, null=True, blank=True)


class CustomFieldSetting(BaseModel):
    """Settings for a custom field of a project"""
    created_at = models.DateTimeField(auto_now_add=True)
    custom_field = models.ForeignKey('CustomField', to_field='remote_id', on_delete=models.CASCADE)
    is_important = models.BooleanField(default=False)
    project = models.ForeignKey('Project', to_field='remote_id', on_delete=models.CASCADE)
    resource_type = models.CharField(
        max_length=24, null=True, blank=True, default='custom_field_setting')
    workspace = models.ForeignKey('Workspace', to_field='remote_id', on_delete=models.CASCADE)


class Project(NamedModel):
    """An Asana project in a workspace having a collection of tasks."""
    layout_choices = (
        ('board', _('board')),
        ('list', _('list')),
    )

    archived = models.BooleanField(default=False)
    color = models.CharField(choices=COLOR_CHOICES, max_length=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    current_status = models.ForeignKey(
        'ProjectStatus', null=True, on_delete=models.SET_NULL, related_name='current_status')
    custom_field_settings = models.ManyToManyField(
        'CustomField', through='CustomFieldSetting', related_name='custom_field_settings')
    due_date = models.DateField(null=True, blank=True)
    followers = models.ManyToManyField('User', related_name='projects_following', blank=True)
    html_notes = models.TextField(null=True, blank=True)
    layout = models.CharField(choices=layout_choices, max_length=16)
    members = models.ManyToManyField('User', blank=True)
    modified_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(
        'User', to_field='remote_id', related_name='projects_owned',
        null=True, on_delete=models.SET_NULL)
    public = models.BooleanField(default=False)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='project')
    start_on = models.DateField(null=True, blank=True)
    team = models.ForeignKey('Team', to_field='remote_id', null=True, on_delete=models.SET_NULL)
    workspace = models.ForeignKey('Workspace', to_field='remote_id', on_delete=models.CASCADE)

    def asana_url(self):
        """Returns the absolute url for this project at Asana."""
        return '{}{}/list'.format(ASANA_BASE_URL, self.remote_id)


class ProjectStatus(BaseModel):
    """An update on the progress of a project."""
    colors = ['red', 'yellow', 'green']
    color_choices = ((choice, _(choice)) for choice in colors)

    color = models.CharField(choices=color_choices, max_length=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'User', to_field='remote_id', null=True, on_delete=models.SET_NULL)
    html_text = models.TextField(null=True, blank=True)
    project = models.ForeignKey(
        'Project', to_field='remote_id', null=True, blank=True, on_delete=models.SET_NULL)
    resource_type = models.CharField(
        max_length=24, null=True, blank=True, default='project_status')
    text = models.TextField(null=True, blank=True)
    title = models.CharField(max_length=1024)

    class Meta:
        ordering = ('-pk',)


class Story(Hearted, NamedModel):
    """The log of a change to an Asana object."""
    source_choices = (
        ('api', _('api')),
        ('email', _('email')),
        ('mobile', _('mobile')),
        ('web', _('web')),
    )
    type_choices = (
        ('comment', _('comment')),
        ('system', _('system')),
    )
    subtype_choices = type_choices + (
        ('added_to_tag', _('added to tag')),
        ('added_to_task', _('added to task')),
        ('added_to_project', _('added to project')),
        ('all_dependencies_marked_complete', _('all dependencies marked complete')),
        ('assigned', _('assigned')),
        ('attachment_added', _('attachment added')),
        ('attachment_liked', _('attachment liked')),
        ('comment_added', _('comment added')),
        ('comment_liked', _('comment liked')),
        ('dependency_added', _('dependency added')),
        ('dependency_due_date_changed', _('dependency due date changed')),
        ('dependency_marked_complete', _('dependency marked complete')),
        ('dependency_marked_incomplete', _('dependency marked incomplete')),
        ('dependency_removed', _('dependency removed')),
        ('dependent_added', _('dependent added')),
        ('dependent_removed', _('dependent removed')),
        ('description_changed', _('description changed')),
        ('due_date_changed', _('due date changed')),
        ('due_today', _('due today')),
        ('duplicate_merged', _('duplicate merged')),
        ('duplicated', _('duplicated')),
        ('enum_custom_field_changed', _('enum custom field changed')),
        ('follower_added', _('follower added')),
        ('liked', _('liked')),
        ('marked_complete', _('marked complete')),
        ('marked_duplicate', _('marked duplicate')),
        ('marked_incomplete', _('marked incomplete')),
        ('marked_today', _('marked today')),
        ('member_added', _('member added')),
        ('name_changed', _('name changed')),
        ('notes_changed', _('notes changed')),
        ('number_custom_field_changed', _('number custom field changed')),
        ('removed_from_project', _('removed from project')),
        ('removed_from_tag', _('removed from tag')),
        ('removed_from_task', _('removed from task')),
        ('section_changed', _('section changed')),
        ('starting_today', _('starting today')),
        ('unassigned', _('unassigned')),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'User', to_field='remote_id', null=True, on_delete=models.SET_NULL)
    html_text = models.CharField(max_length=1024, null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    resource_subtype = models.CharField(
        choices=subtype_choices, max_length=48, null=True, blank=True)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='story')
    source = models.CharField(choices=source_choices, max_length=16)
    target = models.BigIntegerField(db_index=True)
    text = models.CharField(max_length=1024, null=True, blank=True)
    type = models.CharField(  # Deprecated; use resource_subtype
        choices=type_choices, max_length=16, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'stories'


class SyncToken(models.Model):
    """The most recent sync token received from Asana for the project"""
    sync = models.CharField(max_length=36)
    project = models.ForeignKey('Project', to_field='remote_id', on_delete=models.CASCADE)


class Tag(NamedModel):
    """A label within a workspace or organization that can be attached to a task."""
    color = models.CharField(choices=COLOR_CHOICES, max_length=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    followers = models.ManyToManyField('User', related_name='tags_following')
    notes = models.TextField(null=True, blank=True)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='tag')
    workspace = models.ForeignKey(
        'Workspace', to_field='remote_id', on_delete=models.CASCADE, null=True, blank=True)


class Task(Hearted, NamedModel):
    """An Asana task; something that needs doing."""
    status_choices = (
        ('inbox', _('inbox')),
        ('upcoming', _('upcoming')),
        ('later', _('later')),
    )
    subtype_choices = (
        ('default_task', _('default task')),
        ('section', _('section')),
    )

    assignee = models.ForeignKey(
        'User', to_field='remote_id', related_name='assigned_tasks', null=True, blank=True,
        on_delete=models.SET_NULL)
    assignee_status = models.CharField(choices=status_choices, max_length=16)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    custom_fields = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    dependencies = models.ManyToManyField('self', symmetrical=False, related_name='dependents')
    due_at = models.DateTimeField(null=True, blank=True)
    due_on = models.DateField(null=True, blank=True)
    followers = models.ManyToManyField('User', related_name='tasks_following')
    html_notes = models.TextField(null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(null=True, blank=True)
    parent = models.ForeignKey(
        'self', to_field='remote_id', null=True, blank=True, on_delete=models.SET_NULL)
    projects = models.ManyToManyField('Project')
    resource_subtype = models.CharField(
        choices=subtype_choices, max_length=24, default='default_task')
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='task')
    start_on = models.DateField(null=True, blank=True)
    tags = models.ManyToManyField('Tag')

    def _asana_project_url(self, project):
        return '{}{}/{}/list'.format(ASANA_BASE_URL, project.workspace.remote_id, self.remote_id)

    def asana_url(self, project=None):
        """Returns the absolute url for this task at Asana."""
        if project:
            return self._asana_project_url(project)
        projects = self.projects.all()
        if len(projects) == 1:
            project = projects[0]
            return self._asana_project_url(project)
        return super(Task, self).asana_url()

    def delete_from_asana(self, *args, **kwargs):
        """Deletes this task from Asana and then deletes this model instance."""
        client = client_connect()
        client.tasks.delete(self.remote_id)
        logger.debug('Deleted asana task %s', self.name)
        return self.delete(*args, **kwargs)

    def due(self):
        return self.due_at or self.due_on
    due.admin_order_field = 'due_on'

    def refresh_from_asana(self):
        """Updates this task from Asana."""
        client = client_connect()
        task_dict = client.tasks.find_by_id(self.remote_id)
        if task_dict['assignee']:
            user = User.objects.get_or_create(
                remote_id=task_dict['assignee']['id'],
                defaults={'name': task_dict['assignee']['name']})[0]
            task_dict['assignee'] = user
        task_dict.pop('id')
        task_dict.pop('dependents', None)
        dependencies = task_dict.pop('dependencies', None)
        task_dict.pop('hearts', None)
        task_dict.pop('memberships')
        task_dict.pop('num_hearts', None)
        task_dict.pop('projects')
        task_dict.pop('workspace')
        followers_dict = task_dict.pop('followers')
        tags_dict = task_dict.pop('tags')
        for field, value in task_dict.items():
            setattr(self, field, value)
        self.save()
        follower_ids = [follower['id'] for follower in followers_dict]
        followers = User.objects.filter(id__in=follower_ids)
        self.followers.set(followers)
        for tag_ in tags_dict:
            tag = Tag.objects.get_or_create(
                remote_id=tag_['id'],
                defaults={'name': tag_['name']})[0]
            self.tags.add(tag)
        if dependencies:
            self.dependencies.set([dep['id'] for dep in dependencies])

    def sync_to_asana(self, fields=None):
        """Updates Asana to match values from this task."""
        fields = fields or ['completed']
        data = {}
        for field in fields:
            data[field] = getattr(self, field)
        client = client_connect()
        client.tasks.update(self.remote_id, data)
        logger.debug('Updated asana for task %s', self.name)

    def add_comment(self, text):
        """Adds a comment in Asana for this task."""
        client = client_connect()
        response = client.tasks.add_comment(self.remote_id, {'text': text})
        logger.debug('Added comment for task %s: %s', self.name, text)
        return response

    def get_custom_fields(self):
        """Returns custom_fields as a dict"""
        response = json.loads(self.custom_fields)
        custom_field_values = {}
        for custom_field in response:
            if custom_field['resource_subtype'] == 'enum':
                custom_field_values[custom_field['name']] = custom_field['enum_value']['name']
            elif custom_field['resource_subtype'] == 'number':
                if custom_field.get('precision', 0):
                    custom_field_values[custom_field['name']] = float(custom_field['number_value'])
                else:
                    custom_field_values[custom_field['name']] = int(custom_field['number_value'])
            else:
                custom_field_values[custom_field['name']] = custom_field['text_value']
        return custom_field_values


class Team(NamedModel):
    organization_id = models.BigIntegerField(null=True)
    organization_name = models.CharField(max_length=50)
    description = models.CharField(max_length=1024, null=True, blank=True)
    html_description = models.CharField(max_length=1024, null=True, blank=True)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='team')


class User(NamedModel):
    """An Asana user.

    Note this is not related to a django User (although you can establish a relationship yourself).

    """
    email = models.EmailField(_('email address'), null=True, blank=True)
    photo = models.CharField(_('photo'), max_length=255, null=True)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='user')
    workspaces = models.ManyToManyField('Workspace')

    def refresh_from_asana(self):
        client = client_connect()
        user_dict = client.users.find_by_id(self.remote_id)
        user_dict.pop('id')
        user_dict.pop('workspaces')
        if user_dict['photo']:
            user_dict['photo'] = user_dict['photo']['image_128x128']
        for field, value in user_dict.items():
            setattr(self, field, value)
        self.save()


class Webhook(models.Model):
    """A secret negotiated with Asana for keeping a project synchronized."""
    secret = models.CharField(max_length=64, validators=[MinLengthValidator(32)])
    project = models.ForeignKey('Project', to_field='remote_id', on_delete=models.CASCADE)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='webhook')


class Workspace(NamedModel):
    """An object for grouping projects"""
    is_organization = models.BooleanField(default=True)
    resource_type = models.CharField(max_length=24, null=True, blank=True, default='workspace')


def get_next_color():
    """Returns the next color choice.

    For assigning to new Asana projects. Cache where we are in the list.
    """
    color = cache.get('LAST_ASANA_COLOR')
    if color:
        index = COLORS.index(color)
        if index == len(COLORS) - 1:
            color = COLORS[0]
        else:
            color = COLORS[index + 1]
    else:
        color = COLORS[0]
    cache.set('LAST_ASANA_COLOR', color)
    return color

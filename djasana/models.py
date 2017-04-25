import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _

from .connect import client_connect

logger = logging.getLogger(__name__)


STATUS_CHOICES = (
    ('inbox', _('inbox')),
    ('upcoming', _('upcoming')),
    ('later', _('later')),
)

class BaseModel(models.Model):
    remote_id = models.BigIntegerField(
        unique=True, db_index=True,
        help_text=_('The id of this object in Asana.'))
    name = models.CharField(_('name'), max_length=1024)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name or str(self.remote_id)

    def refresh_from_asana(self):
        raise NotImplementedError


class Hearted(models.Model):
    hearted = models.BooleanField(default=False)
    hearts = models.ManyToManyField('User', related_name='%(class)s_hearted')
    num_hearts = models.SmallIntegerField(default=0)

    class Meta:
        abstract = True


class Attachment(BaseModel):
    host_choices = (
        ('asana', 'asana'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    download_url = models.URLField(max_length=1024)
    host = models.CharField(choices=host_choices, max_length=24)
    parent = models.ForeignKey('Task', to_field='remote_id', on_delete=models.CASCADE)
    permanent_url = models.URLField(max_length=1024)
    view_url = models.URLField(max_length=1024)


class Event(models.Model):
    pass


class Project(BaseModel):
    layout_choices = (
        ('list', _('list')),
    )

    archived = models.BooleanField()
    color = models.CharField(max_length=16, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    current_status = models.CharField(choices=STATUS_CHOICES, max_length=16, null=True)
    due_date = models.DateField(null=True)
    followers = models.ManyToManyField('User', related_name='projects_following')
    layout = models.CharField(choices=layout_choices, max_length=16)
    members = models.ManyToManyField('User')
    modified_at = models.DateTimeField()
    notes = models.TextField()
    owner = models.ForeignKey(
        'User', to_field='remote_id', related_name='projects_owned', null=True)
    public = models.BooleanField()
    team = models.ForeignKey('Team', to_field='remote_id')
    workspace = models.ForeignKey('Workspace', to_field='remote_id')


class Story(Hearted, BaseModel):
    source_choices = (
        ('web', _('web')),
    )
    type_choices = (
        ('comment', _('comment')),
        ('system', _('system')),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'User', to_field='remote_id', on_delete=models.SET_NULL, null=True)
    target = models.BigIntegerField(db_index=True)
    source = models.CharField(choices=source_choices, max_length=16)
    text = models.CharField(max_length=1024)
    type= models.CharField(choices=type_choices, max_length=16)

    class Meta:
        verbose_name_plural = 'stories'


class Tag(BaseModel):
    pass


class Task(Hearted, BaseModel):
    assignee = models.ForeignKey(
        'User', to_field='remote_id', related_name='assigned_tasks', null=True)
    assignee_status = models.CharField(choices=STATUS_CHOICES, max_length=16)
    completed = models.BooleanField()
    completed_at = models.DateTimeField(auto_now_add=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True)
    due_on = models.DateField(null=True)
    followers = models.ManyToManyField('User', related_name='tasks_following')
    modified_at = models.DateTimeField()
    notes = models.TextField()
    parent = models.ForeignKey('self', to_field='remote_id', null=True)
    projects = models.ManyToManyField('Project')
    tags = models.ManyToManyField('Tag')

    def due(self):
        return self.due_at or self.due_on


class Team(BaseModel):
    organization_id = models.BigIntegerField(null=True)
    organization_name = models.CharField(max_length=50)


class User(BaseModel):
    email = models.EmailField(_('email address'), blank=True)
    photo = models.CharField(_('photo'), max_length=255, null=True)
    workspaces = models.ManyToManyField('Workspace')

    def refresh_from_asana(self):
        client = client_connect()
        user_dict = client.users.find_by_id(self.remote_id)
        user_dict.pop('id')
        user_dict.pop('workspaces')
        if user_dict['photo']:
            user_dict['photo'] = user_dict['photo']['image_128x128']
        self.save(**user_dict)


class Workspace(BaseModel):
    is_organization = models.BooleanField()

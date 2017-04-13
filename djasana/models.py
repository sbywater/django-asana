from django.db import models
from django.utils.translation import ugettext_lazy as _


class Attachment(models.Model):
    host_choices = (
        ('asana', 'asana'),
    )
    remote_id = models.IntegerField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    download_url = models.URLField()
    host = models.CharField(choices=host_choices, max_length=24)
    name = models.CharField(_('name'), max_length=50)
    parent = models.ForeignKey('Task', on_delete=models.CASCADE)
    permanent_url = models.URLField()
    view_url = models.URLField()


class Event(models.Model):
    pass


class Project(models.Model):
    status_choices = (
        ('inbox', _('inbox')),
        ('incoming', _('incoming')),
        ('later', _('later')),
    )
    layout_choices = (
        ('list', _('list')),
    )

    remote_id = models.IntegerField(unique=True, db_index=True)
    archived = models.BooleanField()
    color = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    current_status = models.CharField(choices=status_choices, max_length=16, null=True)
    due_date = models.DateField()
    followers = models.ManyToManyField('User', related_name='projects_following')
    layout = models.CharField(choices=layout_choices, max_length=16)
    members = models.ManyToManyField('User')
    modified_at = models.DateTimeField()
    name = models.CharField(_('name'), max_length=50)
    notes = models.TextField()
    owner = models.ForeignKey('User', related_name='projects_owned')
    public = models.BooleanField()
    team = models.ForeignKey('Team')
    workspace = models.ForeignKey('Workspace')


class Story(models.Model):
    type_choices = (
        ('comment', _('comment')),
        ('system', _('system')),
    )
    remote_id = models.IntegerField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    text = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = 'stories'


class Tag(models.Model):
    remote_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(_('name'), max_length=50)


class Task(models.Model):
    assignee_status_choices = (
        ('inbox', _('inbox')),
    )
    remote_id = models.IntegerField(unique=True, db_index=True)
    assignee = models.ForeignKey('User', related_name='assigned_tasks')
    assignee_status = models.CharField(choices=assignee_status_choices, max_length=16)
    completed = models.BooleanField()
    completed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()
    due_on = models.DateField()
    followers = models.ManyToManyField('User', related_name='tasks_following')
    hearted = models.BooleanField()
    hearts = models.ManyToManyField('User')
    modified_at = models.DateTimeField()
    name = models.CharField(_('name'), max_length=50)
    notes = models.TextField()
    num_hearts = models.SmallIntegerField()
    parent = models.ForeignKey('self')
    projects = models.ManyToManyField('Project')


class Team(models.Model):
    remote_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(_('name'), max_length=50)
    organization_id = models.IntegerField()
    organization_name = models.CharField(max_length=50)


class User(models.Model):
    remote_id = models.IntegerField(unique=True, db_index=True)
    email = models.EmailField(_('email address'), blank=True)
    name = models.CharField(_('name'), max_length=50)
    photo = models.CharField(_('photo'), max_length=50, null=True)


class Workspace(models.Model):
    remote_id = models.IntegerField(unique=True, db_index=True)
    is_organization = models.BooleanField()
    name = models.CharField(_('name'), max_length=50)

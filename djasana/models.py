import logging

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .connect import client_connect

logger = logging.getLogger(__name__)


STATUS_CHOICES = (
    ('inbox', _('inbox')),
    ('upcoming', _('upcoming')),
    ('later', _('later')),
)

ASANA_BASE_URL = 'https://app.asana.com/0/'


class BaseModel(models.Model):
    remote_id = models.BigIntegerField(
        unique=True, db_index=True,
        help_text=_('The id of this object in Asana.'))
    name = models.CharField(_('name'), max_length=1024)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name[:50] or str(self.remote_id)

    def asana_url(self, *args, **kwargs):
        return '{}{}'.format(ASANA_BASE_URL, self.remote_id)

    def get_absolute_url(self):
        return self.asana_url()


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

    def asana_url(self, project=None):
        return self.permanent_url


class Project(BaseModel):
    layout_choices = (
        ('list', _('list')),
    )

    archived = models.BooleanField(default=False)
    color = models.CharField(max_length=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    current_status = models.CharField(choices=STATUS_CHOICES, max_length=16, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    followers = models.ManyToManyField('User', related_name='projects_following', blank=True)
    layout = models.CharField(choices=layout_choices, max_length=16)
    members = models.ManyToManyField('User', blank=True)
    modified_at = models.DateTimeField(auto_now=True)
    notes = models.TextField()
    owner = models.ForeignKey(
        'User', to_field='remote_id', related_name='projects_owned', null=True)
    public = models.BooleanField(default=False)
    team = models.ForeignKey('Team', to_field='remote_id')
    workspace = models.ForeignKey('Workspace', to_field='remote_id')

    def asana_url(self):
        return '{}{}/list'.format(ASANA_BASE_URL, self.remote_id)


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


class SyncToken(models.Model):
    """The most recent sync token received from Asana for the project"""
    sync = models.CharField(max_length=36)
    project = models.ForeignKey('Project', to_field='remote_id')


class Tag(BaseModel):
    pass


class Task(Hearted, BaseModel):
    assignee = models.ForeignKey(
        'User', to_field='remote_id', related_name='assigned_tasks', null=True)
    assignee_status = models.CharField(choices=STATUS_CHOICES, max_length=16)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True)
    due_on = models.DateField(null=True)
    followers = models.ManyToManyField('User', related_name='tasks_following')
    modified_at = models.DateTimeField(auto_now=True)
    notes = models.TextField()
    parent = models.ForeignKey('self', to_field='remote_id', null=True)
    projects = models.ManyToManyField('Project')
    tags = models.ManyToManyField('Tag')

    def _asana_project_url(self, project):
        return '{}{}/{}/list'.format(ASANA_BASE_URL, project.workspace.remote_id, self.remote_id)

    def asana_url(self, project=None):
        if project:
            return self._asana_project_url(project)
        projects = self.projects.all()
        if len(projects) == 1:
            project = projects[0]
            return self._asana_project_url(project)
        return super(Task, self).asana_url()

    def due(self):
        return self.due_at or self.due_on

    def refresh_from_asana(self):
        client = client_connect()
        task_dict = client.tasks.find_by_id(self.remote_id)
        if task_dict['assignee']:
            user = User.objects.get_or_create(
                remote_id=task_dict['assignee']['id'],
                defaults={'name': task_dict['assignee']['name']})[0]
            task_dict['assignee'] = user
        task_dict.pop('hearts', None)
        task_dict.pop('memberships')
        task_dict.pop('num_hearts')
        task_dict.pop('projects')
        task_dict.pop('workspace')
        followers_dict = task_dict.pop('followers')
        tags_dict = task_dict.pop('tags')
        self.save(**task_dict)
        follower_ids = [follower['id'] for follower in followers_dict]
        followers = User.objects.filter(id__in=follower_ids)
        self.followers.set(followers)
        for tag_ in tags_dict:
            tag = Tag.objects.get_or_create(
                remote_id=tag_['id'],
                defaults={'name': tag_['name']})[0]
            self.tags.add(tag)
        self.save(**task_dict)

    def sync_to_asana(self, fields=None):
        fields = fields or ['completed']
        data = {}
        for field in fields:
            data[field] = getattr(self, field)
        client = client_connect()
        client.tasks.update(self.remote_id, data)
        logger.debug('Updated asana for task {0}', self.name)


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


class Webhook(models.Model):
    secret = models.CharField(max_length=64, validators=[MinValueValidator(64)])
    project = models.ForeignKey('Project', to_field='remote_id')


class Workspace(BaseModel):
    is_organization = models.BooleanField(default=True)

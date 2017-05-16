from django.contrib import admin
from django.utils.safestring import mark_safe

from djasana import models


def asana_link(obj):
    return mark_safe('<a href="{}" target="_blank">View on Asana</a>'.format(obj.asana_url()))


@admin.register(models.Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'parent', asana_link)
    raw_id_fields = ('parent',)


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('__str__', 'owner', 'archived', asana_link)
    list_filter = ('workspace', 'team', 'archived')


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('__str__', 'completed', 'due', asana_link)
    list_filter = ('completed', 'projects__workspace', 'projects__team', 'assignee')
    raw_id_fields = ('assignee', 'parent')
    search_fields = ('remote_id', 'name')


@admin.register(models.Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('__str__', asana_link)


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('__str__',)


@admin.register(models.Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('__str__', asana_link)

from django.contrib import admin

from djasana import models


@admin.register(models.Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'parent')


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('__str__', 'owner', 'archived')
    list_filter = ('workspace', 'team')


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('__str__', 'assignee', 'completed',)
    list_filter = ('completed',)
    raw_id_fields = ('assignee', 'parent')
    search_fields = ('remote_id', 'name')


@admin.register(models.Team)
class TeamAdmin(admin.ModelAdmin):
    pass


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'email',)


@admin.register(models.Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    pass

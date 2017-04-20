from django.contrib import admin

from djasana import models


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('__str__', 'completed')
    list_filter = ('completed',)
    raw_id_fields = ('assignee', 'parent')
    search_fields = ('remote_id', 'name')


@admin.register(models.Team)
class TeamAdmin(admin.ModelAdmin):
    pass


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    pass

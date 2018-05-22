from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from django.utils.safestring import mark_safe

from djasana import models


def asana_link(obj):
    return mark_safe('<a href="{}" target="_blank">View on Asana</a>'.format(obj.asana_url()))


class ParentRawIdWidget(widgets.ForeignKeyRawIdWidget):

    def url_parameters(self):
        params = super().url_parameters()
        object_ = self.attrs.get('object', None)
        if object_:
            # Filter parent choices by project
            params['projects__id__exact'] = object_.projects.first().pk
        return params


@admin.register(models.Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'name', 'parent', asana_link)
    raw_id_fields = ('parent',)
    readonly_fields = (asana_link,)


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('__str__', 'owner', 'archived', asana_link)
    list_filter = ('workspace', 'team', 'archived')
    readonly_fields = ('workspace', 'team', asana_link)


class TaskForm(forms.ModelForm):

    class Meta:
        fields = ('name', 'assignee', 'completed', 'completed_at',
                  'due_at', 'due_on', 'parent', 'notes', 'projects')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['parent'].widget = ParentRawIdWidget(
                rel=self.instance._meta.get_field('parent').remote_field,
                admin_site=admin.site,
                # Pass the object to attrs
                attrs={'object': self.instance}
            )


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    form = TaskForm
    list_display = ('name', 'assignee', 'completed', 'due', asana_link)
    list_filter = ('completed', 'projects__workspace', 'projects__team', 'assignee', 'projects')
    raw_id_fields = ('assignee', 'parent')
    readonly_fields = (asana_link,)
    search_fields = ('remote_id', 'name')


@admin.register(models.Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('__str__', asana_link)
    readonly_fields = (asana_link,)


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('__str__',)
    readonly_fields = (asana_link,)


@admin.register(models.Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('__str__', asana_link)
    readonly_fields = (asana_link,)

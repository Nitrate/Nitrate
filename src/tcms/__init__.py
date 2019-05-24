# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.admin.widgets import AdminSplitDateTime
from django.contrib import admin
from django.db import models
from django import forms
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

__all__ = [
    'BaseModelAdmin',
]

if settings.ASYNC_TASK == 'CELERY':
    # This will make sure the app is always imported when
    # Django starts so that shared_task will use this app.
    from .celery import app as celery_app

    __all__ += ['celery_app']


class NitrateAdminSplitDateTime(AdminSplitDateTime):
    """Use TemplatesSetting to load customized template"""

    def _render(self, template_name, context, renderer=None):
        renderer_class = import_string('django.forms.renderers.TemplatesSetting')
        return mark_safe(renderer_class().render(template_name, context))


class BaseModelAdmin(admin.ModelAdmin):
    """
    Base ModelAdmin to customize HTML controls' style globally for admin form
    in admin site
    """

    formfield_overrides = {
        models.CharField: {
            'widget': forms.TextInput(attrs={'class': 'form-control'})
        },
        models.TextField: {
            'widget': forms.Textarea(attrs={'class': 'form-control'})
        },
        models.ForeignKey: {
            'widget': forms.Select(attrs={'class': 'form-control'})
        },
        models.ManyToManyField: {
            'widget': forms.Select(attrs={'class': 'form-control'})
        },
        models.BooleanField: {
            'widget': forms.CheckboxInput(attrs={'class': 'form-control bootstrap-switch'}),
        },
        models.IntegerField: {
            'widget': forms.NumberInput(attrs={'class': 'form-control'}),
        },
        models.URLField: {
            'widget': forms.TextInput(attrs={'class': 'form-control'})
        },
        models.DateTimeField: {
            'form_class': forms.SplitDateTimeField,
            'widget': NitrateAdminSplitDateTime,
        },
        models.EmailField: {
            'widget': forms.TextInput(attrs={'class': 'form-control'})
        },
        models.GenericIPAddressField: {
            'widget': forms.TextInput(attrs={'class': 'form-control'})
        },
    }

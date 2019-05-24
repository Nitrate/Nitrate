# -*- coding: utf-8 -*-

from django.contrib import admin

from tcms import BaseModelAdmin
from tcms.issuetracker import models


class IssueTrackerProductAdmin(BaseModelAdmin):
    pass


class ProductIssueTrackerRelationshipInlineAdmin(admin.TabularInline):
    model = models.IssueTracker.products.through
    extra = 1
    fields = ['product', 'issue_tracker', 'alias', 'namespace']
    exclude = ['__str__']


class IssueTrackerAdmin(BaseModelAdmin):
    list_display = ('enabled', 'name', 'tracker_product', 'service_url',
                    'credential_type')
    list_display_links = ('name',)

    fieldsets = (
        (None, {
            'fields': ('enabled', 'tracker_product', 'name', 'description',
                       'service_url', 'api_url', 'issue_url_fmt',
                       'validate_regex'),
        }),
        ('Options', {
            'classes': ('wide',),
            'fields': (
                'class_path', 'allow_add_case_to_issue',
                'issue_report_endpoint', 'issue_report_params',
                'issue_report_templ',
            )
        }),
        ('Authentication', {
            'classes': ('wide',),
            'fields': ('credential_type',)
        }),
    )

    inlines = [
        ProductIssueTrackerRelationshipInlineAdmin,
    ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        fields = form.base_fields

        # forms.TextInput is used for models.CharField to render the HTML. But,
        # this field has property choices set, for which forms.Select is used.
        # The BaseModuleAdmin does not handle this case. Customize the class
        # for patterfly Form style here.
        widget = fields['credential_type'].widget
        if 'class' in widget.attrs:
            widget.attrs['class'] += ' form-control'
        else:
            widget.attrs['class'] = 'form-control'
        return form


class IssueAdmin(BaseModelAdmin):
    list_display = ('issue_key', 'tracker', 'case', 'case_run')


class UserPwdCredentialAdmin(BaseModelAdmin):
    fields = ('issue_tracker', 'username', 'password', 'secret_file')
    list_display = ('__str__', 'issue_tracker')


class TokenCredentialAdmin(BaseModelAdmin):
    fields = ('issue_tracker', 'token', 'until', 'secret_file')
    list_display = ('__str__', 'issue_tracker')


admin.site.register(models.IssueTrackerProduct, IssueTrackerProductAdmin)
admin.site.register(models.IssueTracker, IssueTrackerAdmin)
admin.site.register(models.Issue, IssueAdmin)
admin.site.register(models.UserPwdCredential, UserPwdCredentialAdmin)
admin.site.register(models.TokenCredential, TokenCredentialAdmin)

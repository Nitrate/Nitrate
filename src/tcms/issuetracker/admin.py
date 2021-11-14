# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin

from tcms.issuetracker import models


class IssueTrackerProductAdmin(admin.ModelAdmin):
    pass


class ProductIssueTrackerRelationshipInlineAdmin(admin.TabularInline):
    model = models.IssueTracker.products.through
    extra = 1
    fields = ["product", "issue_tracker", "alias", "namespace"]
    exclude = ["__str__"]


class IssueTrackerAdmin(admin.ModelAdmin):
    list_display = (
        "enabled",
        "name",
        "tracker_product",
        "service_url",
        "credential_type",
    )
    list_display_links = ("name",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "enabled",
                    "tracker_product",
                    "name",
                    "description",
                    "service_url",
                    "api_url",
                    "issue_url_fmt",
                    "validate_regex",
                    "issues_display_url_fmt",
                ),
            },
        ),
        (
            "Options",
            {
                "classes": ("wide",),
                "fields": (
                    "class_path",
                    "allow_add_case_to_issue",
                    "issue_report_endpoint",
                    "issue_report_params",
                    "issue_report_templ",
                ),
            },
        ),
        ("Authentication", {"classes": ("wide",), "fields": ("credential_type",)}),
    )

    inlines = [
        ProductIssueTrackerRelationshipInlineAdmin,
    ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        fields = form.base_fields
        fields["service_url"].widget = forms.TextInput(attrs={"size": 30})
        fields["api_url"].widget = forms.TextInput(attrs={"size": 30})
        fields["description"].widget = forms.Textarea(attrs={"cols": 60})
        fields["class_path"].widget = forms.TextInput(attrs={"size": 50})
        fields["issue_url_fmt"].widget = forms.TextInput(attrs={"size": 50})
        fields["issue_report_params"].widget = forms.Textarea(attrs={"cols": 60})
        fields["issue_report_templ"].widget = forms.Textarea(attrs={"cols": 60})
        fields["issue_report_endpoint"].widget = forms.TextInput(attrs={"size": 30})
        fields["issues_display_url_fmt"].widget = forms.TextInput(attrs={"size": 50})
        return form


class IssueAdmin(admin.ModelAdmin):
    list_display = ("issue_key", "tracker", "case", "case_run")


class UserPwdCredentialAdmin(admin.ModelAdmin):
    fields = ("issue_tracker", "username", "password", "secret_file")
    list_display = ("__str__", "issue_tracker")


class TokenCredentialAdmin(admin.ModelAdmin):
    fields = ("issue_tracker", "token", "until", "secret_file")
    list_display = ("__str__", "issue_tracker")


admin.site.register(models.IssueTrackerProduct, IssueTrackerProductAdmin)
admin.site.register(models.IssueTracker, IssueTrackerAdmin)
admin.site.register(models.Issue, IssueAdmin)
admin.site.register(models.UserPwdCredential, UserPwdCredentialAdmin)
admin.site.register(models.TokenCredential, TokenCredentialAdmin)

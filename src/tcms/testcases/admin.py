# -*- coding: utf-8 -*-
from django.contrib import admin

from tcms.testcases import models
from tcms.testcases.models import TestCase, TestCaseCategory, TestCaseStatus


class TestCaseStatusAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("id", "name", "description")


class TestCaseCategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("id", "name", "product", "description")
    list_filter = ("product",)


class TestCaseAdmin(admin.ModelAdmin):
    search_fields = ("summary",)
    list_display = ("case_id", "summary", "category", "author", "case_status")
    list_filter = ("case_status", "category")


class TestCaseTextAdmin(admin.ModelAdmin):
    list_display = ("id", "case")
    exclude = (
        "action_checksum",
        "effect_checksum",
        "setup_checksum",
        "breakdown_checksum",
    )


admin.site.register(TestCaseStatus, TestCaseStatusAdmin)
admin.site.register(TestCaseCategory, TestCaseCategoryAdmin)
admin.site.register(TestCase, TestCaseAdmin)
admin.site.register(models.TestCaseText, TestCaseTextAdmin)

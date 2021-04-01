# -*- coding: utf-8 -*-

from django.urls import path
from . import ajax, files, views

urlpatterns = [
    # Site entry
    path("", views.index, name="nitrate-index"),
    path("search/", views.search, name="nitrate-search"),
    path(
        "ajax/update/case-run-status",
        ajax.UpdateTestCaseRunPropertiesView.as_view(),
        name="ajax-update-case-runs-status",
    ),
    path(
        "ajax/update/case-run-assignee/",
        ajax.UpdateTestCaseRunPropertiesView.as_view(),
        name="ajax-update-case-runs-assignee",
    ),
    path(
        "ajax/update/case-run-sort-key/",
        ajax.UpdateTestCaseRunPropertiesView.as_view(),
        name="ajax-update-case-runs-sort-key",
    ),
    # TODO: merge this into next mapping
    path(
        "ajax/update/case-status/",
        ajax.UpdateTestCasePropertiesView.as_view(),
        name="ajax-update-cases-status",
    ),
    path(
        "ajax/update/cases-priority/",
        ajax.UpdateTestCasePropertiesView.as_view(),
        name="ajax-update-cases-priority",
    ),
    path(
        "ajax/update/cases-default-tester/",
        ajax.UpdateTestCasePropertiesView.as_view(),
        name="ajax-update-cases-default-tester",
    ),
    path(
        "ajax/update/cases-reviewer/",
        ajax.UpdateTestCasePropertiesView.as_view(),
        name="ajax-update-cases-reviewer",
    ),
    path(
        "ajax/update/cases-sortkey/",
        ajax.UpdateTestCasePropertiesView.as_view(),
        name="ajax-update-cases-sort-key",
    ),
    path("ajax/form/", ajax.form, name="ajax-form"),
    path("management/getinfo/", ajax.info, name="ajax-getinfo"),
    path("management/tags/", ajax.tag),
    # Attached file zone
    path("management/uploadfile/", files.UploadFileView.as_view(), name="upload-file"),
    path("management/checkfile/<int:file_id>/", files.check_file, name="check-file"),
    path("management/deletefile/", files.delete_file, name="delete-file"),
]

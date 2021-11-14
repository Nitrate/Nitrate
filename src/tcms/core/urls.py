# -*- coding: utf-8 -*-

from django.urls import path

from . import ajax, files, views

urlpatterns = [
    # Site entry
    path("", views.index, name="nitrate-index"),
    path("search/", views.search, name="nitrate-search"),
    path("ajax/case-runs/", ajax.PatchTestCaseRunsView.as_view(), name="patch-case-runs"),
    path("ajax/cases/", ajax.PatchTestCasesView.as_view(), name="patch-cases"),
    path("ajax/form/", ajax.form, name="ajax-form"),
    path("management/getinfo/", ajax.info, name="ajax-getinfo"),
    path("management/tags/", ajax.manage_tags),
    # Attached file zone
    path("management/uploadfile/", files.UploadFileView.as_view(), name="upload-file"),
    path("management/checkfile/<int:file_id>/", files.check_file, name="check-file"),
    path("management/deletefile/", files.delete_file, name="delete-file"),
]

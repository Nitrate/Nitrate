# -*- coding: utf-8 -*-

from django.urls import path
from . import ajax, files, views

urlpatterns = [
    # Site entry
    path('', views.index, name='nitrate-index'),
    path('search/', views.search, name='nitrate-search'),

    # Ajax call responder
    path('ajax/update/', ajax.update, name='ajax-update'),

    # TODO: merge this into next mapping
    path('ajax/update/case-status/', ajax.update_cases_case_status),
    path('ajax/update/case-run-status', ajax.update_case_run_status,
         name='ajax-update-caserun-status'),
    path('ajax/update/cases-priority/', ajax.update_cases_priority),
    path('ajax/update/cases-default-tester/', ajax.update_cases_default_tester,
         name='ajax-update-cases-default-tester'),
    path('ajax/update/cases-reviewer/', ajax.update_cases_reviewer),
    path('ajax/update/cases-sortkey/', ajax.update_cases_sortkey),
    path('ajax/form/', ajax.form, name='ajax-form'),
    path('management/getinfo/', ajax.info, name='ajax-getinfo'),
    path('management/tags/', ajax.tag),

    # Attached file zone
    path('management/uploadfile/', files.UploadFileView.as_view(), name='upload-file'),
    path('management/checkfile/<int:file_id>/', files.check_file, name='check-file'),
    path('management/deletefile/', files.delete_file, name='delete-file'),
]

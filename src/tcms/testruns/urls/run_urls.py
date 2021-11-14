# -*- coding: utf-8 -*-

from django.urls import path

from tcms.testruns import ajax, views

urlpatterns = [
    path("new/", views.new, name="run-new"),
    path("<int:run_id>/", views.get, name="run-get"),
    path("<int:run_id>/clone/", views.new_run_with_caseruns, name="run-clone"),
    path("<int:run_id>/delete/", views.delete, name="run-delete"),
    path("<int:run_id>/edit/", views.edit, name="run-edit"),
    path("<int:run_id>/report/", views.TestRunReportView.as_view(), name="run-report"),
    path("<int:run_id>/ordercase/", views.order_case, name="run-order-case"),
    path(
        "<int:run_id>/changestatus/",
        views.ChangeRunStatusView.as_view(),
        name="run-change-status",
    ),
    path("<int:run_id>/ordercaserun/", views.order_case, name="run-order-caserun"),
    path(
        "<int:run_id>/removecaserun/",
        views.RemoveCaseRunView.as_view(),
        name="run-remove-caserun",
    ),
    path(
        "<int:run_id>/assigncase/",
        views.AddCasesToRunView.as_view(),
        name="add-cases-to-run",
    ),
    path("<int:run_id>/cc/", views.cc, name="run-cc"),
    path("<int:run_id>/update/", views.update_case_run_text, name="run-update"),
    path("<int:run_id>/export/", views.export, name="run-export"),
    path(
        "<int:run_id>/case-run/<int:case_run_id>/file-issue/",
        views.FileIssueForCaseRun.as_view(),
        name="run-caserun-file-issue",
    ),
    path("<int:run_id>/issues/", ajax.manage_case_run_issues, name="run-issues"),
    path(
        "<int:run_id>/statistics/",
        views.RunStatisticsView.as_view(),
        name="run-statistics",
    ),
]

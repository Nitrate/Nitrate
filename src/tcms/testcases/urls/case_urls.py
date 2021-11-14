# -*- coding: utf-8 -*-

from django.urls import path

from tcms.testruns import views as testruns_views

from .. import views

urlpatterns = [
    path("<int:case_id>/", views.get, name="case-get"),
    path("<int:case_id>/edit/", views.edit, name="case-edit"),
    path("<int:case_id>/history/", views.text_history, name="case-text-history"),
    path(
        "<int:case_id>/attachment/",
        views.ListCaseAttachmentsView.as_view(),
        name="case-attachment",
    ),
    path("<int:case_id>/log/", views.get_log, name="case-get-log"),
    path(
        "<int:case_id>/issues/add/",
        views.AddIssueToCases.as_view(),
        name="cases-add-issue",
    ),
    path(
        "<int:case_id>/issues/delete/",
        views.DeleteIssueFromCases.as_view(),
        name="cases-delete-issue",
    ),
    path("<int:case_id>/plan/", views.plan, name="case-plan"),
    path(
        "<int:case_id>/plans/add/",
        views.AddCaseToPlansView.as_view(),
        name="case-add-to-plans",
    ),
    path(
        "<int:case_id>/plans/remove/",
        views.RemoveCaseFromPlansView.as_view(),
        name="case-remove-from-plans",
    ),
    path(
        "<int:case_id>/readonly-pane/",
        views.SimpleTestCaseView.as_view(),
        name="case-readonly-pane",
    ),
    path(
        "<int:case_id>/review-pane/",
        views.TestCaseReviewPaneView.as_view(),
        name="case-review-pane",
    ),
    path(
        "<int:case_id>/caserun-list-pane/",
        views.TestCaseCaseRunListPaneView.as_view(),
        name="caserun-list-pane",
    ),
    path(
        "<int:case_id>/caserun-simple-pane/",
        views.TestCaseSimpleCaseRunView.as_view(),
        name="caserun-simple-pane",
    ),
    path(
        "<int:case_id>/caserun-detail-pane/",
        views.TestCaseCaseRunDetailPanelView.as_view(),
        name="caserun-detail-pane",
    ),
    path(
        "<int:plan_id>/runs/",
        testruns_views.load_runs_of_one_plan,
        name="load_runs_of_one_plan_url",
    ),
]

# -*- coding: utf-8 -*-

from django.urls import path

from tcms.testruns import views as testruns_views

from .. import views

urlpatterns = [
    path("<int:plan_id>/", views.get, name="plan-get"),
    path("<int:plan_id>/<slug:slug>", views.get, name="plan-get"),
    path("<int:plan_id>/delete/", views.delete, name="plan-delete"),
    path(
        "<int:plan_id>/chooseruns/",
        views.AddCasesToRunsView.as_view(),
        name="plan-choose-run",
    ),
    path("<int:plan_id>/edit/", views.edit, name="plan-edit"),
    path("<int:plan_id>/attachment/", views.attachment, name="plan-attachment"),
    path("<int:plan_id>/history/", views.text_history, name="plan-text-history"),
    path(
        "<int:plan_id>/reorder-cases/",
        views.ReorderCasesView.as_view(),
        name="plan-reorder-cases",
    ),
    path(
        "<int:plan_id>/link-cases/",
        views.LinkCasesView.as_view(),
        name="plan-link-cases",
    ),
    path(
        "<int:plan_id>/link-cases/search/",
        views.LinkCasesSearchView.as_view(),
        name="plan-search-cases-for-link",
    ),
    path(
        "<int:plan_id>/import-cases/",
        views.ImportCasesView.as_view(),
        name="plan-import-cases",
    ),
    path(
        "<int:plan_id>/delete-cases/",
        views.DeleteCasesView.as_view(),
        name="plan-delete-cases",
    ),
    path(
        "<int:plan_id>/runs/",
        testruns_views.load_runs_of_one_plan,
        name="load_runs_of_one_plan_url",
    ),
    path(
        "<int:plan_id>/set-enable/",
        views.SetPlanActiveView.as_view(enable=True),
        name="plan-set-enable",
    ),
    path(
        "<int:plan_id>/set-disable/",
        views.SetPlanActiveView.as_view(enable=False),
        name="plan-set-disable",
    ),
    path("<int:plan_id>/treeview/", views.construct_plans_treeview, name="plan-treeview"),
    path(
        "<int:plan_id>/treeview/add-children/",
        views.treeview_add_child_plans,
        name="plan-treeview-add-children",
    ),
    path(
        "<int:plan_id>/treeview/remove-children/",
        views.treeview_remove_child_plans,
        name="plan-treeview-remove-children",
    ),
    path(
        "<int:plan_id>/treeview/change-parent/",
        views.PlanTreeChangeParentView.as_view(),
        name="plan-treeview-change-parent",
    ),
]

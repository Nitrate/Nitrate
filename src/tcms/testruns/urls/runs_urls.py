# -*- coding: utf-8 -*-

from django.urls import path

from .. import views

urlpatterns = [
    path("", views.search_runs, name="runs-all"),
    path("clone/", views.clone, name="runs-clone"),
    path(
        "env_value/add/",
        views.AddEnvValueToRunView.as_view(),
        name="runs-add-env-value",
    ),
    path(
        "env_value/change/",
        views.ChangeRunEnvValueView.as_view(),
        name="runs-change-env-value",
    ),
    path(
        "env_value/delete/",
        views.DeleteRunEnvValueView.as_view(),
        name="runs-delete-env-value",
    ),
    path("case-runs/comment-many/", views.comment_case_runs, name="caserun-comment-caseruns"),
]

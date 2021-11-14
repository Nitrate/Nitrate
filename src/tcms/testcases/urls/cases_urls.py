# -*- coding: utf-8 -*-

from django.urls import path

from .. import views

urlpatterns = [
    path("new/", views.new, name="cases-new"),
    path("", views.all, name="cases-all"),
    path("search/", views.search_cases, name="cases-search"),
    path("subtotal/by-status/", views.simple_subtotal_by_status, name="cases-subtotal-by-status"),
    path(
        "automated/",
        views.ChangeCaseAutomatedPropertyView.as_view(),
        name="cases-automated",
    ),
    path(
        "tag-candidates-for-removal/",
        views.tag_candidates_list_for_removal,
        name="cases-tag-candidates-for-removal",
    ),
    path("category/", views.category, name="cases-category"),
    path("clone/", views.clone, name="cases-clone"),
    path("printable/", views.printable, name="cases-printable"),
    path("export/", views.export, name="cases-export"),
    path("add-component/", views.AddComponentView.as_view(), name="cases-add-component"),
    path(
        "remove-component/",
        views.RemoveComponentView.as_view(),
        name="cases-remove-component",
    ),
    path(
        "get-component-form/",
        views.GetComponentFormView.as_view(),
        name="cases-get-component-form",
    ),
]

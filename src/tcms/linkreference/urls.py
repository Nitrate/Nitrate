# -*- coding: utf-8 -*-

from django.urls import path

from tcms.linkreference import views

urlpatterns = [
    path("add/", views.AddLinkToTargetView.as_view(), name="add-link-reference"),
    path("get/", views.get, name="get-link-references"),
    path(
        "remove/<int:link_id>/",
        views.RemoveLinkReferenceView.as_view(),
        name="remove-link-reference",
    ),
]

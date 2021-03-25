# -*- coding: utf-8 -*-

from django.urls import path
from django.views.generic.base import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(url="overall/", permanent=True)),
    path("overall/", views.overall, name="report-overall"),
    path("product/<int:product_id>/overview/", views.overview, name="report-overview"),
    path(
        "product/<int:product_id>/build/",
        views.ProductBuildReport.as_view(),
        name="report-overall-product-build",
    ),
    path(
        "product/<int:product_id>/version/",
        views.ProductVersionReport.as_view(),
        name="report-overall-product-version",
    ),
    path(
        "product/<int:product_id>/component/",
        views.ProductComponentReport.as_view(),
        name="report-overall-product-component",
    ),
    path("custom/", views.CustomReport.as_view(), name="report-custom"),
    path(
        "custom/details/",
        views.CustomDetailReport.as_view(),
        name="report-custom-details",
    ),
    path("testing/", views.TestingReport.as_view(), name="testing-report"),
    path(
        "testing/case-runs/",
        views.TestingReportCaseRuns.as_view(),
        name="testing-report-case-runs",
    ),
]

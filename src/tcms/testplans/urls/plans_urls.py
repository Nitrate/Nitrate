# -*- coding: utf-8 -*-

from django.urls import path

from .. import views

urlpatterns = [
    path("", views.SearchPlansView.as_view(), name="plans-all"),
    path("pages/", views.SearchPlansPagesView.as_view(), name="plans-pages"),
    # # FIXME: probably should move to testcases app
    path(
        "clone-cases/",
        views.SimplePlansFilterView.as_view(template_name="case/clone_select_plan.html"),
        name="plans-for-cloning-cases",
    ),
    path(
        "preview/",
        views.SimplePlansFilterView.as_view(template_name="plan/preview.html"),
        name="plans-for-preview",
    ),
    path("new/", views.CreateNewPlanView.as_view(), name="plans-new"),
    path("clone/", views.clone, name="plans-clone"),
    path("printable/", views.printable, name="plans-printable"),
    path("export/", views.export, name="plans-export"),
    # path('component/', views.component, name='plans-component'),
    path(
        "component/",
        views.PlanComponentsActionView.as_view(),
        name="plans-component-actions",
    ),
]

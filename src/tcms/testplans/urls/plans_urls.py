# -*- coding: utf-8 -*-

from django.urls import path
from .. import views

urlpatterns = [
    path('', views.all, name='plans-all'),
    path('new/', views.CreateNewPlanView.as_view(), name='plans-new'),
    path('ajax/', views.ajax_search, name='plans-ajax-search'),
    path('treeview/', views.tree_view, name='plans-treeview'),
    path('clone/', views.clone, name='plans-clone'),
    path('printable/', views.printable, name='plans-printable'),
    path('export/', views.export, name='plans-export'),
    # path('component/', views.component, name='plans-component'),

    path('component/', views.PlanComponentsActionView.as_view(),
         name='plans-component-actions'),
]

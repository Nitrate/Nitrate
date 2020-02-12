# -*- coding: utf-8 -*-

from django.urls import path

from .. import views

urlpatterns = [
    path('', views.all, name='runs-all'),
    path('ajax/', views.ajax_search, name='runs-ajax-search'),
    path('env_value/', views.env_value, name='runs-env-value'),
    path('clone/', views.clone, name='runs-clone'),
]

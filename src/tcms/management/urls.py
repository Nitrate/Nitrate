# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('environment/groups/', views.environment_groups,
         name='management-env-groups'),
    path('environment/group/edit/', views.environment_group_edit,
         name='management-env-group-edit'),
    path('environment/properties/', views.environment_properties,
         name='management-env-properties'),
    path('environment/properties/values/', views.environment_property_values,
         name='management-env-properties-values'),
]

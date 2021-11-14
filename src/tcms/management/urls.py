# -*- coding: utf-8 -*-

from django.urls import path

from tcms.management import views

urlpatterns = [
    # Views for environment groups
    path(
        "environment/groups/",
        views.EnvironmentGroupsListView.as_view(),
        name="management-env-groups",
    ),
    path(
        "environment/groups/add/",
        views.EnvironmentGroupAddView.as_view(),
        name="management-add-env-group",
    ),
    path(
        "environment/groups/<int:env_group_id>/set-status/",
        views.EnvironmentGroupSetStatusView.as_view(),
        name="management-set-env-group-status",
    ),
    path(
        "environment/groups/<int:env_group_id>/delete/",
        views.EnvironmentGroupDeleteView.as_view(),
        name="management-delete-env-group",
    ),
    path(
        "environment/groups/<int:env_group_id>/edit/",
        views.EnvironmentGroupEditView.as_view(),
        name="management-env-group-edit",
    ),
    # Views for environment properties and values
    path(
        "environment/properties/",
        views.EnvironmentPropertiesView.as_view(),
        name="management-env-properties",
    ),
    path(
        "environment/properties/add/",
        views.EnvironmentPropertyAddView.as_view(),
        name="management-add-env-property",
    ),
    path(
        "environment/properties/<int:env_property_id>/edit/",
        views.EnvironmentPropertyEditView.as_view(),
        name="management-edit-env-property",
    ),
    path(
        "environment/properties/set-status/",
        views.EnvironmentPropertySetStatusView.as_view(),
        name="management-set-env-property-status",
    ),
    path(
        "environment/properties/<int:property_id>/values/",
        views.EnvironmentPropertyValuesListView.as_view(),
        name="management-env-properties-values",
    ),
    path(
        "environment/properties/<int:env_property_id>/values/add/",
        views.EnvironmentPropertyValuesAddView.as_view(),
        name="management-add-env-property-values",
    ),
    path(
        "environment/properties/values/set-status/",
        views.EnvironmentPropertyValuesSetStatusView.as_view(),
        name="management-set-env-property-values-status",
    ),
    path(
        "environment/properties/values/<int:property_value_id>/edit/",
        views.EnvironmentPropertyValueEditView.as_view(),
        name="management-env-property-value-edit",
    ),
]

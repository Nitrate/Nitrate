# -*- coding: utf-8 -*-

from itertools import groupby
from operator import attrgetter, itemgetter

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView, View

from tcms.core.responses import JsonResponseBadRequest, JsonResponseForbidden, JsonResponseNotFound
from tcms.core.utils import QuerySetIterationProxy
from tcms.logs.models import TCMSLogModel
from tcms.management.models import (
    TCMSEnvGroup,
    TCMSEnvGroupPropertyMap,
    TCMSEnvProperty,
    TCMSEnvValue,
)

MODULE_NAME = "management"


class EnvironmentGroupAddView(PermissionRequiredMixin, View):
    """Add new environment group"""

    permission_required = "management.add_tcmsenvgroup"

    def post(self, request):
        group_name = request.POST.get("name")

        # Get the group name of environment from javascript
        if not group_name:
            return JsonResponseBadRequest({"message": "Environment group name is required."})

        if TCMSEnvGroup.objects.filter(name=group_name).exists():
            return JsonResponseBadRequest(
                {
                    "message": f'Environment group name "{group_name}" already'
                    f" exists, please choose another name."
                }
            )

        env = TCMSEnvGroup.objects.create(
            name=group_name, manager_id=request.user.id, modified_by_id=None
        )
        env.log_action(who=request.user, new_value=f"Initial env group {env.name}")
        return JsonResponse({"env_group_id": env.id})


class EnvironmentGroupDeleteView(View):
    """Delete environment group"""

    def post(self, request, env_group_id):
        try:
            group = TCMSEnvGroup.objects.get(pk=int(env_group_id))
        except TCMSEnvGroup.DoesNotExist:
            return JsonResponseNotFound(
                {"message": f"Environment group with id {env_group_id} does not exist."}
            )
        else:
            if request.user.pk != group.manager_id and not request.user.has_perm(
                "management.delete_tcmsenvgroup"
            ):
                return JsonResponseForbidden(
                    {
                        "message": f"You are not allowed to delete environment "
                        f"group {group.name}."
                    }
                )

            group.delete()

        return JsonResponse({"env_group_id": int(env_group_id)})


class EnvironmentGroupSetStatusView(PermissionRequiredMixin, View):
    """Modify an environment group"""

    permission_required = "management.change_tcmsenvgroup"

    def post(self, request, env_group_id):
        status = request.POST.get("status")
        if status is None:
            return JsonResponseBadRequest({"message": "Environment group status is missing."})
        if status not in ["0", "1"]:
            return JsonResponseBadRequest(
                {"message": f'Environment group status "{status}" is invalid.'}
            )
        try:
            env = TCMSEnvGroup.objects.get(pk=int(env_group_id))
        except TCMSEnvGroup.DoesNotExist:
            return JsonResponseNotFound(
                {"message": f"Environment group with id {env_group_id} does not exist."}
            )
        else:
            new_status = bool(int(status))
            if env.is_active != new_status:
                env.is_active = new_status
                env.save(update_fields=["is_active"])

                env.log_action(
                    who=request.user,
                    field="is_active",
                    original_value=env.is_active,
                    new_value=new_status,
                )

            return JsonResponse({"env_group_id": env_group_id})


class EnvironmentGroupsListView(TemplateView):
    """The environment groups index page"""

    template_name = "environment/groups.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "name" in self.request.GET:
            env_groups = TCMSEnvGroup.objects.filter(name__icontains=self.request.GET["name"])
        else:
            env_groups = TCMSEnvGroup.objects.all()

        # Get properties for each group
        qs = (
            TCMSEnvGroupPropertyMap.objects.filter(group__in=env_groups)
            .values("group__pk", "property__name")
            .order_by("group__pk", "property__name")
            .iterator()
        )
        properties = {key: list(value) for key, value in groupby(qs, itemgetter("group__pk"))}

        # Get logs for each group
        env_group_ct = ContentType.objects.get_for_model(TCMSEnvGroup)
        qs = (
            TCMSLogModel.objects.filter(content_type=env_group_ct, object_pk__in=env_groups)
            .only(
                "object_pk",
                "who__username",
                "date",
                "field",
                "original_value",
                "new_value",
            )
            .order_by("object_pk")
        )

        # we have to convert object_pk to an integer due to it's a string stored in
        # database.
        logs = {int(key): list(value) for key, value in groupby(qs, attrgetter("object_pk"))}

        env_groups = (
            env_groups.select_related("modified_by", "manager")
            .order_by("is_active", "name")
            .iterator()
        )

        context.update(
            {
                "environments": QuerySetIterationProxy(
                    env_groups, properties=properties, another_logs=logs
                ),
                "module": "env",
            }
        )
        return context


class EnvironmentGroupEditView(PermissionRequiredMixin, View):
    """Edit environment group"""

    permission_required = "management.change_tcmsenvgroup"
    template_name = "environment/group_edit.html"

    def get(self, request, env_group_id):
        env_group = get_object_or_404(TCMSEnvGroup, pk=env_group_id)
        context_data = {
            "environment": env_group,
            "properties": TCMSEnvProperty.get_active(),
            "selected_properties": env_group.property.all(),
            "message": "",
        }
        return render(request, self.template_name, context=context_data)

    def post(self, request, env_group_id):
        env_group = get_object_or_404(TCMSEnvGroup, pk=env_group_id)
        de = TCMSEnvGroup.objects.filter(name=request.POST["name"]).first()
        if de and env_group != de:
            context_data = {
                "environment": env_group,
                "properties": TCMSEnvProperty.get_active(),
                "selected_properties": env_group.property.all(),
                "message": "Duplicated name already exists, please change to another name.",
            }
            return render(request, self.template_name, context=context_data)

        new_name = request.POST["name"]
        if env_group.name != new_name:
            original_name = env_group.name
            env_group.name = new_name
            env_group.log_action(
                who=request.user,
                field="name",
                original_value=original_name,
                new_value=new_name,
            )

        enable_group = "enabled" in request.POST
        if env_group.is_active != enable_group:
            original_value = env_group.is_active
            env_group.is_active = enable_group
            env_group.log_action(
                who=request.user,
                field="is_active",
                original_value=original_value,
                new_value=enable_group,
            )

        env_group.modified_by_id = request.user.id
        env_group.save()

        existing_properties = set(env_group.property.all())
        selected_property_ids = list(map(int, request.POST.getlist("selected_property_ids")))
        selected_properties = set(TCMSEnvProperty.objects.filter(pk__in=selected_property_ids))

        newly_selected_properties = selected_properties - existing_properties

        if newly_selected_properties:
            for env_property in newly_selected_properties:
                TCMSEnvGroupPropertyMap.objects.create(group=env_group, property=env_property)

            env_group.log_action(
                who=request.user,
                field="Property values",
                original_value=", ".join(sorted(item.name for item in existing_properties)),
                new_value=", ".join(sorted(item.name for item in newly_selected_properties)),
            )

        response = "Environment group saved successfully."

        context_data = {
            "environment": env_group,
            "properties": TCMSEnvProperty.get_active(),
            "selected_properties": env_group.property.order_by("name"),
            "message": response,
        }
        return render(request, self.template_name, context=context_data)


class EnvironmentPropertyAddView(PermissionRequiredMixin, View):
    """Add an environment property"""

    permission_required = "management.add_tcmsenvproperty"

    def post(self, request):
        property_name = request.POST.get("name")

        if not property_name:
            return JsonResponseBadRequest({"message": "Property name is missing."})

        if TCMSEnvProperty.objects.filter(name=property_name).exists():
            return JsonResponseBadRequest(
                {
                    "message": f"Environment property {property_name} "
                    f"already exists, please choose another name."
                }
            )

        new_property = TCMSEnvProperty.objects.create(name=property_name)

        return JsonResponse({"id": new_property.pk, "name": new_property.name})


class EnvironmentPropertyEditView(PermissionRequiredMixin, View):
    """Edit an environment property"""

    permission_required = "management.change_tcmsenvproperty"

    def post(self, request, env_property_id):
        env_property = TCMSEnvProperty.objects.filter(pk=env_property_id).first()
        if env_property is None:
            return JsonResponseBadRequest(
                {"message": f"Environment property with id {env_property_id} " f"does not exist."}
            )

        new_name = request.POST.get("name", env_property.name)
        env_property.name = new_name
        env_property.save(update_fields=["name"])

        return JsonResponse({"id": env_property_id, "name": new_name})


class EnvironmentPropertySetStatusView(PermissionRequiredMixin, View):
    """Enable or disable environment properties"""

    permission_required = "management.change_tcmsenvproperty"

    def post(self, request):
        property_ids = request.POST.getlist("id")

        if not property_ids:
            return JsonResponseBadRequest(
                {"message": "Missing environment property ids. Nothing changed."}
            )

        invalid_ids = list(filter(lambda item: not item.isdigit(), property_ids))
        if invalid_ids:
            if len(invalid_ids) > 1:
                msg = f'Environment property ids {", ".join(invalid_ids)} are not number.'
            else:
                msg = f"Environment property id {invalid_ids[0]} is not a number."
            return JsonResponseBadRequest({"message": msg})

        new_status = request.POST.get("status")
        if new_status is None:
            return JsonResponseBadRequest({"message": "Missing status."})
        if new_status not in ["0", "1"]:
            return JsonResponseBadRequest({"message": f"Invalid status {new_status}."})

        property_ids = list(map(int, property_ids))
        env_properties = TCMSEnvProperty.objects.filter(pk__in=property_ids)

        for env_property in env_properties:
            env_property.is_active = bool(int(new_status))
            env_property.save()

        # FIXME: why delete such properties?
        if not env_property.is_active:
            TCMSEnvGroupPropertyMap.objects.filter(property__id__in=property_ids).delete()

        return JsonResponse({"property_ids": property_ids})


class EnvironmentPropertiesView(TemplateView):
    """Environment properties index view"""

    template_name = "environment/property.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"properties": TCMSEnvProperty.objects.order_by("-is_active", "name")})
        return context


class EnvironmentPropertyValuesAddView(PermissionRequiredMixin, View):
    """Add environment property values"""

    permission_required = "management.add_tcmsenvvalue"
    template_name = "environment/ajax/property_values.html"

    def post(self, request, env_property_id):
        env_property = TCMSEnvProperty.objects.filter(pk=env_property_id).first()
        if env_property is None:
            return HttpResponseNotFound(
                f"Environment property id {env_property_id} does not exist.",
            )

        new_values = set(map(lambda item: item.strip(), request.POST.getlist("value")))
        existing_values = set(env_property.value.values_list("value", flat=True))
        values_to_add = set(new_values) - set(existing_values)

        for value in values_to_add:
            TCMSEnvValue.objects.create(value=value, property=env_property)

        return render(
            request,
            self.template_name,
            context={
                "property": env_property,
                "values": TCMSEnvValue.objects.filter(property=env_property).order_by("value"),
            },
        )


class EnvironmentPropertyValuesSetStatusView(PermissionRequiredMixin, View):
    """Disable or enable environment property values"""

    permission_required = "management.change_tcmsenvvalue"
    template_name = "environment/ajax/property_values.html"

    def post(self, request):
        value_ids = request.POST.getlist("id")
        if not value_ids:
            return HttpResponseBadRequest("Property value id is missing.")

        cleaned_value_ids = []
        for item in value_ids:
            cleaned_item = item.strip()
            if not cleaned_item:
                continue
            if not cleaned_item.isdigit():
                return HttpResponseBadRequest(f"Value id {cleaned_item} is not an integer.")
            cleaned_value_ids.append(int(cleaned_item))

        status = request.POST.get("status")
        if status is None:
            return HttpResponseBadRequest("Status is missing")
        if status not in ["0", "1"]:
            return HttpResponseBadRequest(f"Status {status} is invalid.")

        new_status = bool(int(status))
        values = TCMSEnvValue.objects.filter(pk__in=cleaned_value_ids)
        for value in values:
            value.is_active = new_status
            value.save()

        env_property = values[0].property
        return render(
            request,
            self.template_name,
            context={
                "property": env_property,
                "values": TCMSEnvValue.objects.filter(property=env_property).order_by("value"),
            },
        )


class EnvironmentPropertyValueEditView(PermissionRequiredMixin, View):
    """Edit an environment property value"""

    permission_required = "management.change_tcmsenvvalue"
    template_name = "environment/ajax/property_values.html"

    def post(self, request, property_value_id):
        new_value = request.POST.get("value")
        if new_value is None:
            return HttpResponseBadRequest("Missing new value to update.")
        if not new_value:
            return HttpResponseBadRequest("The value is empty.")

        property_value = TCMSEnvValue.objects.filter(pk=property_value_id).first()
        if property_value is None:
            return HttpResponseNotFound(f"Property value id {property_value_id} does not exist.")

        property_value.value = new_value
        property_value.save(update_fields=["value"])

        return render(
            request,
            self.template_name,
            context={
                "property": property_value.property,
                "values": TCMSEnvValue.objects.filter(property=property_value.property).order_by(
                    "value"
                ),
            },
        )


class EnvironmentPropertyValuesListView(TemplateView):
    """List of environment property values"""

    template_name = "environment/ajax/property_values.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        env_property = get_object_or_404(TCMSEnvProperty, pk=self.kwargs["property_id"])
        context.update(
            {
                "property": env_property,
                "values": env_property.value.order_by("value"),
            }
        )

        return context

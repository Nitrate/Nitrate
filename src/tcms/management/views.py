# -*- coding: utf-8 -*-

from json import dumps as json_dumps
from itertools import groupby
from operator import itemgetter

from django.contrib.auth.decorators import permission_required
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.http import Http404
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from tcms.logs.models import TCMSLogModel
from tcms.core.utils import QuerySetIterationProxy
from tcms.management.models import TCMSEnvGroup
from tcms.management.models import TCMSEnvGroupPropertyMap
from tcms.management.models import TCMSEnvProperty
from tcms.management.models import TCMSEnvValue

MODULE_NAME = "management"


@require_GET
def environment_groups(request, template_name='environment/groups.html'):
    """
    Environements list
    """

    env_groups = TCMSEnvGroup.objects

    has_perm = request.user.has_perm
    user_action = request.GET.get('action')

    # Add action
    if user_action == 'add':
        if not has_perm('management.add_tcmsenvgroup'):
            return JsonResponse({'rc': 1, 'response': 'Permission denied.'})

        group_name = request.GET.get('name')

        # Get the group name of envrionment from javascript
        if not group_name:
            return JsonResponse(
                {'rc': 1, 'response': 'Environment group name is required.'})

        if env_groups.filter(name=group_name).exists():
            response_msg = (
                f"Environment group name '{group_name}' already exists, "
                f"please select another name."
            )
            return JsonResponse({'rc': 1, 'response': response_msg})
        else:
            env = env_groups.create(name=group_name,
                                    manager_id=request.user.id,
                                    modified_by_id=None)
            env.log_action(who=request.user,
                           new_value='Initial env group %s' % env.name)
            return JsonResponse({'rc': 0, 'response': 'ok', 'id': env.id})

    # Del action
    if user_action == 'del':
        if not request.GET.get('id'):
            raise Http404

        try:
            group_pk = int(request.GET['id'])
        except ValueError:
            return JsonResponse({'rc': 1, 'response': 'id must be an integer.'})

        groups = list(env_groups.filter(pk=group_pk))
        if len(groups) == 0:
            raise Http404

        if request.user.pk != groups[0].manager_id:
            if not has_perm('management.delete_tcmsenvgroup'):
                return JsonResponse({'rc': 1, 'response': 'Permission denied.'})

        groups[0].delete()

        return JsonResponse({'rc': 0, 'response': 'ok'})

    # Modify actions
    if user_action == 'modify':
        if not has_perm('management.change_tcmsenvgroup'):
            return JsonResponse({'rc': 1, 'response': 'Permission denied.'})

        try:
            env = env_groups.get(id=request.GET['id'])
            if request.GET.get('status') in ['0', '1']:
                returned_status = bool(int(request.GET['status']))
                if env.is_active != returned_status:
                    env.is_active = returned_status
                    env.save(update_fields=['is_active'])

                    env.log_action(
                        who=request.user,
                        field='is_active',
                        original_value=env.is_active,
                        new_value=returned_status)
            else:
                return JsonResponse({'rc': 1, 'response': 'Argument illegel.'})
        except TCMSEnvGroup.DoesNotExist as error:
            raise Http404(error)

    # Search actions
    if user_action == 'search':
        if request.GET.get('name'):
            env_groups = env_groups.filter(
                name__icontains=request.GET['name']
            )
        else:
            env_groups = env_groups.all()
    else:
        env_groups = env_groups.all().order_by('is_active')

    # Get properties for each group
    qs = TCMSEnvGroupPropertyMap.objects.filter(group__in=env_groups)
    qs = qs.values('group__pk', 'property__name')
    qs = qs.order_by('group__pk', 'property__name').iterator()
    properties = {
        key: list(value) for key, value in groupby(qs, itemgetter('group__pk'))
    }

    # Get logs for each group
    env_group_ct = ContentType.objects.get_for_model(TCMSEnvGroup)
    qs = TCMSLogModel.objects.filter(content_type=env_group_ct,
                                     object_pk__in=env_groups)
    qs = qs.values('object_pk', 'who__username', 'date', 'field',
                   'original_value', 'new_value')
    qs = qs.order_by('object_pk').iterator()
    # we have to convert object_pk to an integer due to it's a string stored in
    # database.
    logs = {
        int(key): list(value) for key, value in
        groupby(qs, itemgetter('object_pk'))
    }

    env_groups = env_groups.select_related('modified_by', 'manager').iterator()

    env_groups = QuerySetIterationProxy(env_groups,
                                        properties=properties,
                                        another_logs=logs)
    context_data = {
        'environments': env_groups,
        'module': 'env',
    }
    return render(request, template_name, context=context_data)


@require_GET
@permission_required('management.change_tcmsenvgroup')
def environment_group_edit(request, template_name='environment/group_edit.html'):
    """
    Assign properties to environment group
    """

    # Initial the response
    response = ''
    environment_id = request.GET.get('id', None)

    if environment_id is None:
        raise Http404

    try:
        environment = TCMSEnvGroup.objects.get(pk=environment_id)
    except TCMSEnvGroup.DoesNotExist:
        raise Http404

    try:
        de = TCMSEnvGroup.objects.get(name=request.GET.get('name'))
        if environment != de:
            context_data = {
                'environment': environment,
                'properties': TCMSEnvProperty.get_active(),
                'selected_properties': environment.property.all(),
                'message': 'Duplicated name already exists, please change to '
                           'another name.',
            }
            return render(request, template_name, context=context_data)
    except TCMSEnvGroup.DoesNotExist:
        pass

    if request.GET.get('action') == 'modify':   # Actions of modify
        environment_name = request.GET['name']
        if environment.name != environment_name:
            original_value = environment.name
            environment.name = environment_name
            environment.log_action(
                who=request.user,
                field='name',
                original_value=original_value,
                new_value=environment_name)

        returned_env_status = 'enabled' in request.GET
        if environment.is_active != returned_env_status:
            original_value = environment.is_active
            environment.is_active = returned_env_status
            environment.log_action(
                who=request.user,
                field='is_active',
                original_value=original_value,
                new_value=returned_env_status)

        environment.modified_by_id = request.user.id
        environment.save()

        original_property_values = list(
            environment.property.values_list('name', flat=True))
        original_property_values.sort()

        # Remove all of properties of the group.
        TCMSEnvGroupPropertyMap.objects.filter(group__id=environment.id).delete()

        # Readd the property to environemnt group and log the action
        for property_id in request.GET.getlist('selected_property_ids'):
            TCMSEnvGroupPropertyMap.objects.create(group_id=environment.id,
                                                   property_id=property_id)

        new_property_values = list(
            environment.property.values_list('name', flat=True))
        new_property_values.sort()

        environment.log_action(
            who=request.user,
            field='Property values',
            original_value=', '.join(original_property_values),
            new_value=', '.join(new_property_values))

        response = 'Environment group saved successfully.'

    context_data = {
        'environment': environment,
        'properties': TCMSEnvProperty.get_active(),
        'selected_properties': environment.property.all(),
        'message': response,
    }
    return render(request, template_name, context=context_data)


@require_GET
def environment_properties(request, template_name='environment/property.html'):
    """
    Edit environemnt properties and values belong to
    """

    # Initial the ajax response
    ajax_response = {'rc': 0, 'response': 'ok'}
    message = ''

    has_perm = request.user.has_perm
    user_action = request.GET.get('action')

    # Actions of create properties
    if user_action == 'add':
        if not has_perm('management.add_tcmsenvproperty'):
            return JsonResponse({'rc': 1, 'response': 'Permission denied'})

        property_name = request.GET.get('name')

        if not property_name:
            return JsonResponse({'rc': 1, 'response': 'Property name is required'})

        if TCMSEnvProperty.objects.filter(name=property_name).exists():
            resp_msg = (
                f"Environment property named '{property_name}' already exists,"
                f" please select another name."
            )
            return JsonResponse({'rc': 1, 'response': resp_msg})

        new_property = TCMSEnvProperty.objects.create(name=property_name)

        return JsonResponse({
            'rc': 0,
            'response': 'ok',
            'id': new_property.pk,
            'name': new_property.name
        })

    # Actions of edit a exist properties
    if user_action == 'edit':
        if not has_perm('management.change_tcmsenvproperty'):
            return JsonResponse({'rc': 1, 'response': 'Permission denied'})

        if not request.GET.get('id'):
            return JsonResponse({'rc': 1, 'response': 'ID is required'})

        try:
            property_id = request.GET['id']
            env_property = TCMSEnvProperty.objects.get(id=int(property_id))
        except ValueError:
            return JsonResponse({
                'rc': 1,
                'response': f'ID {property_id} is not a valid integer.'
            })
        except TCMSEnvProperty.DoesNotExist:
            return JsonResponse({'rc': 1, 'response': 'ID does not exist.'})

        new_name = request.GET.get('name', env_property.name)
        env_property.name = new_name
        try:
            env_property.save(update_fields=['name'])
        except Exception:
            return JsonResponse({'rc': 1, 'response': 'Cannot save property.'})

        return JsonResponse({'rc': 0, 'response': 'ok'})

    # Actions of remove properties
    if user_action == 'modify':
        if not has_perm('management.change_tcmsenvproperty'):
            message = 'Permission denied'

        property_ids = request.GET.getlist('id')

        if has_perm('management.change_tcmsenvproperty') and property_ids:
            env_properties = TCMSEnvProperty.objects.filter(id__in=property_ids)

            if request.GET.get('status') in ['0', '1']:
                for env_property in env_properties:
                    env_property.is_active = int(request.GET['status'])
                    env_property.save()

                property_values = "', '".join(sorted(
                    env_properties.values_list('name', flat=True)))
                message = "Modify test properties status '%s' successfully." % property_values

                if not env_property.is_active:
                    TCMSEnvGroupPropertyMap.objects.filter(
                        property__id__in=property_ids).delete()
            else:
                message = 'Argument illegal'

    if request.is_ajax():
        ajax_response['rc'] = 1
        ajax_response['response'] = 'Unknown action'
        return HttpResponse(json_dumps(ajax_response))

    context_data = {
        'message': message,
        'properties': TCMSEnvProperty.objects.all().order_by('-is_active')
    }
    return render(request, template_name, context=context_data)


@require_GET
def environment_property_values(request):
    """
    List values of property
    """
    template_name = 'environment/ajax/property_values.html'
    message = ''
    duplicated_property_value = []

    if not request.GET.get('property_id'):
        return HttpResponse('Property ID should specify')

    try:
        property = TCMSEnvProperty.objects.get(id=request.GET['property_id'])
    except TCMSEnvProperty.DoesNotExist as error:
        return HttpResponse(error)

    user_action = request.GET.get('action')

    if user_action == 'add' and request.GET.get('value'):
        if not request.user.has_perm('management.add_tcmsenvvalue'):
            return HttpResponse('Permission denied')

        for value in request.GET['value'].split(','):
            try:
                property.value.create(value=value)
            except IntegrityError as error:
                if error[1].startswith('Duplicate'):
                    duplicated_property_value.append(value)

    if user_action == 'edit' and request.GET.get('id'):
        if not request.user.has_perm('management.change_tcmsenvvalue'):
            return HttpResponse('Permission denied')

        try:
            property_value = property.value.get(id=request.GET['id'])
            property_value.value = request.GET.get('value', property_value.value)
            try:
                property_value.save()
            except IntegrityError as error:
                if error[1].startswith('Duplicate'):
                    duplicated_property_value.append(property_value.value)

        except TCMSEnvValue.DoesNotExist as error:
            return HttpResponse(error[1])

    if user_action == 'modify' and request.GET.get('id'):
        if not request.user.has_perm('management.change_tcmsenvvalue'):
            return HttpResponse('Permission denied')

        values = property.value.filter(id__in=request.GET.getlist('id'))
        status = request.GET.get('status')
        if status in ['0', '1']:
            for value in values:
                value.is_active = int(status)
                value.save()
        else:
            return HttpResponse('Argument illegel')

    if duplicated_property_value:
        s = "', '".join(duplicated_property_value)
        message = (
            f"Value(s) named '{s}' already exists in this property, "
            f"please select another name."
        )

    values = property.value.all()
    context_data = {
        'property': property,
        'values': values,
        'message': message,
    }
    return render(request, template_name, context=context_data)

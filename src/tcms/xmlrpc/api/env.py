# -*- coding: utf-8 -*-

from tcms.management.models import TCMSEnvGroup, TCMSEnvProperty, TCMSEnvValue
from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.utils import parse_bool_value

__all__ = (
    "filter_groups",
    "filter_properties",
    "filter_values",
    "get_properties",
    "get_values",
)

__xmlrpc_namespace__ = "TestEnv"


@log_call(namespace=__xmlrpc_namespace__)
def filter_groups(request, query):
    """Performs a search and returns the resulting list of env groups.

    :param dict query: mapping containing following criteria to find out
        envrionment groups.

        * id: (int) environment group ID.
        * name: (str) environment group name.
        * manager: ForeignKey: Auth.user
        * modified_by: ForeignKey: Auth.user
        * is_active: (bool)
        * property: ForeignKey: :class:`TCMSEnvProperty`

    :return: list of mappings of found environment groups.
    :rtype: list

    Example::

        # Get all of env group name contains 'Desktop'
        Env.filter_groups({'name__icontains': 'Desktop'})
    """
    if "is_active" in query:
        query["is_active"] = parse_bool_value(query["is_active"])
    return TCMSEnvGroup.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def filter_properties(request, query):
    """Performs a search and returns the resulting list of env properties.

    :param dict query: mapping containing following criteria to find out
        environment properties.

        * id: (int) environment property ID.
        * name: (str) property name.
        * is_active: (bool) whether to find active properties.
        * group: ForeignKey: :class:`TCMSEnvGroup`
        * value: ForeignKey: :class:`TCMSEnvValues`

    :return: Array: Matching env properties are retuned in a list of hashes.

    Example::

        # Get all of env properties name contains 'Desktop'
        Env.filter_properties({'name__icontains': 'Desktop'})
    """
    if "is_active" in query:
        query["is_active"] = parse_bool_value(query["is_active"])
    return TCMSEnvProperty.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def filter_values(request, query):
    """Performs a search and returns the resulting list of env properties.

    :param dict query: mapping containing these criteria.

        * id: (int) ID of env value
        * value: (str)
        * is_active: (bool)
        * property: ForeignKey: :class:`TCMSEnvProperty`

    :return: list of mappings containing found environment property values.
    :rtype: list

    Example::

        # Get all of env values name contains 'Desktop'
        Env.filter_values({'name__icontains': 'Desktop'})
    """
    if "is_active" in query:
        query["is_active"] = parse_bool_value(query["is_active"])
    return TCMSEnvValue.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_properties(request, env_group_id=None, is_active=True):
    """Get the list of properties associated with this env group.

    :param int env_group_id: env_group_id of the env group in the Database
        Return all of properties when the argument is not specified.
    :param bool is_active: If ``True``, only include builds. Default: ``True``.
    :return: list of found environment properties.
    :rtype: list

    Example::

        # Get all of properties
        Env.get_properties()
        # Get the properties in group 10
        Env.get_properties(10)
    """
    query = {"is_active": parse_bool_value(is_active)}
    if env_group_id:
        query["group__pk"] = env_group_id

    return TCMSEnvProperty.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_values(request, env_property_id=None, is_active=True):
    """Get the list of values associated with this env property.

    :param int env_property_id: environment property ID. If omitted, all
        environment property values will be returned.
    :param bool is_active: indicate whether to get values from active
        properties. Default is ``True``.
    :return: list of mappings containing found environment property values.
    :rtype: list

    Example::

        # Get all values from active environment properties
        Env.get_values()
        # Get the properties in group 10
        Env.get_values(10)
    """
    query = {"is_active": parse_bool_value(is_active)}
    if env_property_id:
        query["property__pk"] = env_property_id

    return TCMSEnvValue.to_xmlrpc(query)

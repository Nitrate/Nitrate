# -*- coding: utf-8 -*-

from tcms.management.models import TestTag
from tcms.xmlrpc.decorators import log_call

__all__ = ("get_tags",)

__xmlrpc_namespace__ = "Tag"


@log_call(namespace=__xmlrpc_namespace__)
def get_tags(request, values):
    """Get tags by ID or name.

    :param dict values: a mapping containing these criteria.

        * ids: (list[int]) list of tag IDs.
        * names: (list[str]) list of names.

    :return: a list of mappings of :class:`TestTag`.
    :rtype: list

    Example::

        Tag.get_tags({'ids': [121, 123]})
    """
    if not isinstance(values, dict):
        raise TypeError("Argument values must be an dictionary.")
    if values.get("ids"):
        query = {"id__in": values.get("ids")}
        return TestTag.to_xmlrpc(query)
    elif values.get("names"):
        query = {"name__in": values.get("names")}
        return TestTag.to_xmlrpc(query)
    else:
        raise ValueError("Must specify ids or names at least.")

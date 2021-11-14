# -*- coding: utf-8 -*-

from tcms.xmlrpc import get_version
from tcms.xmlrpc.decorators import log_call

__all__ = ("get",)

__xmlrpc_namespace__ = "Version"


@log_call(namespace=__xmlrpc_namespace__)
def get(request):
    """Retrieve XMLRPC's version

    :return: A list that represents the version.
    :rtype: list

    Example:

        Version.get()
    """

    return get_version()

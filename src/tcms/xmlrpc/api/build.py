# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import permission_required

from tcms.management.models import TestBuild
from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.utils import parse_bool_value, pre_check_product

__all__ = (
    "check_build",
    "create",
    "get",
    "get_runs",
    "get_caseruns",
    "lookup_id_by_name",
    "lookup_name_by_id",
    "update",
)

__xmlrpc_namespace__ = "TestBuild"


@log_call(namespace=__xmlrpc_namespace__)
def check_build(request, name, product):
    """Looks up and returns a build by name

    :param str name: name of the build.
    :param product: product_id of the product in the Database
    :type product: int or str
    :return: matching :class:`TestBuild` object hash or error if not found.
    :rtype: dict

    Example::

        # Get with product ID
        Build.check_build('2008-02-25', 1)
        # Get with product name
        Build.check_build('2008-02-25', 'Product A')
    """
    p = pre_check_product(values=product)
    tb = TestBuild.objects.get(name=name, product=p)
    return tb.serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("management.add_testbuild", raise_exception=True)
def create(request, values):
    """Creates a new build object and stores it in the database

    :param dict values: a mapping containing following items to create a
        :class:`TestBuild`

        * product: (int or str) the product ID or name the new TestBuild should belong to.
        * name: (str) the build name.
        * description: (str) optional description.
        * is_active: (bool) optional. To indicate whether new build is active. Defaults to ``True``.

    :return: a mapping serialized from newly created :class:`TestBuild`.
    :rtype: dict

    Example::

        # Create build by product ID and set the build active.
        Build.create({'product': 234, 'name': 'tcms_testing', 'description': 'None', 'is_active': 1})
        # Create build by product name and set the build to inactive.
        Build.create({'product': 'TCMS', 'name': 'tcms_testing 2', 'description': 'None', 'is_active': 0})
    """
    if not values.get("product") or not values.get("name"):
        raise ValueError("Product and name are both required.")

    p = pre_check_product(values)

    return TestBuild.objects.create(
        product=p,
        name=values["name"],
        description=values.get("description"),
        is_active=parse_bool_value(values.get("is_active", True)),
    ).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get(request, build_id):
    """Used to load an existing build from the database.

    :param int build_id: the build ID.
    :return: A blessed Build object hash
    :rtype: list

    Example::

        Build.get(1234)
    """
    return TestBuild.objects.get(build_id=build_id).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_runs(request, build_id):
    """Returns the list of runs that this Build is used in.

    :param int build_id: build ID.
    :return: list of test runs.
    :rtype: list

    Example::

        Build.get_runs(1234)
    """
    from tcms.testruns.models import TestRun

    tb = TestBuild.objects.get(build_id=build_id)
    query = {"build": tb}

    return TestRun.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_caseruns(request, build_id):
    """Returns the list of case runs that this Build is used in.

    :param int build_id: build ID.
    :return: list of mappings of found case runs.

    Example::

        Build.get_caseruns(1234)
    """
    from tcms.testruns.models import TestCaseRun

    tb = TestBuild.objects.get(build_id=build_id)
    query = {"build": tb}

    return TestCaseRun.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_id_by_name(request, name, product):
    """
    DEPRECATED - CONSIDERED HARMFUL Use Build.check_build instead
    """
    return check_build(request, name, product)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_name_by_id(request, build_id):
    """Lookup name by ID

    .. deprecated:: x.x
       Use ``Build.get`` instead.
    """
    return get(request, build_id)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("management.change_testbuild", raise_exception=True)
def update(request, build_id, values):
    """
    Description: Updates the fields of the selected build or builds.

    :param int build_id: the build ID.
    :param dict values: a mapping containing build information to update.

        * product: (int or str) optional new product ID or name.
        * name: (str) optional new build name.
        * description: (str) optional new description.
        * is_active: (bool) set active or not optionally.

    :return: a mapping serialized from the updated :class:`TestBuild` object.
    :rtype: dict

    Example::

        # Update name to 'foo' for build id 702
        Build.update(702, {'name': 'foo'})
        # Update status to inactive for build id 702
        Build.update(702, {'is_active': 0})
    """
    tb = TestBuild.objects.get(build_id=build_id)

    if not values:
        return tb.serialize()

    def _update_value(obj, name, value):
        setattr(obj, name, value)
        update_fields.append(name)

    update_fields = list()
    if values.get("product"):
        _update_value(tb, "product", pre_check_product(values))
    if values.get("name"):
        _update_value(tb, "name", values["name"])
    if values.get("description"):
        _update_value(tb, "description", values["description"])
    if values.get("is_active") is not None:
        _update_value(tb, "is_active", parse_bool_value(values.get("is_active", True)))

    tb.save(update_fields=update_fields)

    return tb.serialize()

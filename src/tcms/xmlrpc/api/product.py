# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User

from tcms.management.models import Product
from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.utils import parse_bool_value, pre_check_product

__all__ = (
    "check_category",
    "check_component",
    "check_product",
    "filter",
    "filter_categories",
    "filter_components",
    "filter_versions",
    "get",
    "get_builds",
    "get_cases",
    "get_categories",
    "get_category",
    "add_component",
    "get_component",
    "update_component",
    "get_components",
    "get_environments",
    "get_milestones",
    "get_plans",
    "get_runs",
    "get_tag",
    "add_version",
    "get_versions",
    "lookup_name_by_id",
    "lookup_id_by_name",
)

__xmlrpc_namespace__ = "Product"


@log_call(namespace=__xmlrpc_namespace__)
def check_category(request, name, product):
    """Looks up and returns a category by name.

    :param str name: name of the category.
    :param product: product ID or name.
    :type product: int or str
    :return: a mapping representing the category.
    :rtype: dict

    Example::

        # Get with product ID
        Product.check_category('Feature', 1)
        # Get with product name
        Product.check_category('Feature', 'product name')
    """
    from tcms.testcases.models import TestCaseCategory

    p = pre_check_product(values=product)
    return TestCaseCategory.objects.get(name=name, product=p).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def check_component(request, name, product):
    """Looks up and returns a component by name.

    :param str name: name of the category.
    :param product: product ID or name.
    :return: a mapping representing a :class:`Component`
    :rtype: dict

    Example::

        # Get with product ID
        Product.check_component('acpi', 1)
        # Get with product name
        Product.check_component('acpi', 'Product A')
    """
    from tcms.management.models import Component

    p = pre_check_product(values=product)
    return Component.objects.get(name=name, product=p).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def check_product(request, name):
    """Looks up and returns a validated product.

    :param name: product ID or name.
    :type name: int or str
    :return: a mapping representing the :class:`Product`.
    :rtype: dict

    Example::

        # Get with product ID
        Product.check_product(1)
        # Get with product name
        Product.check_product('Product A')
    """
    p = pre_check_product(values=name)
    return p.serialize()


@log_call(namespace=__xmlrpc_namespace__)
def filter(request, query):
    """Performs a search and returns the resulting list of products.

    :param dict query: a mapping containing following criteria.

        * id: (int) product id.
        * name: (str) product name.
        * classification: ForeignKey: :class:`Classification`.
        * description: (str) description.

    :return: a mapping representing a :class:`Product`.
    :rtype: dict

    Example::

        # Get all of product named 'product name'
        Product.filter({'name': 'product name'})
    """
    return Product.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def filter_categories(request, query):
    """Performs a search and returns the resulting list of categories.

    :param dict query: a mapping containing following criteria.

        * id: (int) category ID.
        * name: (str) category name.
        * product: ForeignKey: :class:`Product`.
        * description: (str) category description.

    :return: a mapping representing found category.
    :rtype: dict

    Example::

        # Get all of categories named like 'libvirt'
        Product.filter_categories({'name__icontains': 'regression'})
        # Get all of categories named in product 'product name'
        Product.filter_categories({'product__name': 'product name'})
    """
    from tcms.testcases.models import TestCaseCategory

    return TestCaseCategory.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def filter_components(request, query):
    """Performs a search and returns the resulting list of components.

    :param dict query: a mapping containing following criteria.

        * id: (int) product ID.
        * name: (str) component name.
        * product: ForeignKey: :class:`Product`.
        * initial_owner: ForeignKey: ``Auth.User``.
        * initial_qa_contact: ForeignKey: ``Auth.User``.
        * description str: component description.

    :return: a mapping of found :class:`Component`.
    :rtype: dict

    Example::

        # Get all of components named like 'libvirt'
        Product.filter_components({'name__icontains': 'libvirt'})
        # Get all of components named in product 'product name'
        Product.filter_components({'product__name': 'product name'})
    """
    from tcms.management.models import Component

    return Component.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def filter_versions(request, query):
    """Performs a search and returns the resulting list of versions.

    :param dict query: a mapping containing following criteria.

        * id: (int) ID of product
        * value: (str) version value.
        * product: ForeignKey: :class:`Product`.

    :return: a list of mappings of :class:`Version`.
    :rtype: list

    Example::

        # Get all of versions named like '2.4.0-SNAPSHOT'
        Product.filter_versions({'value__icontains': '2.4.0-SNAPSHOT'})
        # Get all of filter_versions named in product 'product name'
        Product.filter_versions({'product__name': 'product name'})
    """
    from tcms.management.models import Version

    return Version.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get(request, id):
    """Used to load an existing product from the database.

    :param int id: product ID.
    :return: a mapping representing found product.
    :rtype: :class:`Product`.

    Example::

        Product.get(61)
    """
    return Product.objects.get(id=int(id)).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_builds(request, product, is_active=True):
    """Get the list of builds associated with this product.

    :param product: product ID or name.
    :type product: int or str
    :param bool is_active: if ``True``, only return active builds. Otherwise,
        inactive builds will be returned.
    :return: a list of mappings of :class:`TestBuild`.
    :rtype: list

    Example::

        # Get with product id including all builds
        Product.get_builds(1)
        # Get with product name excluding all inactive builds
        Product.get_builds('product name', 0)
    """
    from tcms.management.models import TestBuild

    p = pre_check_product(values=product)
    query = {"product": p, "is_active": parse_bool_value(is_active)}
    return TestBuild.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_cases(request, product):
    """Get the list of cases associated with this product.

    :param product: product ID or name.
    :type product: int or str
    :return: a list of mappings of :class:`TestCase`.

    Example::

        # Get with product id
        Product.get_cases(61)
        # Get with product name
        Product.get_cases('product name')
    """
    from tcms.testcases.models import TestCase

    p = pre_check_product(values=product)
    query = {"category__product": p}
    return TestCase.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_categories(request, product):
    """Get the list of categories associated with this product.

    :param product: product ID or name.
    :type product: int or str
    :return: a list of mappings of :class:`TestCaseCategory`.
    :rtype: list

    Example:

        # Get with product id
        Product.get_categories(61)
        # Get with product name
        Product.get_categories('product name')
    """
    from tcms.testcases.models import TestCaseCategory

    p = pre_check_product(values=product)
    query = {"product": p}
    return TestCaseCategory.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_category(request, id):
    """Get the category matching the given id.

    :param int id: category ID.
    :return: a mapping representing found :class:`TestCaseCategory`.
    :rtype: dict

    Example::

        Product.get_category(11)
    """
    from tcms.testcases.models import TestCaseCategory

    return TestCaseCategory.objects.get(id=int(id)).serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("management.add_component", raise_exception=True)
def add_component(request, product, name, initial_owner_id=None, initial_qa_contact_id=None):
    """Add component to selected product.

    :param product: product ID or name.
    :type product: int or str
    :param str name: Component name
    :param int initial_owner_id: optional initial owner ID. Defaults to current
        logged in user.
    :param int initial_qa_contact_id: optional initial QA contact ID. Defaults
        to current logged in user.
    :return: a mapping of new :class:`Component`.
    :rtype: dict

    Example::

        Product.add_component(71, 'JPBMM')
    """
    from tcms.management.models import Component

    product = pre_check_product(values=product)

    if User.objects.filter(pk=initial_owner_id).exists():
        _initial_owner_id = initial_owner_id
    else:
        _initial_owner_id = request.user.pk

    if User.objects.filter(pk=initial_qa_contact_id).exists():
        _initial_qa_contact_id = initial_qa_contact_id
    else:
        _initial_qa_contact_id = request.user.pk

    return Component.objects.create(
        name=name,
        product=product,
        initial_owner_id=_initial_owner_id,
        initial_qa_contact_id=_initial_qa_contact_id,
    ).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_component(request, id):
    """Get the component matching the given id.

    :param int id: component ID.
    :return: a mapping representing found :class:`Component`.
    :rtype: dict

    Example::

        Product.get_component(11)
    """
    from tcms.management.models import Component

    return Component.objects.get(id=int(id)).serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("management.change_component", raise_exception=True)
def update_component(request, component_id, values):
    """Update component to selected product.

    :param int component_id: component ID.
    :param dict values: a mapping containing these new data.

        * name: (str) optional.
        * initial_owner_id: (int) optional.
        * initial_qa_contact_id: (int) optional.

    :return: a mapping representing updated :class:`Component`.
    :rtype: dict

    Example::

        Product.update_component(1, {'name': 'NewName'})
    """
    from tcms.management.models import Component

    if not isinstance(values, dict) or "name" not in values:
        raise ValueError(f"Component name is not in values {values}.")

    name = values["name"]
    if not isinstance(name, str) or len(name) == 0:
        raise ValueError(f"Component name {name} is not a string value.")

    component = Component.objects.get(pk=int(component_id))
    component.name = name
    if (
        values.get("initial_owner_id")
        and User.objects.filter(pk=values["initial_owner_id"]).exists()
    ):
        component.initial_owner_id = values["initial_owner_id"]
    if (
        values.get("initial_qa_contact_id")
        and User.objects.filter(pk=values["initial_qa_contact_id"]).exists()
    ):
        component.initial_qa_contact_id = values["initial_qa_contact_id"]
    component.save()
    return component.serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_components(request, product):
    """Get the list of components associated with this product.

    :param product: product ID or name.
    :type product: int or str
    :return: a list of mappings of :class:`Component`.
    :rtype: list

    Example::

        # Get with product id
        Product.get_components(61)
        # Get with product name
        Product.get_components('product name')
    """
    from tcms.management.models import Component

    p = pre_check_product(values=product)
    query = {"product": p}
    return Component.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_environments(request, product):
    """FIXME: NOT IMPLEMENTED"""
    raise NotImplementedError("Not implemented RPC method")


@log_call(namespace=__xmlrpc_namespace__)
def get_milestones(request, product):
    """FIXME: NOT IMPLEMENTED"""
    raise NotImplementedError("Not implemented RPC method")


@log_call(namespace=__xmlrpc_namespace__)
def get_plans(request, product):
    """Get the list of plans associated with this product.

    :param product: product ID or name.
    :type product: int or str
    :return: a list of mappings of :class:`TestPlan`.
    :rtype: list

    Example::

        # Get with product id
        Product.get_plans(61)
        # Get with product name
        Product.get_plans('product name')
    """
    from tcms.testplans.models import TestPlan

    p = pre_check_product(values=product)
    query = {"product": p}
    return TestPlan.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_runs(request, product):
    """Get the list of runs associated with this product.

    :params product: product ID or name.
    :type product: int or str
    :return: a list of mappings of test runs.
    :rtype: list

    Example::

        # Get with product id
        Product.get_runs(1)
        # Get with product name
        Product.get_runs('product name')
    """
    from tcms.testruns.models import TestRun

    p = pre_check_product(values=product)
    query = {"build__product": p}
    return TestRun.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_tag(request, id):
    """Get the list of tags.

    :param int id: tag ID.
    :return: a mapping representing found :class:`TestTag`.
    :rtype: dict

    Example::

        Product.get_tag(1)
    """
    from tcms.management.models import TestTag

    return TestTag.objects.get(pk=int(id)).serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("management.add_version", raise_exception=True)
def add_version(request, values):
    """Add version to specified product.

    :param dict values: a mapping containing these data

        * product: (int or str) product ID or name.
        * value: (str) the version value.

    :return: a mapping representing newly added :class:`Version`.
    :raise ValueError: if fail to add version.

    Example::

        # Add version for specified product:
        Product.add_version({'value': 'devel', 'product': 1})
        {'product': 'Test Product', 'id': '1', 'value': 'devel', 'product_id': 1}
        # Run it again:
        Product.add_version({'value': 'devel', 'product': 1})
        [['__all__', 'Version with this Product and Value already exists.']]
    """
    from tcms.core import forms
    from tcms.management.forms import VersionForm

    product = pre_check_product(values)
    form_values = values.copy()
    form_values["product"] = product.pk

    form = VersionForm(form_values)
    if form.is_valid():
        version = form.save()
        return version.serialize()
    else:
        raise ValueError(forms.errors_to_list(form))


@log_call(namespace=__xmlrpc_namespace__)
def get_versions(request, product):
    """Get the list of versions associated with this product.

    :param product: product ID or name.
    :type product: int or str
    :return: a list of mappings of versions.
    :rtype: list

    Example::

        # Get with product id
        Product.get_versions(1)
        # Get with product name
        Product.get_versions('product name')
    """
    from tcms.management.models import Version

    p = pre_check_product(values=product)
    query = {"product": p}
    return Version.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_name_by_id(request, id):
    """DEPRECATED Use Product.get instead"""
    return get(request, id)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_id_by_name(request, name):
    """DEPRECATED - CONSIDERED HARMFUL Use Product.check_product instead"""
    return check_product(request, name)

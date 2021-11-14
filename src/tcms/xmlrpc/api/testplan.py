# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ObjectDoesNotExist

from tcms.management.models import Component, Product, TestTag
from tcms.testplans.importer import clean_xml_file
from tcms.testplans.models import TCMSEnvPlanMap, TestPlan, TestPlanType
from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.utils import deprecate_critetion_attachment, distinct_count, pre_process_ids

__all__ = (
    "add_tag",
    "add_component",
    "check_plan_type",
    "create",
    "filter",
    "filter_count",
    "get",
    "get_change_history",
    "get_env_groups",
    "get_plan_type",
    "get_product",
    "get_tags",
    "get_components",
    "get_test_cases",
    "get_all_cases_tags",
    "get_test_runs",
    "get_text",
    "lookup_type_id_by_name",
    "lookup_type_name_by_id",
    "remove_tag",
    "remove_component",
    "store_text",
    "update",
    "import_case_via_XML",
)

__xmlrpc_namespace__ = "TestPlan"


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testplans.add_testplantag", raise_exception=True)
def add_tag(request, plan_ids, tags):
    """Add one or more tags to the selected test plans.

    :param plan_ids: give one or more plan IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a plan ID.
    :type plan_ids: int, str or list
    :param tags: a tag name or list of tag names to be added.
    :type tags: str or list[str]
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.

    Example::

        # Add tag 'foobar' to plan 1
        TestPlan.add_tag(1, 'foobar')
        # Add tag list ['foo', 'bar'] to plan list [1, 2]
        TestPlan.add_tag([1, 2], ['foo', 'bar'])
        # Add tag list ['foo', 'bar'] to plan list [1, 2] with String
        TestPlan.add_tag('1, 2', 'foo, bar')
    """
    # FIXME: this could be optimized to reduce possible huge number of SQLs

    tps = TestPlan.objects.filter(plan_id__in=pre_process_ids(value=plan_ids))
    tags = TestTag.string_to_list(tags)

    for tag in tags:
        t, c = TestTag.objects.get_or_create(name=tag)
        for tp in tps.iterator():
            tp.add_tag(tag=t)

    return


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testplans.add_testplancomponent", raise_exception=True)
def add_component(request, plan_ids, component_ids):
    """Adds one or more components to the selected test plan.

    :param plan_ids: give one or more plan IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a plan ID.
    :type plan_ids: int, str or list
    :param component_ids: give one or more component IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a component ID.
    :type component_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.

    Example::

        # Add component id 54321 to plan 1234
        TestPlan.add_component(1234, 54321)
        # Add component ids list [1234, 5678] to plan list [56789, 12345]
        TestPlan.add_component([56789, 12345], [1234, 5678])
        # Add component ids list '1234, 5678' to plan list '56789, 12345' with String
        TestPlan.add_component('56789, 12345', '1234, 5678')
    """
    # FIXME: optimize this method to reduce possible huge number of SQLs

    tps = TestPlan.objects.filter(plan_id__in=pre_process_ids(value=plan_ids))
    cs = Component.objects.filter(id__in=pre_process_ids(value=component_ids))

    for tp in tps.iterator():
        for c in cs.iterator():
            tp.add_component(c)

    return


@log_call(namespace=__xmlrpc_namespace__)
def check_plan_type(request, name):
    """Get a plan type by name

    :param str name: the plan type.
    :return: a mapping of found :class:`TestPlanType`.
    :rtype: dict

    Example::

        TestPlan.check_plan_type('regression')
    """
    return TestPlanType.objects.get(name=name).serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testplans.add_testplan", raise_exception=True)
def create(request, values):
    """Creates a new Test Plan object and stores it in the database.

    :param dict values: a mapping containing these plan data:

        * product: (int) **Required** ID of product
        * name: (str) **Required**
        * type: (int) **Required** ID of plan type
        * product_version: (int) **Required** version ID.
        * default_product_version: (int) optional version ID.
        * text: (str) **Required** Plan documents, HTML acceptable.
        * parent: (int) optional Parent plan ID
        * is_active: bool optional 0: Archived 1: Active (Default 0)

    :return: a mapping of newly created :class:`TestPlan`.
    :rtype: dict

    Example::

        # Minimal test case parameters
        values = {
            'product': 1,
            'name': 'Testplan foobar',
            'type': 1,
            'parent_id': 2,
            'default_product_version': 1,
            'text':'Testing TCMS',
        }
        TestPlan.create(values)

    .. deprecated: x.y
       ``default_product_version`` is deprecated and will be removed.
    """
    from tcms.core import forms
    from tcms.xmlrpc.forms import NewPlanForm

    if values.get("default_product_version"):
        values["product_version"] = values.pop("default_product_version")

    if not values.get("product"):
        raise ValueError("Value of product is required")

    form = NewPlanForm(values)
    form.populate(product_id=values["product"])

    if form.is_valid():
        tp = TestPlan.objects.create(
            product=form.cleaned_data["product"],
            name=form.cleaned_data["name"],
            type=form.cleaned_data["type"],
            author=request.user,
            product_version=form.cleaned_data["product_version"],
            parent=form.cleaned_data["parent"],
            is_active=form.cleaned_data["is_active"],
        )

        tp.add_text(
            author=request.user,
            plan_text=values["text"],
        )

        return tp.serialize()
    else:
        raise ValueError(forms.errors_to_list(form))


@log_call(namespace=__xmlrpc_namespace__)
def filter(request, values={}):
    """Performs a search and returns the resulting list of test plans.

    :param dict values: a mapping containing these criteira.

        * author: ForeignKey: Auth.User
        * attachments: ForeignKey: Attachment
        * case: ForeignKey: TestCase
        * create_date: DateTime
        * env_group: ForeignKey: Environment Group
        * name: (str)
        * plan_id: (int)
        * product: ForeignKey: Product
        * product_version: ForeignKey: Version
        * tag: ForeignKey: TestTag
        * text: ForeignKey: Test Plan Text
        * type: ForeignKey: Test Plan Type

    :return: list of mappings of found :class:`TestPlan`.
    :rtype: list[dict]

    Example::

        # Get all of plans contain 'TCMS' in name
        TestPlan.filter({'name__icontain': 'TCMS'})
        # Get all of plans create by xkuang
        TestPlan.filter({'author__username': 'xkuang'})
        # Get all of plans the author name starts with x
        TestPlan.filter({'author__username__startswith': 'x'})
        # Get plans contain the case ID 1, 2, 3
        TestPlan.filter({'case__case_id__in': [1, 2, 3]})
    """
    deprecate_critetion_attachment(values)
    return TestPlan.to_xmlrpc(values)


@log_call(namespace=__xmlrpc_namespace__)
def filter_count(request, values={}):
    """Performs a search and returns the resulting count of plans.

    :param dict values: a mapping containing criteria. See also
        :meth:`TestPlan.filter <tcms.xmlrpc.api.testplan.filter>`.
    :return: total matching plans.
    :rtype: int

    .. seealso:: See example of :meth:`TestPlan.filter <tcms.xmlrpc.api.testplan.filter>`.
    """
    return distinct_count(TestPlan, values)


@log_call(namespace=__xmlrpc_namespace__)
def get(request, plan_id):
    """Used to load an existing test plan from the database.

    :param int plan_id: plan ID.
    :return: a mapping of found :class:`TestPlan`.
    :rtype: dict

    Example::

        TestPlan.get(1)
    """
    tp = TestPlan.objects.get(plan_id=plan_id)
    response = tp.serialize()

    # This is for backward-compatibility. Actually, this is not a good way to
    # add this extra field. But, now that's it.
    response["default_product_version"] = response["product_version"]

    # get the xmlrpc tags
    tag_ids = tp.tag.values_list("id", flat=True)
    query = {"id__in": tag_ids}
    tags = TestTag.to_xmlrpc(query)
    # cut 'id' attribute off, only leave 'name' here
    tags_without_id = [tag["name"] for tag in tags]
    # replace tag_id list in the serialize return data
    response["tag"] = tags_without_id
    return response


@log_call(namespace=__xmlrpc_namespace__)
def get_change_history(request, plan_id):
    """Get the list of changes to the fields of this plan.

    :param int plan_id: plan ID.
    :return: a list of mappings of found history.

    .. warning::

       NOT IMPLEMENTED - History is different than before.
    """
    raise NotImplementedError("Not implemented RPC method")


@log_call(namespace=__xmlrpc_namespace__)
def get_env_groups(request, plan_id):
    """Get the list of env groups to the fields of this plan.

    :param int plan_id: plan ID.
    :return: list of mappings of found :class:`TCMSEnvGroup`.
    :rtype: list[dict]
    """
    from tcms.management.models import TCMSEnvGroup

    query = {"testplan__pk": plan_id}
    return TCMSEnvGroup.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_plan_type(request, id):
    """Get plan type

    :param int id: plan ID.
    :return: a mapping of found :class:`TestPlanType`.
    :rtype: dict

    Example::

        TestPlan.get_plan_type(1)
    """
    return TestPlanType.objects.get(id=id).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_product(request, plan_id):
    """Get the Product the plan is assiciated with.

    :param int plan_id: plan ID.
    :return: a mapping of found :class:`Product`.
    :rtype: dict

    Example::

        TestPlan.get_product(1)
    """
    products = Product.objects.filter(plan=plan_id)
    products = products.select_related("classification")
    products = products.defer("classification__description")
    if len(products) == 0:
        raise Product.DoesNotExist
    else:
        return products[0].serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_tags(request, plan_id):
    """Get the list of tags attached to this plan.

    :param int plan_id: plan ID.
    :return: list of mappings of found :class:`TestTag`.
    :rtype: list[dict]

    Example::

        TestPlan.get_tags(1)
    """
    tp = TestPlan.objects.get(plan_id=plan_id)

    tag_ids = tp.tag.values_list("id", flat=True)
    query = {"id__in": tag_ids}
    return TestTag.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_components(request, plan_id):
    """Get the list of components attached to this plan.

    :param int plan_id: plan ID.
    :return: list of mappings of found :class:`Component`.
    :rtype: list[dict]

    Example::

        TestPlan.get_components(1)
    """
    tp = TestPlan.objects.get(plan_id=plan_id)

    component_ids = tp.component.values_list("id", flat=True)
    query = {"id__in": component_ids}
    return Component.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_all_cases_tags(request, plan_id):
    """Get the list of tags attached to this plan's testcases.

    :param int plan_id: plan ID.
    :return: list of mappings of found :class:`TestTag`.
    :rtype: list[dict]

    Example::

        TestPlan.get_all_cases_tags(137)
    """
    tp = TestPlan.objects.get(plan_id=plan_id)

    tcs = tp.case.all()
    tag_ids = []
    for tc in tcs.iterator():
        tag_ids.extend(tc.tag.values_list("id", flat=True))
    tag_ids = list(set(tag_ids))
    query = {"id__in": tag_ids}
    return TestTag.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_test_cases(request, plan_id):
    """Get the list of cases that this plan is linked to.

    :param int plan_id: plan ID.
    :return: list of mappings of found :class:`TestCase`.
    :rtype: list[dict]

    Example::

        TestPlan.get_test_cases(1)
    """
    from tcms.testcases.models import TestCase
    from tcms.testplans.models import TestPlan
    from tcms.xmlrpc.serializer import XMLRPCSerializer

    tp = TestPlan.objects.get(pk=plan_id)
    tcs = TestCase.objects.filter(plan=tp).order_by("testcaseplan__sortkey")
    serialized_tcs = XMLRPCSerializer(tcs.iterator()).serialize_queryset()
    if serialized_tcs:
        for serialized_tc in serialized_tcs:
            case_id = serialized_tc.get("case_id", None)
            tc = tcs.get(pk=case_id)
            tcp = tc.testcaseplan_set.get(plan=tp)
            serialized_tc["sortkey"] = tcp.sortkey
    return serialized_tcs


@log_call(namespace=__xmlrpc_namespace__)
def get_test_runs(request, plan_id):
    """Get the list of runs in this plan.

    :param int plan_id: plan ID.
    :return: list of mappings of found :class:`TestRun`.
    :rtype: list[dict]

    Example::

        TestPlan.get_test_runs(1)
    """
    from tcms.testruns.models import TestRun

    query = {"plan": plan_id}
    return TestRun.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_text(request, plan_id, plan_text_version=None):
    """The plan document for a given test plan.

    :param int plan_id: plan ID.
    :param str text: the content to be added. Could contain HTML.
    :param int plan_text_version: optional text version. Defaults to the latest
        if omitted.
    :return: a mapping of text.
    :rtype: dict

    Example::

        # Get all latest case text
        TestPlan.get_text(1)
        # Get all case text with version 4
        TestPlan.get_text(1, 4)
    """
    tp = TestPlan.objects.get(plan_id=plan_id)
    test_plan_text = tp.get_text_with_version(plan_text_version=plan_text_version)
    if test_plan_text:
        return test_plan_text.serialize()
    else:
        return "No plan text with version '%s' found." % plan_text_version


@log_call(namespace=__xmlrpc_namespace__)
def lookup_type_id_by_name(request, name):
    """DEPRECATED - CONSIDERED HARMFUL Use TestPlan.check_plan_type instead"""
    return check_plan_type(request=request, name=name)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_type_name_by_id(request, id):
    """DEPRECATED - CONSIDERED HARMFUL Use TestPlan.get_plan_type instead"""
    return get_plan_type(request=request, id=id)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testplans.delete_testplantag", raise_exception=True)
def remove_tag(request, plan_ids, tags):
    """Remove a tag from a plan.

    :param plan_ids: give one or more plan IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a plan ID.
    :type plan_ids: int, str or list
    :param tags: a tag name or a list of tag names to be removed.
    :type tags: str or list[str]
    :return: Empty on success.

    Example::

        # Remove tag 'foo' from plan 1
        TestPlan.remove_tag(1, 'foo')
        # Remove tag 'foo' and 'bar' from plan list [1, 2]
        TestPlan.remove_tag([1, 2], ['foo', 'bar'])
        # Remove tag 'foo' and 'bar' from plan list '1, 2' with String
        TestPlan.remove_tag('1, 2', 'foo, bar')
    """
    from tcms.management.models import TestTag

    tps = TestPlan.objects.filter(plan_id__in=pre_process_ids(value=plan_ids))
    tgs = TestTag.objects.filter(name__in=TestTag.string_to_list(tags))

    for tp in tps.iterator():
        for tg in tgs.iterator():
            try:
                tp.remove_tag(tag=tg)
            except ObjectDoesNotExist:
                pass

    return


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testplans.delete_testplancomponent", raise_exception=True)
def remove_component(request, plan_ids, component_ids):
    """Removes selected component from the selected test plan.

    :param plan_ids: give one or more plan IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a plan ID.
    :type plan_ids: int, str or list
    :param component_ids: give one or more component IDs. It could be an
        integer, a string containing comma separated IDs, or a list of int each
        of them is a component ID.
    :type component_ids: int, str or list
    :return: Empty on success.

    Example::

        # Remove component id 2 from plan 1
        TestPlan.remove_component(1, 2)
        # Remove component ids list [3, 4] from plan list [1, 2]
        TestPlan.remove_component([1, 2], [3, 4])
        # Remove component ids list '3, 4' from plan list '1, 2' with String
        TestPlan.remove_component('1, 2', '3, 4')
    """
    tps = TestPlan.objects.filter(plan_id__in=pre_process_ids(value=plan_ids))
    cs = Component.objects.filter(id__in=pre_process_ids(value=component_ids))

    for tp in tps.iterator():
        for c in cs.iterator():
            try:
                tp.remove_component(component=c)
            except ObjectDoesNotExist:
                pass

    return


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testplans.add_testplantext", raise_exception=True)
def store_text(request, plan_id, text, author=None):
    """Update the document field of a plan.

    :param int plan_id: plan ID.
    :param str text: the content to be added. Could contain HTML.
    :param int author: optional user ID of author. Defaults to ``request.user``
        if omitted.
    :return: a mapping of newly stored text.
    :rtype: dict

    Example::

        TestPlan.store_text(1, 'Plan Text', 2)
    """
    from django.contrib.auth.models import User

    tp = TestPlan.objects.get(plan_id=plan_id)

    if author:
        author = User.objects.get(id=author)
    else:
        author = request.user

    return tp.add_text(
        author=author,
        plan_text=text and text.strip(),
    ).serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testplans.change_testplan", raise_exception=True)
def update(request, plan_ids, values):
    """Updates the fields of the selected test plan.

    :param plan_ids: give one or more plan IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a plan ID.
    :type plan_ids: int, str or list
    :param dict values: a mapping containing these plan data to update

        * product: (int) ID of product
        * name: (str)
        * type: (int) ID of plan type
        * product_version: (int) ID of version
        * default_product_version: (int) alternative version ID.
        * owner: (str)/(int) user_name/user_id
        * parent: (int) Parent plan ID
        * is_active: bool True/False
        * env_group: (int) New environment group ID

    :return: a mapping of updated :class:`TestPlan`.
    :rtype: dict

    Example::

        # Update product to 7 for plan 1 and 2
        TestPlan.update([1, 2], {'product': 7})

    .. deprecated:: x.y
       ``default_product_version`` is deprecated and will be removed.
    """
    from tcms.core import forms
    from tcms.xmlrpc.forms import EditPlanForm

    if values.get("default_product_version"):
        values["product_version"] = values.pop("default_product_version")

    form = EditPlanForm(values)

    if values.get("product_version") and not values.get("product"):
        raise ValueError('Field "product" is required by product_version')

    if values.get("product") and not values.get("product_version"):
        raise ValueError('Field "product_version" is required by product')

    if values.get("product_version") and values.get("product"):
        form.populate(product_id=values["product"])

    plan_ids = pre_process_ids(value=plan_ids)
    tps = TestPlan.objects.filter(pk__in=plan_ids)

    if form.is_valid():
        _values = dict()
        if form.cleaned_data["name"]:
            _values["name"] = form.cleaned_data["name"]

        if form.cleaned_data["type"]:
            _values["type"] = form.cleaned_data["type"]

        if form.cleaned_data["product"]:
            _values["product"] = form.cleaned_data["product"]

        if form.cleaned_data["product_version"]:
            _values["product_version"] = form.cleaned_data["product_version"]

        if form.cleaned_data["owner"]:
            _values["owner"] = form.cleaned_data["owner"]

        if form.cleaned_data["parent"]:
            _values["parent"] = form.cleaned_data["parent"]

        if not (values.get("is_active") is None):
            _values["is_active"] = form.cleaned_data["is_active"]

        tps.update(**_values)

        # requested to update environment group for selected test plans
        if form.cleaned_data["env_group"]:
            # prepare the list of new objects to be inserted into DB
            new_objects = [
                TCMSEnvPlanMap(plan_id=plan_pk, group_id=form.cleaned_data["env_group"].pk)
                for plan_pk in plan_ids
            ]

            # first delete the old values (b/c many-to-many I presume ?)
            TCMSEnvPlanMap.objects.filter(plan__in=plan_ids).delete()
            # then create all objects with 1 INSERT
            TCMSEnvPlanMap.objects.bulk_create(new_objects)
    else:
        raise ValueError(forms.errors_to_list(form))

    query = {"pk__in": tps.values_list("pk", flat=True)}
    return TestPlan.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def import_case_via_XML(request, plan_id, xml_content):
    """Add cases to plan via XML file

    :param int plan_id: plan ID.
    :param str xml_content: content of XML document containing cases.
    :return: a simple string to indicate a successful import.

    Example::

        fb = open('tcms.xml', 'rb')
        TestPlan.import_case_via_XML(1, fb.read())
    """
    tp = TestPlan.objects.get(pk=plan_id)
    new_case_from_xml = list(clean_xml_file(xml_content))
    tp.import_cases(new_case_from_xml)
    return "Success update {} cases".format(len(new_case_from_xml))

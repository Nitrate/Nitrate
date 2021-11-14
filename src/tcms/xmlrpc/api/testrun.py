# -*- coding: utf-8 -*-

import logging
from operator import methodcaller
from typing import List

from django.core.exceptions import ObjectDoesNotExist
from kobo.django.xmlrpc.decorators import user_passes_test

from tcms.issuetracker.models import Issue
from tcms.management.models import TCMSEnvValue, TestTag
from tcms.testcases.models import TestCase
from tcms.testruns.models import TestCaseRun, TestRun
from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.utils import distinct_count, pre_process_estimated_time, pre_process_ids

__all__ = (
    "add_cases",
    "add_tag",
    "create",
    "env_value",
    "filter",
    "filter_count",
    "get",
    "get_issues",
    "get_change_history",
    "get_completion_report",
    "get_env_values",
    "get_tags",
    "get_test_case_runs",
    "get_test_cases",
    "get_test_plan",
    "link_env_value",
    "remove_cases",
    "remove_tag",
    "unlink_env_value",
    "update",
)

__xmlrpc_namespace__ = "TestRun"

logger = logging.getLogger(__name__)


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.add_testcaserun"))
def add_cases(request, run_ids, case_ids):
    """Add one or more cases to the selected test runs.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Add case id 10 to run 1
        TestRun.add_cases(1, 10)
        # Add case ids list [10, 20] to run list [1, 2]
        TestRun.add_cases([1, 2], [10, 20])
        # Add case ids list '10, 20' to run list '1, 2' with String
        TestRun.add_cases('1, 2', '10, 20')
    """
    trs = TestRun.objects.filter(run_id__in=pre_process_ids(run_ids))
    tcs = TestCase.objects.filter(case_id__in=pre_process_ids(case_ids))

    for tr in trs.iterator():
        for tc in tcs.iterator():
            tr.add_case_run(case=tc)


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.delete_testcaserun"))
def remove_cases(request, run_ids, case_ids):
    """Remove one or more cases from the selected test runs.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Remove case 10 from run 1
        TestRun.remove_cases(1, 10)
        # Remove case ids list [10, 20] from run list [1, 2]
        TestRun.remove_cases([1, 2], [10, 20])
        # Remove case ids list '10, 20' from run list '1, 2' with String
        TestRun.remove_cases('1, 2', '10, 20')
    """
    trs = TestRun.objects.filter(run_id__in=pre_process_ids(run_ids))
    for tr in trs.iterator():
        crs = TestCaseRun.objects.filter(run=tr, case__in=pre_process_ids(case_ids))
        crs.delete()


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.add_testruntag"))
def add_tag(request, run_ids, tags):
    """Add one or more tags to the selected test runs.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :param tags: tag name or a list of tag names to remove.
    :type tags: str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Add tag 'foobar' to run 1
        TestPlan.add_tag(1, 'foobar')
        # Add tag list ['foo', 'bar'] to run list [1, 2]
        TestPlan.add_tag([1, 2], ['foo', 'bar'])
        # Add tag list ['foo', 'bar'] to run list [1, 2] with String
        TestPlan.add_tag('1, 2', 'foo, bar')
    """
    trs = TestRun.objects.filter(pk__in=pre_process_ids(value=run_ids))
    tags: List[str] = TestTag.string_to_list(tags)

    for tag in tags:
        t, _ = TestTag.objects.get_or_create(name=tag)
        tr: TestRun
        for tr in trs.iterator():
            tr.add_tag(tag=t)


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.add_testrun"))
def create(request, values):
    """Creates a new Test Run object and stores it in the database.

    :param dict values: a mapping containing these data to create a test run.

        * plan: (int) **Required** ID of test plan
        * build: (int)/(str) **Required** ID of Build
        * manager: (int) **Required** ID of run manager
        * summary: (str) **Required**
        * product: (int) **Required** ID of product
        * product_version: (int) **Required** ID of product version
        * default_tester: (int) optional ID of run default tester
        * plan_text_version: (int) optional
        * estimated_time: (str) optional, could be in format ``2h30m30s``, which is recommended or ``HH:MM:SS``.
        * notes: (str) optional
        * status: (int) optional 0:RUNNING 1:STOPPED  (default 0)
        * case: list or (str) optional list of case ids to add to the run
        * tag: list or (str) optional list of tag to add to the run

    :return: a mapping representing newly created :class:`TestRun`.
    :rtype: dict

    .. versionchanged:: 4.5
       Argument ``errata_id`` is removed.

    Example::

        values = {
            'build': 2,
            'manager': 1,
            'plan': 1,
            'product': 1,
            'product_version': 2,
            'summary': 'Testing XML-RPC for TCMS',
        }
        TestRun.create(values)
    """
    from datetime import datetime

    from tcms.core import forms
    from tcms.testruns.forms import XMLRPCNewRunForm

    if not values.get("product"):
        raise ValueError("Value of product is required")
    # TODO: XMLRPC only accept HH:MM:SS rather than DdHhMm

    if values.get("estimated_time"):
        values["estimated_time"] = pre_process_estimated_time(values.get("estimated_time"))

    if values.get("case"):
        values["case"] = pre_process_ids(value=values["case"])

    form = XMLRPCNewRunForm(values)
    form.populate(product_id=values["product"])

    if form.is_valid():
        tr = TestRun.objects.create(
            product_version=form.cleaned_data["product_version"],
            plan_text_version=form.cleaned_data["plan_text_version"],
            stop_date=form.cleaned_data["status"] and datetime.now() or None,
            summary=form.cleaned_data["summary"],
            notes=form.cleaned_data["notes"],
            estimated_time=form.cleaned_data["estimated_time"],
            plan=form.cleaned_data["plan"],
            build=form.cleaned_data["build"],
            manager=form.cleaned_data["manager"],
            default_tester=form.cleaned_data["default_tester"],
        )

        if form.cleaned_data["case"]:
            for c in form.cleaned_data["case"]:
                tr.add_case_run(case=c)
                del c

        if form.cleaned_data["tag"]:
            tags = form.cleaned_data["tag"]
            tags = [c.strip() for c in tags.split(",") if c]

            for tag in tags:
                t, c = TestTag.objects.get_or_create(name=tag)
                tr.add_tag(tag=t)
                del tag, t, c
    else:
        raise ValueError(forms.errors_to_list(form))

    return tr.serialize()


def __env_value_operation(request, action: str, run_ids, env_value_ids):
    trs = TestRun.objects.filter(pk__in=pre_process_ids(value=run_ids))
    evs = TCMSEnvValue.objects.filter(pk__in=pre_process_ids(value=env_value_ids))
    for tr in trs.iterator():
        for ev in evs.iterator():
            try:
                func = getattr(tr, action + "_env_value")
                func(env_value=ev)
            except ObjectDoesNotExist:
                logger.debug(
                    "User %s wants to remove property value %r from test run %r, "
                    "however this test run does not have that value.",
                    request.user,
                    ev,
                    tr,
                )


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.change_tcmsenvrunvaluemap"))
def env_value(request, action, run_ids, env_value_ids):
    """
    Add or remove env values to the given runs, function is same as
    link_env_value or unlink_env_value

    :param str action: what action to do, ``add`` or ``remove``.
    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :param env_value_ids: give one or more environment value IDs. It could be
        an integer, a string containing comma separated IDs, or a list of int
        each of them is a environment value ID.
    :type env_value_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Add env value 20 to run id 8
        TestRun.env_value('add', 8, 20)
    """
    __env_value_operation(request, action, run_ids, env_value_ids)


@log_call(namespace=__xmlrpc_namespace__)
def filter(request, values={}):
    """Performs a search and returns the resulting list of test runs.

    :param dict values: a mapping containing these criteria.

        * build: ForeignKey: TestBuild
        * cc: ForeignKey: Auth.User
        * env_value: ForeignKey: Environment Value
        * default_tester: ForeignKey: Auth.User
        * run_id: (int)
        * manager: ForeignKey: Auth.User
        * notes: (str)
        * plan: ForeignKey: TestPlan
        * summary: (str)
        * tag: ForeignKey: Tag
        * product_version: ForeignKey: Version

    :return: list of mappings of found :class:`TestRun`.
    :rtype: list

    Example::

        # Get all of runs contain 'TCMS' in summary
        TestRun.filter({'summary__icontain': 'TCMS'})
        # Get all of runs managed by xkuang
        TestRun.filter({'manager__username': 'xkuang'})
        # Get all of runs the manager name starts with x
        TestRun.filter({'manager__username__startswith': 'x'})
        # Get runs contain the case ID 1, 2, 3
        TestRun.filter({'case_run__case__case_id__in': [1, 2, 3]})
    """
    return TestRun.to_xmlrpc(values)


@log_call(namespace=__xmlrpc_namespace__)
def filter_count(request, values={}):
    """Performs a search and returns the resulting count of runs.

    :param dict values: a mapping containing criteria. See also
        :meth:`TestRun.filter <tcms.xmlrpc.api.testrun.filter>`.
    :return: total matching runs.
    :rtype: int

    .. seealso::
       See examples of :meth:`TestRun.filter <tcms.xmlrpc.api.testrun.filter>`.
    """
    return distinct_count(TestRun, values)


@log_call(namespace=__xmlrpc_namespace__)
def get(request, run_id):
    """Used to load an existing test run from the database.

    :param int run_id: test run ID.
    :return: a mapping representing found :class:`TestRun`.
    :rtype: dict

    Example::

        TestRun.get(1)
    """
    try:
        tr = TestRun.objects.get(run_id=run_id)
    except TestRun.DoesNotExist as error:
        return error
    response = tr.serialize()
    # get the xmlrpc tags
    tag_ids = tr.tag.values_list("id", flat=True)
    query = {"id__in": tag_ids}
    tags = TestTag.to_xmlrpc(query)
    # cut 'id' attribute off, only leave 'name' here
    tags_without_id = [tag["name"] for tag in tags]
    # replace tag_id list in the serialize return data
    response["tag"] = tags_without_id
    return response


@log_call(namespace=__xmlrpc_namespace__)
def get_issues(request, run_ids):
    """Get the list of issues attached to this run.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :return: a list of mappings of :class:`Issue <tcms.issuetracker.models.Issue>`.
    :rtype: list[dict]

    Example::

        # Get issues belonging to ID 12345
        TestRun.get_issues(1)
        # Get issues belonging to run ids list [1, 2]
        TestRun.get_issues([1, 2])
        # Get issues belonging to run ids list 1 and 2 with string
        TestRun.get_issues('1, 2')
    """
    query = {"case_run__run__in": pre_process_ids(run_ids)}
    return Issue.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_change_history(request, run_id):
    """Get the list of changes to the fields of this run.

    :param int run_id: run ID.
    :return: list of mapping with changed fields and their details.
    :rtype: list

    .. warning::
       NOT IMPLEMENTED - History is different than before.
    """
    raise NotImplementedError("Not implemented RPC method")  # pragma: no cover


@log_call(namespace=__xmlrpc_namespace__)
def get_completion_report(request, run_ids):
    """Get a report of the current status of the selected runs combined.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :return: A mapping containing counts and percentages of the combined totals
        of case-runs in the run. Counts only the most recently statused
        case-run for a given build and environment.
    :rtype: dict

    .. warning::
       NOT IMPLEMENTED
    """
    raise NotImplementedError("Not implemented RPC method")  # pragma: no cover


@log_call(namespace=__xmlrpc_namespace__)
def get_env_values(request, run_id):
    """Get the list of env values to this run.

    :param int run_id: run ID.
    :return: a list of mappings representing found :class:`TCMSEnvValue`.
    :rtype: List[dict]

    Example::

        TestRun.get_env_values(8)
    """
    from tcms.management.models import TCMSEnvValue

    # FIXME: return [] if run_id is None or ""

    query = {"testrun__pk": run_id}
    return TCMSEnvValue.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_tags(request, run_id):
    """Get the list of tags attached to this run.

    :param int run_id: run ID.
    :return: a mapping representing found :class:`TestTag`.
    :rtype: dict

    Example::

        TestRun.get_tags(1)
    """
    tr = TestRun.objects.get(run_id=run_id)

    tag_ids = tr.tag.values_list("id", flat=True)
    query = {"id__in": tag_ids}
    return TestTag.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_test_case_runs(request, run_id):
    """Get the list of cases that this run is linked to.

    :param int run_id: run ID.
    :return: a list of mappings of found :class:`TestCaseRun`.
    :rtype: list[dict]

    Example::

        # Get all of case runs
        TestRun.get_test_case_runs(1)
    """
    return TestCaseRun.to_xmlrpc({"run__run_id": run_id})


@log_call(namespace=__xmlrpc_namespace__)
def get_test_cases(request, run_id):
    """Get the list of cases that this run is linked to.

    :param int run_id: run ID.
    :return: a list of mappings of found :class:`TestCase`.
    :rtype: list[dict]

    Example::

        TestRun.get_test_cases(1)
    """
    tcs_serializer = TestCase.to_xmlrpc(query={"case_run__run_id": run_id})

    qs = TestCaseRun.objects.filter(run_id=run_id).values("case", "pk", "case_run_status__name")
    extra_info = {row["case"]: row for row in qs.iterator()}

    for case in tcs_serializer:
        info = extra_info[case["case_id"]]
        case["case_run_id"] = info["pk"]
        case["case_run_status"] = info["case_run_status__name"]

    return tcs_serializer


@log_call(namespace=__xmlrpc_namespace__)
def get_test_plan(request, run_id):
    """Get the plan that this run is associated with.

    :param int run_id: run ID.
    :return: a mapping of found :class:`TestPlan`.
    :rtype: dict

    Example::

        TestRun.get_test_plan(1)
    """
    return TestRun.objects.select_related("plan").get(run_id=run_id).plan.serialize()


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.delete_testruntag"))
def remove_tag(request, run_ids, tags):
    """Remove a tag from a run.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :param tags: tag name or a list of tag names to remove.
    :type tags: str or list
    :return: a list which is empty on success.
    :rtype: list

    Example::

        # Remove tag 'foo' from run 1
        TestRun.remove_tag(1, 'foo')
        # Remove tag 'foo' and 'bar' from run list [1, 2]
        TestRun.remove_tag([1, 2], ['foo', 'bar'])
        # Remove tag 'foo' and 'bar' from run list '1, 2' with String
        TestRun.remove_tag('1, 2', 'foo, bar')
    """
    trs = TestRun.objects.filter(run_id__in=pre_process_ids(value=run_ids))
    tgs = TestTag.objects.filter(name__in=TestTag.string_to_list(tags))

    tr: TestRun
    for tr in trs.iterator():
        for tg in tgs.iterator():
            tr.remove_tag(tag=tg)


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.change_testrun"))
def update(request, run_ids, values):
    """Updates the fields of the selected test run.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :param dict values: a mapping containing these data to update specified
        runs.

        * plan: (int) TestPlan.plan_id
        * product: (int) Product.id
        * build: (int) Build.id
        * manager: (int) Auth.User.id
        * default_tester: Intege Auth.User.id
        * summary: (str)
        * estimated_time: (TimeDelta) in format ``2h30m30s`` which is recommended or ``HH:MM:SS``.
        * product_version: (int)
        * plan_text_version: (int)
        * notes: (str)
        * status: (int) 0:RUNNING 1:FINISHED

    :return: list of mappings of the updated test runs.
    :rtype: list[dict]

    .. versionchanged:: 4.5
       Argument ``errata_id`` is removed.

    Example::

        # Update status to finished for run 1 and 2
        TestRun.update([1, 2], {'status': 1})
    """
    from datetime import datetime

    from tcms.core import forms
    from tcms.testruns.forms import XMLRPCUpdateRunForm

    if values.get("product_version") and not values.get("product"):
        raise ValueError('Field "product" is required by product_version')

    if values.get("estimated_time"):
        values["estimated_time"] = pre_process_estimated_time(values.get("estimated_time"))

    form = XMLRPCUpdateRunForm(values)
    if values.get("product_version"):
        form.populate(product_id=values["product"])

    if form.is_valid():
        trs = TestRun.objects.filter(pk__in=pre_process_ids(value=run_ids))
        _values = dict()
        if form.cleaned_data["plan"]:
            _values["plan"] = form.cleaned_data["plan"]

        if form.cleaned_data["build"]:
            _values["build"] = form.cleaned_data["build"]

        if form.cleaned_data["manager"]:
            _values["manager"] = form.cleaned_data["manager"]

        if "default_tester" in values:
            default_tester = form.cleaned_data["default_tester"]
            if values.get("default_tester") and default_tester:
                _values["default_tester"] = default_tester
            else:
                _values["default_tester"] = None

        if form.cleaned_data["summary"]:
            _values["summary"] = form.cleaned_data["summary"]

        if values.get("estimated_time") is not None:
            _values["estimated_time"] = form.cleaned_data["estimated_time"]

        if form.cleaned_data["product_version"]:
            _values["product_version"] = form.cleaned_data["product_version"]

        if "notes" in values:
            if values["notes"] in (None, ""):
                _values["notes"] = values["notes"]
            if form.cleaned_data["notes"]:
                _values["notes"] = form.cleaned_data["notes"]

        if form.cleaned_data["plan_text_version"]:
            _values["plan_text_version"] = form.cleaned_data["plan_text_version"]

        if isinstance(form.cleaned_data["status"], int):
            if form.cleaned_data["status"]:
                _values["stop_date"] = datetime.now()
            else:
                _values["stop_date"] = None

        trs.update(**_values)
    else:
        raise ValueError(forms.errors_to_list(form))

    query = {"pk__in": trs.values_list("pk", flat=True)}
    return TestRun.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.add_tcmsenvrunvaluemap"))
def link_env_value(request, run_ids, env_value_ids):
    """Link env values to the given runs.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :param env_value_ids: give one or more environment value IDs. It could be
        an integer, a string containing comma separated IDs, or a list of int
        each of them is a environment value ID.
    :type env_value_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Add env value 1 to run id 2
        TestRun.link_env_value(2, 1)
    """
    return __env_value_operation(request, "add", run_ids, env_value_ids)


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "testruns.delete_tcmsenvrunvaluemap"))
def unlink_env_value(request, run_ids, env_value_ids):
    """Unlink env values to the given runs.

    :param run_ids: give one or more run IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a run ID.
    :type run_ids: int, str or list
    :param env_value_ids: give one or more environment value IDs. It could be
        an integer, a string containing comma separated IDs, or a list of int
        each of them is a environment value ID.
    :type env_value_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Unlink env value 1 to run id 2
        TestRun.unlink_env_value(2, 1)
    """
    return __env_value_operation(request, "remove", run_ids, env_value_ids)

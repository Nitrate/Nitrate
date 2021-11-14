# -*- coding: utf-8 -*-

import itertools

from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.forms import EmailField

import tcms.comments.models
from tcms.core.utils import form_error_messages_to_list, timedelta2int
from tcms.issuetracker.models import Issue, IssueTracker
from tcms.management.models import TestTag
from tcms.testcases.forms import CaseIssueForm
from tcms.testcases.models import TestCase, TestCasePlan
from tcms.testplans.models import TestPlan
from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.utils import (
    deprecate_critetion_attachment,
    distinct_count,
    pre_process_estimated_time,
    pre_process_ids,
)

__all__ = (
    "add_comment",
    "add_component",
    "add_tag",
    "add_to_run",
    "attach_issue",
    "check_case_status",
    "check_priority",
    "calculate_average_estimated_time",
    "calculate_total_estimated_time",
    "create",
    "detach_issue",
    "filter",
    "filter_count",
    "get",
    "get_issue_tracker",
    "get_issues",
    "get_case_run_history",
    "get_case_status",
    "get_change_history",
    "get_components",
    "get_plans",
    "get_tags",
    "get_text",
    "get_priority",
    "link_plan",
    "lookup_category_name_by_id",
    "lookup_category_id_by_name",
    "lookup_priority_name_by_id",
    "lookup_priority_id_by_name",
    "lookup_status_name_by_id",
    "lookup_status_id_by_name",
    "notification_add_cc",
    "notification_get_cc_list",
    "notification_remove_cc",
    "remove_component",
    "remove_tag",
    "store_text",
    "unlink_plan",
    "update",
)

__xmlrpc_namespace__ = "TestCase"


@log_call(namespace=__xmlrpc_namespace__)
def add_comment(request, case_ids, comment):
    """Adds comments to selected test cases.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param str comment: the comment content to add.
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occurred.

    Example::

        # Add comment 'foobar' to case 1
        TestCase.add_comment(1, 'foobar')
        # Add 'foobar' to cases list [1, 2]
        TestCase.add_comment([1, 2], 'foobar')
        # Add 'foobar' to cases list '1, 2' with String
        TestCase.add_comment('1, 2', 'foobar')
    """
    object_pks = pre_process_ids(value=case_ids)
    if not object_pks:
        return
    tcms.comments.models.add_comment(
        request.user,
        "testcases.testcase",
        object_pks,
        comment,
        request.META.get("REMOTE_ADDR"),
    )


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.add_testcasecomponent", raise_exception=True)
def add_component(request, case_ids, component_ids):
    """Adds one or more components to the selected test cases.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param component_ids: give one or more component IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a component ID.
    :type component_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.

    Example::

        # Add component id 1 to case 1
        TestCase.add_component(1, 1)
        # Add component ids list [3, 4] to cases list [1, 2]
        TestCase.add_component([1, 2], [3, 4])
        # Add component ids list '3, 4' to cases list '1, 2' with String
        TestCase.add_component('1, 2', '3, 4')
    """
    from tcms.management.models import Component

    tcs = TestCase.objects.filter(case_id__in=pre_process_ids(value=case_ids))
    cs = Component.objects.filter(id__in=pre_process_ids(value=component_ids))

    for tc in tcs.iterator():
        for c in cs.iterator():
            tc.add_component(component=c)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.add_testcasetag", raise_exception=True)
def add_tag(request, case_ids, tags):
    """Add one or more tags to the selected test cases.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param tags: tag name or a list of tag names to remove.
    :type tags: str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.

    Example::

        # Add tag 'foobar' to case 1
        TestCase.add_tag(1, 'foobar')
        # Add tag list ['foo', 'bar'] to cases list [1, 2]
        TestCase.add_tag([1, 2], ['foo', 'bar'])
        # Add tag list ['foo', 'bar'] to cases list [1, 2] with String
        TestCase.add_tag('1, 2', 'foo, bar')
    """
    tcs = TestCase.objects.filter(case_id__in=pre_process_ids(value=case_ids)).only("pk")

    if not tcs.exists():
        return

    tags = TestTag.string_to_list(tags)

    if not tags:
        return

    for tag in tags:
        t, c = TestTag.objects.get_or_create(name=tag)
        for tc in tcs.iterator():
            tc.add_tag(tag=t)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testruns.add_testcaserun", raise_exception=True)
def add_to_run(request, case_ids, run_ids):
    """Add one or more cases to the selected test runs.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param run_ids: give one or more run IDs. It could be an integer, a string
        containing comma separated IDs, or a list of int each of them is a run
        ID.
    :type run_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.

    Example::

        # Add case 1 to run id 1
        TestCase.add_to_run(1, 1)
        # Add case ids list [1, 2] to run list [3, 4]
        TestCase.add_to_run([1, 2], [3, 4])
        # Add case ids list 1 and 2 to run list 3 and 4 with String
        TestCase.add_to_run('1, 2', '3, 4')
    """
    from tcms.testruns.models import TestRun

    case_ids = pre_process_ids(case_ids)
    run_ids = pre_process_ids(run_ids)

    trs = TestRun.objects.filter(run_id__in=run_ids)
    if not trs.exists():
        raise ValueError("Invalid run_ids")

    tcs = TestCase.objects.filter(case_id__in=case_ids)
    if not tcs.exists():
        raise ValueError("Invalid case_ids")

    for run, case in itertools.product(trs, tcs):
        run.add_case_run(case)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("issuetracker.add_issue", raise_exception=True)
def attach_issue(request, values):
    """Add one or more issues to the selected test cases.

    :param dict values: mapping or list of mappings containing these bug
        information.

        * case: (int) **Required**. Case ID.
        * issue_key: (str) **Required**. issue key.
        * tracker: (int) **Required**. issue tracker ID.
        * summary: (str) optional issue's summary.
        * description: (str) optional issue's description.

    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        values = {
            'case': 1,
            'issue_key': '1000',
            'tracker': 1,
            'summary': 'Testing TCMS',
            'description': 'Just foo and bar',
        }
        TestCase.attach_issue(values)

    .. versionchanged:: 4.2
       Some arguments passed via ``values`` are changed. ``case_id`` is changed
       to ``case``, ``bug_id`` is changed to ``issue_key``, ``bug_system_id``
       is changed to ``tracker``. Default issue tracker is not supported. So,
       if passed-in tracker does not exist, it will be treated as an error.
    """
    if isinstance(values, dict):
        values = [values]

    for value in values:
        form = CaseIssueForm(value)
        if form.is_valid():
            case = form.cleaned_data["case"]
            case.add_issue(
                form.cleaned_data["issue_key"],
                form.cleaned_data["tracker"],
                summary=form.cleaned_data["summary"],
                description=form.cleaned_data["description"],
            )
        else:
            raise ValueError(form_error_messages_to_list(form))


@log_call(namespace=__xmlrpc_namespace__)
def check_case_status(request, name):
    """Looks up and returns a case status by name.

    :param str name: name of the case status.
    :return: a mapping representing found case status.
    :rtype: :class:`TestCaseStatus`.

    Example::

        TestCase.check_case_status('proposed')
    """
    from tcms.testcases.models import TestCaseStatus

    return TestCaseStatus.objects.get(name=name).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def check_priority(request, value):
    """Looks up and returns a priority by name.

    :param str value: name of the priority.
    :return: a mapping representing found priority.
    :rtype: :class:`Priority`.

    Example::

        TestCase.check_priority('p1')
    """
    from tcms.management.models import Priority

    return Priority.objects.get(value=value).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def calculate_average_estimated_time(request, case_ids):
    """Returns an average estimated time for cases.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :return: Time in "HH:MM:SS" format.
    :rtype: str

    Example::

        TestCase.calculate_average_estimated_time([609, 610, 611])
    """
    from django.db.models import Avg

    tcs = TestCase.objects.filter(pk__in=pre_process_ids(case_ids)).only("estimated_time")

    if not tcs.exists():
        raise ValueError("Please input valid case Id")

    # aggregate avg return integer directly rather than timedelta
    seconds = tcs.aggregate(Avg("estimated_time")).get("estimated_time__avg")

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    # TODO: return h:m:s or d:h:m
    return "%02i:%02i:%02i" % (h, m, s)


@log_call(namespace=__xmlrpc_namespace__)
def calculate_total_estimated_time(request, case_ids):
    """Returns an total estimated time for cases.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :return: Time in "HH:MM:SS" format.
    :rtype: str

    Example::

        TestCase.calculate_total_estimated_time([609, 610, 611])
    """
    from django.db.models import Sum

    tcs = TestCase.objects.filter(pk__in=pre_process_ids(case_ids)).only("estimated_time")

    if not tcs.exists():
        raise ValueError("Please input valid case Id")

    # aggregate Sum return integer directly rather than timedelta
    seconds = tcs.aggregate(total=Sum("estimated_time"))["total"].seconds

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    # TODO: return h:m:s or d:h:m
    return "%02i:%02i:%02i" % (h, m, s)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.add_testcase", raise_exception=True)
def create(request, values):
    """Creates a new Test Case object and stores it in the database.

    :param values: a mapping or list of mappings containing these case
        information for creation.

        * product: (int) **Required** ID of Product
        * category: (int) **Required** ID of Category
        * priority: (int) **Required** ID of Priority
        * summary: (str) **Required**
        * case_status: (int) optional ID of case status
        * plan Array/Str/Int optional ID or List of plan_ids
        * component: (int)/str optional ID of Priority
        * default_tester: (str) optional Login of tester
        * estimated_time: (str) optional 2h30m30s(recommend) or HH:MM:SS Format|
        * is_automated: (int) optional 0: Manual, 1: Auto, 2: Both
        * is_automated_proposed: (bool) optional Default 0
        * script: (str) optional
        * arguments: (str) optional
        * requirement: (str) optional
        * alias: (str) optional Must be unique
        * action: (str) optional
        * effect: (str) optional Expected Result
        * setup: (str) optional
        * breakdown: (str) optional
        * tag Array/str optional String Comma separated
        * bug Array/str optional String Comma separated
        * extra_link: (str) optional reference link

    :return: a mapping of newly created test case if a single case was created,
        or a list of mappings of created cases if more than one are created.
    :rtype: dict of list[dict]

    Example::

        # Minimal test case parameters
        values = {
            'category': 1,
            'product': 1,
            'summary': 'Testing XML-RPC',
            'priority': 1,
        }
        TestCase.create(values)
    """
    from tcms.core import forms
    from tcms.xmlrpc.forms import NewCaseForm

    if not (values.get("category") or values.get("summary")):
        raise ValueError()

    values["component"] = pre_process_ids(values.get("component", []))
    values["plan"] = pre_process_ids(values.get("plan", []))
    values["bug"] = pre_process_ids(values.get("bug", []))
    if values.get("estimated_time"):
        values["estimated_time"] = pre_process_estimated_time(values.get("estimated_time"))

    form = NewCaseForm(values)
    form.populate(values.get("product"))

    if form.is_valid():
        # Create the case
        tc = TestCase.create(author=request.user, values=form.cleaned_data)

        # Add case text to the case
        tc.add_text(
            action=form.cleaned_data["action"] or "",
            effect=form.cleaned_data["effect"] or "",
            setup=form.cleaned_data["setup"] or "",
            breakdown=form.cleaned_data["breakdown"] or "",
        )

        # Add the case to specific plans
        for p in form.cleaned_data["plan"]:
            tc.add_to_plan(plan=p)
            del p

        # Add components to the case
        for c in form.cleaned_data["component"]:
            tc.add_component(component=c)
            del c

        # Add tag to the case
        for tag in TestTag.string_to_list(values.get("tag", [])):
            t, c = TestTag.objects.get_or_create(name=tag)
            tc.add_tag(tag=t)
    else:
        # Print the errors if the form is not passed validation.
        raise ValueError(forms.errors_to_list(form))

    return get(request, tc.case_id)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("issuetracker.delete_issue", raise_exception=True)
def detach_issue(request, case_ids, issue_keys):
    """Remove one or more issues to the selected test cases.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param issue_keys: give one or more bug IDs. It could be an integer, a string
        containing comma separated IDs, or a list of int each of them is a bug
        ID.
    :type issue_keys: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.

    Example::

        # Remove issue key 1000 from case 1
        TestCase.detach_issue(1, 1000)
        # Remove issue keys list [1000, 1001] from cases list [1, 2]
        TestCase.detach_issue([1, 2], [1000, 1001])
        # Remove issue keys list '1000, 1001' from cases list '1, 2' with String
        TestCase.detach_issue('1, 2', '1000, 1001')
    """
    case_ids = pre_process_ids(case_ids)
    issue_keys = pre_process_ids(issue_keys)

    cases = TestCase.objects.filter(case_id__in=case_ids).only("pk").iterator()
    for case, issue_key in itertools.product(cases, issue_keys):
        case.remove_issue(issue_key)


@log_call(namespace=__xmlrpc_namespace__)
def filter(request, query):
    """Performs a search and returns the resulting list of test cases.

    :param dict query: a mapping containing these criteria.

        * author: A Bugzilla login (email address)
        * attachments: ForeignKey: Attachment
        * alias: (str)
        * case_id: (int)
        * case_status: ForeignKey: Case Stat
        * category: ForeignKey: :class:`Category`
        * component: ForeignKey: :class:`Component`
        * default_tester: ForeignKey: ``Auth.User``
        * estimated_time: String: 2h30m30s(recommend) or HH:MM:SS
        * plan: ForeignKey: :class:`TestPlan`
        * priority: ForeignKey: :class:`Priority`
        * category__product: ForeignKey: :class:`Product`
        * summary: (str)
        * tags: ForeignKey: :class:`Tags`
        * create_date: Datetime
        * is_automated: 1: Only show current 0: show not current
        * script: (str)

    :return: list of mappings of found :class:`TestCase`.
    :rtype: list

    Example::

        # Get all of cases contain 'TCMS' in summary
        TestCase.filter({'summary__icontain': 'TCMS'})
        # Get all of cases create by xkuang
        TestCase.filter({'author__username': 'xkuang'})
        # Get all of cases the author name starts with x
        TestCase.filter({'author__username__startswith': 'x'})
        # Get all of cases belong to the plan 1
        TestCase.filter({'plan__plan_id': 1})
        # Get all of cases belong to the plan create by xkuang
        TestCase.filter({'plan__author__username': 'xkuang'})
        # Get cases with ID 12345, 23456, 34567 - Here is only support array so far.
        TestCase.filter({'case_id__in': [12345, 23456, 34567]})
    """
    if query.get("estimated_time"):
        query["estimated_time"] = timedelta2int(
            pre_process_estimated_time(query.get("estimated_time"))
        )
    deprecate_critetion_attachment(query)
    return TestCase.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def filter_count(request, values={}):
    """Performs a search and returns the resulting count of cases.

    :param dict values: a mapping containing same criteria with
        :meth:`TestCase.filter <tcms.xmlrpc.api.testcase.filter>`.
    :return: the number of matching cases.
    :rtype: int

    .. seealso:: Examples of :meth:`TestCase.filter <tcms.xmlrpc.api.testcase.filter>`.
    """

    if values.get("estimated_time"):
        values["estimated_time"] = timedelta2int(
            pre_process_estimated_time(values.get("estimated_time"))
        )

    return distinct_count(TestCase, values)


@log_call(namespace=__xmlrpc_namespace__)
def get(request, case_id):
    """Used to load an existing test case from the database.

    :param case_id: case ID.
    :type case_id: int or str
    :return: a mappings representing found test case.
    :rtype: dict

    Example::

        TestCase.get(1)
    """
    tc = TestCase.objects.get(case_id=case_id)

    tc_latest_text = tc.latest_text().serialize()

    response = tc.serialize()
    response["text"] = tc_latest_text
    # get the xmlrpc tags
    tag_ids = tc.tag.values_list("id", flat=True)
    query = {"id__in": tag_ids}
    tags = TestTag.to_xmlrpc(query)
    # cut 'id' attribute off, only leave 'name' here
    tags_without_id = [tag["name"] for tag in tags]
    # replace tag_id list in the serialize return data
    response["tag"] = tags_without_id
    return response


@log_call(namespace=__xmlrpc_namespace__)
def get_issue_tracker(request, id):
    """Used to load an existing test case issue trackers from the database.

    :param id: issue tracker ID.
    :type id: int or str
    :return: a mappings representing found :class:`IssueTracker`.
    :rtype: dict

    Example::

        TestCase.get_issue_tracker(1)
    """
    return IssueTracker.objects.get(pk=int(id)).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_issues(request, case_ids):
    """Get the list of issues that are associated with this test case.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :return: list of mappings of :class:`Issue`.
    :rtype: list[dict]

    Example::

        # Get issues belonging to case 1
        TestCase.get_issues(1)
        # Get issues belonging to cases [1, 2]
        TestCase.get_issues([1, 2])
        # Get issues belonging to case 1 and 2 with string
        TestCase.get_issues('1, 2')
    """
    case_ids = pre_process_ids(case_ids)
    query = {"case__in": case_ids}
    return Issue.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_case_run_history(request, case_id):
    """Get the list of case-runs for all runs this case appears in.

    To limit this list by build or other attribute, see
    :meth:`TestCaseRun.filter <tcms.xmlrpc.api.testcaserun.filter>`.

    :param case_id: case ID.
    :type case_id: int or str
    :return: list of mappings of case runs.

    Example::

        TestCase.get_case_run_history(1)

    .. warning:: NOT IMPLEMENTED - Case run history is different than before
    """
    raise NotImplementedError("Not implemented RPC method")


@log_call(namespace=__xmlrpc_namespace__)
def get_case_status(request, id=None):
    """Get the case status matching the given id.

    :param int id: case status ID.
    :return: a mapping representing found :class:`TestCaseStatus`.
    :rtype: dict

    Example::

        # Get all of case status
        TestCase.get_case_status()
        # Get case status by ID 1
        TestCase.get_case_status(1)
    """
    from tcms.testcases.models import TestCaseStatus

    if id is None:
        return TestCaseStatus.to_xmlrpc()
    else:
        return TestCaseStatus.objects.get(id=id).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_change_history(request, case_id):
    """Get the list of changes to the fields of this case.

    :param case_id: case ID.
    :type case_id: int or str
    :return: a list of mappings of history.

    Example::

        TestCase.get_change_history(12345)

    .. warning::

       NOT IMPLEMENTED - Case history is different than before
    """
    raise NotImplementedError("Not implemented RPC method")


@log_call(namespace=__xmlrpc_namespace__)
def get_components(request, case_id):
    """Get the list of components attached to this case.

    :param case_id: case ID.
    :type case_id: int or str
    :return: a list of mappings of :class:`Component`.
    :rtype: list[dict]

    Example::

        TestCase.get_components(1)
    """
    from tcms.management.models import Component

    tc = TestCase.objects.get(case_id=case_id)

    component_ids = tc.component.values_list("id", flat=True)
    query = {"id__in": component_ids}
    return Component.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_plans(request, case_id):
    """Get the list of plans that this case is linked to.

    :param case_id: case ID.
    :type case_id: int or str
    :return: a list of mappings of :class:`TestPlan`.
    :rtype: list[dict]

    Example::

        TestCase.get_plans(1)
    """
    tc = TestCase.objects.get(case_id=case_id)

    plan_ids = tc.plan.values_list("plan_id", flat=True)
    query = {"plan_id__in": plan_ids}
    return TestPlan.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_tags(request, case_id):
    """Get the list of tags attached to this case.

    :param case_id: case ID.
    :type case_id: int or str
    :return: a list of mappings of :class:`TestTag`.
    :rtype: list[dict]

    Example::

        TestCase.get_tags(1)
    """
    tc = TestCase.objects.get(case_id=case_id)

    tag_ids = tc.tag.values_list("id", flat=True)
    query = {"id__in": tag_ids}
    return TestTag.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_text(request, case_id, case_text_version=None):
    """
    Get the associated case' Action, Expected Results, Setup, Breakdown for a
    given version

    :param case_id: case ID.
    :type case_id: int or str
    :param int case_text_version: optional version of the text you want
        returned. Defaults to the latest, if omitted.
    :return: a mapping representing a case text.
    :rtype: dict

    Example::

        # Get all latest case text
        TestCase.get_text(1)
        # Get all case text with version 4
        TestCase.get_text(1, 4)
    """
    tc = TestCase.objects.get(case_id=case_id)

    return tc.get_text_with_version(case_text_version=case_text_version).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_priority(request, id):
    """Get the priority matching the given id.

    :param int id: priority ID.
    :return: a mapping representing found :class:`Priority`.
    :rtype: dict

    Example::

        TestCase.get_priority(1)
    """
    from tcms.management.models import Priority

    return Priority.objects.get(id=id).serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.add_testcaseplan", raise_exception=True)
def link_plan(request, case_ids, plan_ids):
    """ "Link test cases to the given plan.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param plan_ids: give one or more plan IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a plan ID.
    :type plan_ids: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list or list[dict]

    Example::

        # Add case 1 to plan id 2
        TestCase.link_plan(1, 2)
        # Add case ids list [1, 2] to plan list [3, 4]
        TestCase.link_plan([1, 2], [3, 4])
        # Add case ids list 1 and 2 to plan list 3 and 4 with String
        TestCase.link_plan('1, 2', '3, 4')
    """
    case_ids = pre_process_ids(value=case_ids)
    qs = TestCase.objects.filter(pk__in=case_ids)
    tcs_ids = qs.values_list("pk", flat=True)

    # Check the non-exist case ids.
    ids_diff = set(case_ids) - set(tcs_ids.iterator())
    if ids_diff:
        ids_str = ",".join(map(str, ids_diff))
        if len(ids_diff) > 1:
            err_msg = "TestCases %s do not exist." % ids_str
        else:
            err_msg = "TestCase %s does not exist." % ids_str
        raise ObjectDoesNotExist(err_msg)

    plan_ids = pre_process_ids(value=plan_ids)
    qs = TestPlan.objects.filter(pk__in=plan_ids)
    tps_ids = qs.values_list("pk", flat=True)

    # Check the non-exist plan ids.
    ids_diff = set(plan_ids) - set(tps_ids.iterator())
    if ids_diff:
        ids_str = ",".join(map(str, ids_diff))
        if len(ids_diff) > 1:
            err_msg = "TestPlans %s do not exist." % ids_str
        else:
            err_msg = "TestPlan %s does not exist." % ids_str
        raise ObjectDoesNotExist(err_msg)

    # (plan_id, case_id) pair might probably exist in test_case_plans table, so
    # skip the ones that do exist and create the rest.
    # note: this query returns a list of tuples!
    existing = TestCasePlan.objects.filter(plan__in=plan_ids, case__in=case_ids).values_list(
        "plan", "case"
    )

    # Link the plans to cases
    def _generate_link_plan_value():
        for plan_id in plan_ids:
            for case_id in case_ids:
                if (plan_id, case_id) not in existing:
                    yield plan_id, case_id

    TestCasePlan.objects.bulk_create(
        [
            TestCasePlan(plan_id=_plan_id, case_id=_case_id)
            for _plan_id, _case_id in _generate_link_plan_value()
        ]
    )


@log_call(namespace=__xmlrpc_namespace__)
def lookup_category_name_by_id(request, id):
    """Lookup category name by ID

    .. deprecated:: x.y

       Use :meth:`Product.get_category <tcms.xmlrpc.api.product.get_category>` instead.
    """
    from tcms.xmlrpc.api.product import get_category

    return get_category(request=request, id=id)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_category_id_by_name(request, name, product):
    """Lookup category ID by name

    .. deprecated:: x.y

       Use :meth:`Product.check_category <tcms.xmlrpc.api.product.check_category>` instead.
    """
    from tcms.xmlrpc.api.product import check_category

    return check_category(request=request, name=name, product=product)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_priority_name_by_id(request, id):
    """Lookup priority name by ID

    .. deprecated:: x.y

       Use :meth:`TestCase.get_priority <tcms.xmlrpc.api.testcase.get_priority>` instead.
    """
    return get_priority(request=request, id=id)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_priority_id_by_name(request, value):
    """Lookup priority ID by name

    .. deprecated:: x.y

       Use :meth:`TestCase.check_priority <tcms.xmlrpc.api.testcase.check_priority>` instead.
    """
    return check_priority(request=request, value=value)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_status_name_by_id(request, id):
    """Lookup status name by ID

    .. deprecated:: x.y

       Use :meth:`TestCase.get_case_status <tcms.xmlrpc.api.testcase.get_case_status >` instead.
    """
    return get_case_status(request=request, id=id)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_status_id_by_name(request, name):
    """Lookup status ID by name

    .. deprecated:: x.y

       Use :meth:`TestCase.check_case_status <tcms.xmlrpc.api.testcase.check_case_status >` instead.
    """
    return check_case_status(request=request, name=name)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.delete_testcasecomponent", raise_exception=True)
def remove_component(request, case_ids, component_ids):
    """Removes selected component from the selected test case.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param component_ids: give one or more component IDs. It could be an
        integer, a string containing comma separated IDs, or a list of int each
        of them is a component ID.
    :type plan_ids: int, str or list
    :return: a list which is emtpy on success.
    :rtype: list

    Example::

        # Remove component id 1 from case 1
        TestCase.remove_component(1, 1)
        # Remove component ids list [3, 4] from cases list [1, 2]
        TestCase.remove_component([1, 2], [3, 4])
        # Remove component ids list '3, 4' from cases list '1, 2' with String
        TestCase.remove_component('1, 2', '3, 4')
    """
    from tcms.management.models import Component

    cases = TestCase.objects.filter(case_id__in=pre_process_ids(value=case_ids))
    components = Component.objects.filter(id__in=pre_process_ids(value=component_ids))

    for case, component in itertools.product(cases, components):
        case.remove_component(component=component)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.delete_testcasetag", raise_exception=True)
def remove_tag(request, case_ids, tags):
    """Remove a tag from a case.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param tags: tag name or a list of tag names to remove.
    :type tags: str or list
    :return: a list which is emtpy on success.
    :rtype: list

    Example::

        # Remove tag 'foo' from case 1
        TestCase.remove_tag(1, 'foo')
        # Remove tag 'foo' and bar from cases list [1, 2]
        TestCase.remove_tag([1, 2], ['foo', 'bar'])
        # Remove tag 'foo' and 'bar' from cases list '1, 2' with String
        TestCase.remove_tag('1, 2', 'foo, bar')
    """
    cases = TestCase.objects.filter(case_id__in=pre_process_ids(value=case_ids))
    tags = TestTag.objects.filter(name__in=TestTag.string_to_list(tags))

    for case, tag in itertools.product(cases, tags):
        case.remove_tag(tag)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.add_testcasetext", raise_exception=True)
def store_text(request, case_id, action, effect="", setup="", breakdown="", author_id=None):
    """Update the large text fields of a case.

    :param int case_id: case ID.
    :param str action: action text of specified case.
    :param str effect: effect text of specified case. Defaults to empty string if omitted.
    :param str setup: setup text of specified case. Defaults to empty string if omitted.
    :param str breakdown: breakdown text of specified case. Defaults to empty string if omitted.
    :param int auth_id: author's user ID.
    :return: a mapping of newly added text of specified case.
    :rtype: dict

    Example::

        TestCase.store_text(1, 'Action')
        TestCase.store_text(1, 'Action', 'Effect', 'Setup', 'Breakdown', 2)
    """
    from django.contrib.auth.models import User

    tc = TestCase.objects.get(case_id=case_id)

    if author_id:
        author = User.objects.get(id=author_id)
    else:
        author = request.user

    return tc.add_text(
        author=author,
        action=action and action.strip(),
        effect=effect and effect.strip(),
        setup=setup and setup.strip(),
        breakdown=breakdown and breakdown.strip(),
    ).serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.delete_testcaseplan", raise_exception=True)
def unlink_plan(requst, case_id, plan_id):
    """
    Unlink a test case from the given plan. If only one plan is linked, this
    will delete the test case.

    :param case_id: case ID.
    :type case_id: int or str
    :param int plan_id: plan ID from where to unlink the specified case.
    :return: a list of mappings of test plans that are still linked to the
        specified case. If there is no linked test plans, empty list will be
        returned.
    :rtype: list[dict]

    Example::

        # Unlink case 100 from plan 10
        TestCase.unlink_plan(100, 10)
    """
    TestCasePlan.objects.filter(case=case_id, plan=plan_id).delete()
    plan_pks = TestCasePlan.objects.filter(case=case_id).values_list("plan", flat=True)
    return TestPlan.to_xmlrpc(query={"pk__in": plan_pks})


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.change_testcase", raise_exception=True)
def update(request, case_ids, values):
    """Updates the fields of the selected case or cases.

                 $values   - Hash of keys matching TestCase fields and the new values
                             to set each field to.

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param dict values: a mapping containing these case data to update.

        * case_status: (ini) optional
        * product: (ini) optional (Required if changes category)
        * category: (ini) optional
        * priority: (ini) optional
        * default_tester: (str or int) optional (str - user_name, int - user_id)
        * estimated_time: (str) optional (2h30m30s(recommend) or HH:MM:SS
        * is_automated: (ini) optional (0 - Manual, 1 - Auto, 2 - Both)
        * is_automated_proposed: (bool) optional
        * script: (str) optional
        * arguments: (str) optional
        * summary: (str) optional
        * requirement: (str) optional
        * alias: (str) optional
        * notes: (str) optional
        * extra_link: (str) optional (reference link)

    :return: a list of mappings of updated :class:`TestCase`.
    :rtype: list(dict)

    Example::

        # Update alias to 'tcms' for case 1 and 2
        TestCase.update([1, 2], {'alias': 'tcms'})
    """
    from tcms.core import forms
    from tcms.xmlrpc.forms import UpdateCaseForm

    if values.get("estimated_time"):
        values["estimated_time"] = pre_process_estimated_time(values.get("estimated_time"))

    form = UpdateCaseForm(values)

    if values.get("category") and not values.get("product"):
        raise ValueError("Product ID is required for category")

    if values.get("product"):
        form.populate(product_id=values["product"])

    if form.is_valid():
        tcs = TestCase.update(
            case_ids=pre_process_ids(value=case_ids),
            values=form.cleaned_data,
        )
    else:
        raise ValueError(forms.errors_to_list(form))

    query = {"pk__in": tcs.values_list("pk", flat=True)}
    return TestCase.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def validate_cc_list(cc_list):
    """Validate each email in cc_list argument

    This is called by ``notification_*`` methods internally.

    No return value, and if any email in cc_list is not valid, ValidationError
    will be raised.
    """

    if not isinstance(cc_list, list):
        raise TypeError("cc_list should be a list object.")

    field = EmailField(
        required=True,
        error_messages={
            "required": "Missing email address.",
            "invalid": "%(value)s is not a valid email address.",
        },
    )

    for item in cc_list:
        field.clean(item)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.change_testcase", raise_exception=True)
def notification_add_cc(request, case_ids, cc_list):
    """Add email addresses to the notification CC list of specific TestCases

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param list cc_list: list of email addresses to be added to the specified
        cases.
    """
    validate_cc_list(cc_list)

    tc_ids = pre_process_ids(case_ids)

    for tc in TestCase.objects.filter(pk__in=tc_ids).iterator():
        # First, find those that do not exist yet.
        existing_cc = tc.emailing.get_cc_list()
        adding_cc = list(set(cc_list) - set(existing_cc))

        tc.emailing.add_cc(adding_cc)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.change_testcase", raise_exception=True)
def notification_remove_cc(request, case_ids, cc_list):
    """Remove email addresses from the notification CC list of specific TestCases

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :param list cc_list: list of email addresses to be removed from specified cases.
    """
    validate_cc_list(cc_list)
    tc_ids = pre_process_ids(case_ids)
    for tc in TestCase.objects.filter(pk__in=tc_ids).only("pk").iterator():
        tc.emailing.remove_cc(cc_list)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testcases.change_testcase", raise_exception=True)
def notification_get_cc_list(request, case_ids):
    """Return whole CC list of each TestCase

    :param case_ids: give one or more case IDs. It could be an integer, a
        string containing comma separated IDs, or a list of int each of them is
        a case ID.
    :type case_ids: int, str or list
    :return: a mapping from case ID to list of CC email addresses.
    :rtype: dict(str, list)
    """
    result = {}
    tc_ids = pre_process_ids(case_ids)
    for tc in TestCase.objects.filter(pk__in=tc_ids).iterator():
        cc_list = tc.emailing.get_cc_list()
        result[str(tc.pk)] = cc_list
    return result

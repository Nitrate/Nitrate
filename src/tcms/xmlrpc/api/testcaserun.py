# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import permission_required

import tcms.comments.models
from tcms.core.utils import form_error_messages_to_list
from tcms.issuetracker.models import Issue
from tcms.issuetracker.services import find_service
from tcms.linkreference.models import LinkReference, create_link
from tcms.testcases.forms import CaseRunIssueForm
from tcms.testruns.models import TestCaseRun, TestCaseRunStatus
from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.serializer import XMLRPCSerializer
from tcms.xmlrpc.utils import distinct_count, pre_process_ids

__all__ = (
    "add_comment",
    "attach_issue",
    "attach_log",
    "check_case_run_status",
    "create",
    "detach_issue",
    "detach_log",
    "filter",
    "filter_count",
    "get",
    "get_s",
    "get_issues",
    "get_issues_s",
    "get_case_run_status",
    "get_completion_time",
    "get_completion_time_s",
    "get_history",
    "get_history_s",
    "get_logs",
    "lookup_status_name_by_id",
    "lookup_status_id_by_name",
    "update",
)

__xmlrpc_namespace__ = "TestCaseRun"


class GetCaseRun:
    def pre_process_tcr(self, case_run_id):
        return TestCaseRun.objects.get(pk=case_run_id)

    def pre_process_tcr_s(self, run_id, case_id, build_id, environment_id=0):
        query = {"run__pk": run_id, "case__pk": case_id, "build__pk": build_id}

        if environment_id:
            query["environment_id"] = environment_id

        return TestCaseRun.objects.get(**query)


gcr = GetCaseRun()


@log_call(namespace=__xmlrpc_namespace__)
def add_comment(request, case_run_ids, comment):
    """Adds comments to selected test case runs.

    :param case_run_ids: give one or more case run IDs. It could be an integer,
        a string containing comma separated IDs, or a list of int each of them
        is a case run ID.
    :type run_ids: int, str or list
    :param str comment: the comment content to add.
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Add comment 'foobar' to case run 1
        TestCaseRun.add_comment(1, 'foobar')
        # Add 'foobar' to case runs list [1, 2]
        TestCaseRun.add_comment([1, 2], 'foobar')
        # Add 'foobar' to case runs list '1, 2' with String
        TestCaseRun.add_comment('1, 2', 'foobar')
    """
    object_pks = pre_process_ids(value=case_run_ids)
    if not object_pks:
        return
    tcms.comments.models.add_comment(
        request.user,
        "testruns.testcaserun",
        object_pks,
        comment,
        request.META.get("REMOTE_ADDR"),
    )


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("issuetracker.add_issue", raise_exception=True)
def attach_issue(request, values):
    """Add one or more issues to the selected test cases.

    :param dict values: a mapping containing these data to create a test run.

        * issue_key: (str) **Required** the issue key.
        * case_run: (int) **Required** ID of Case
        * tracker: (int) **Required** ID of issue tracker that issue should
          belong to.
        * summary: (str) optional issue's summary
        * description: (str) optional issue' description

    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Attach an issue 67890 to case run 12345
        TestCaseRun.attach_issue({
                'case_run': [12345],
                'issue_key': '67890',
                'tracker': 1,
                'summary': 'Testing TCMS',
                'description': 'Just foo and bar',
            })

    .. versionchanged:: 4.2
       Some arguments passed via ``values`` are changed. ``case_run_id`` is
       changed to ``case_run``, ``bug_id`` is changed to ``issue_key``,
       ``bz_system_id`` is changed to ``tracker``. ``issue_key`` accepts string
       instead of integer. ``case_run`` within ``values`` must be a list of
       test case ids.
    """
    if isinstance(values, dict):
        values = [
            values,
        ]

    for value in values:
        form = CaseRunIssueForm(value)
        if form.is_valid():
            service = find_service(form.cleaned_data["tracker"])
            issue_key = form.cleaned_data["issue_key"]
            summary = form.cleaned_data["summary"]
            description = form.cleaned_data["description"]
            case_runs = form.cleaned_data["case_run"]
            for case_run in case_runs:
                service.add_issue(
                    issue_key,
                    case_run.case,
                    case_run=case_run,
                    summary=summary,
                    description=description,
                )
        else:
            raise ValueError(form_error_messages_to_list(form))


@log_call(namespace=__xmlrpc_namespace__)
def check_case_run_status(request, name):
    """Get case run status by name

    :param str name: the status name.
    :return: a mapping representing found case run status.
    :rtype: dict

    Example::

        TestCaseRun.check_case_run_status('idle')
    """
    return TestCaseRunStatus.objects.get(name=name).serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testruns.add_testcaserun", raise_exception=True)
def create(request, values):
    """Creates a new Test Case Run object and stores it in the database.

    :param dict values: a mapping containing these data to create a case run.

        * run: (int) **Required** ID of Test Run
        * case: (int) **Required** ID of test case
        * build: (int) **Required** ID of a Build in plan's product
        * assignee: (int) optional ID of assignee
        * case_run_status: (int) optional Defaults to "IDLE"
        * case_text_version: (int) optional Default to latest case text version
        * notes: (str) optional
        * sortkey: (int) optional a.k.a. Index, Default to 0

    :return: a mapping representing a newly created case run.
    :rtype: dict

    Example::

        # Minimal test case parameters
        values = {
            'run': 1990,
            'case': 12345,
            'build': 123,
        }
        TestCaseRun.create(values)
    """
    from tcms.core import forms
    from tcms.testruns.forms import XMLRPCNewCaseRunForm

    form = XMLRPCNewCaseRunForm(values)

    if not isinstance(values, dict):
        raise TypeError("Argument values must be in dict type.")
    if not values:
        raise ValueError("Argument values is empty.")

    if form.is_valid():
        tr = form.cleaned_data["run"]

        tcr = tr.add_case_run(
            case=form.cleaned_data["case"],
            build=form.cleaned_data["build"],
            assignee=form.cleaned_data["assignee"],
            case_run_status=form.cleaned_data["case_run_status"],
            case_text_version=form.cleaned_data["case_text_version"],
            notes=form.cleaned_data["notes"],
            sortkey=form.cleaned_data["sortkey"],
        )
    else:
        raise ValueError(forms.errors_to_list(form))

    return tcr.serialize()


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("issuetracker.delete_issue", raise_exception=True)
def detach_issue(request, case_run_ids, issue_keys):
    """Remove one or more issues to the selected test case-runs.

    :param case_run_ids: give one or more case run IDs. It could be an integer,
        a string containing comma separated IDs, or a list of int each of them
        is a case run ID.
    :type run_ids: int, str or list
    :param issue_keys: give one or more case run IDs. It could be an integer,
        a string containing comma separated IDs, or a list of int each of them
        is a case run ID.
    :type issue_keys: int, str or list
    :return: a list which is empty on success or a list of mappings with
        failure codes if a failure occured.
    :rtype: list

    Example::

        # Remove issue 1000 from case run 1
        TestCaseRun.detach_issue(1, 1000)
        # Remove issues [1000, 2000] from case runs list [1, 2]
        TestCaseRun.detach_issue([1, 2], [1000, 2000])
        # Remove issues '1000, 2000' from case runs list '1, 2' with String
        TestCaseRun.detach_issue('1, 2', '1000, 2000')
    """
    tcrs = TestCaseRun.objects.filter(pk__in=pre_process_ids(case_run_ids))
    issue_keys = pre_process_ids(issue_keys)

    for tcr in tcrs.iterator():
        for issue_key in issue_keys:
            tcr.remove_issue(issue_key=issue_key, case_run=tcr)


@log_call(namespace=__xmlrpc_namespace__)
def filter(request, values={}):
    """Performs a search and returns the resulting list of test cases.

    :param dict values: a mapping containing these criteria.

        * case_run_id: (int)
        * assignee: ForeignKey: Auth.User
        * build: ForeignKey: TestBuild
        * case: ForeignKey: TestCase
        * case_run_status: ForeignKey: TestCaseRunStatus
        * notes: (str)
        * run: ForeignKey: TestRun
        * tested_by: ForeignKey: Auth.User
        * running_date: Datetime
        * close_date: Datetime

    :return: a list of found :class:`TestCaseRun`.
    :rtype: list[dict]

    Example::

        # Get all case runs contain 'TCMS' in case summary
        TestCaseRun.filter({'case__summary__icontain': 'TCMS'})
    """
    return TestCaseRun.to_xmlrpc(values)


@log_call(namespace=__xmlrpc_namespace__)
def filter_count(request, values={}):
    """Performs a search and returns the resulting count of cases.

    :param dict values: a mapping containing criteria. See also
        :class:`TestCaseRun.filter <tcms.xmlrpc.api.testcaserun.filter>`.
    :return: total matching cases.
    :rtype: int

    .. seealso::
       See example in :class:`TestCaseRun.filter <tcms.xmlrpc.api.testcaserun.filter>`.
    """
    from tcms.testruns.models import TestCaseRun

    return distinct_count(TestCaseRun, values)


@log_call(namespace=__xmlrpc_namespace__)
def get(request, case_run_id):
    """Used to load an existing test case-run from the database.

    :param int case_run_id: case run ID.
    :return: a mapping representing found :class:`TestCaseRun`.
    :rtype: dict

    Example::

        TestCaseRun.get(1)
    """
    return gcr.pre_process_tcr(case_run_id=case_run_id).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_s(request, case_id, run_id, build_id, environment_id=0):
    """Used to load an existing test case from the database.

    :param int case_id: case ID.
    :param int run_id: run ID.
    :param int build_id: build ID.
    :param int environment_id: optional environment ID. Defaults to ``0``.
    :return: a list of found :class:`TestCaseRun`.
    :rtype: list[dict]

    Example::

        TestCaseRun.get_s(1, 2, 3, 4)
    """
    return gcr.pre_process_tcr_s(run_id, case_id, build_id, environment_id).serialize()


@log_call(namespace=__xmlrpc_namespace__)
def get_issues(request, case_run_id):
    """Get the list of issues that are associated with this test case run

    :param int case_run_id: case run ID.
    :return: a list of mappings of :class:`Issue`.
    :rytpe: list[dict]

    Example::

        TestCaseRun.get_issues(10)
    """
    query = {"case_run": int(case_run_id)}
    return Issue.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_issues_s(request, run_id, case_id, build_id, environment_id=0):
    """Get the list of issues that are associated with this test case run

    :param int case_id: case ID.
    :param int run_id: run ID.
    :param int build_id: build ID.
    :param int environment_id: optional environment ID. Defaults to ``0``.
    :return: a list of found :class:`Issue`.
    :rtype: list[dict]

    Example::

        TestCaseRun.get_issues_s(1, 2, 3, 4)
    """
    query = {
        "case_run__run": int(run_id),
        "case_run__build": int(build_id),
        "case_run__case": int(case_id),
    }
    # Just keep the same with original implementation that calls
    # pre_process_tcr_s. In which following logical exists. I don't why this
    # should happen there exactly.
    # FIXME: seems it should be `if environment_id is not None`, otherwise such
    # judgement should not happen.
    if environment_id:
        query["case_run__environment_id"] = int(environment_id)
    return Issue.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def get_case_run_status(request, case_run_status_id=None):
    """Get case run status

    :param int case_run_status_id: optional case run status ID.
    :return: a mapping representing a case run status of specified ID.
        Otherwise, a list of mappings of all case run status will be returned,
        if ``case_run_status_id`` is omitted.
    :rtype: dict or list[dict]

    Example::

        # Get all of case run status
        TestCaseRun.get_case_run_status()
        # Get case run status by ID 1
        TestCaseRun.get_case_run_status(1)
    """
    if case_run_status_id:
        return TestCaseRunStatus.objects.get(pk=case_run_status_id).serialize()

    return TestCaseRunStatus.to_xmlrpc()


@log_call(namespace=__xmlrpc_namespace__)
def get_completion_time(request, case_run_id):
    """Returns the time in seconds that it took for this case to complete.

    :param int case_run_id: caes run ID.
    :return: Seconds since run was started till this case was completed.  Or
        empty hash for insufficent data.
    :rtype: int

    Example::

        TestCaseRun.get_completion_time(1)
    """
    from tcms.core.forms.widgets import SECONDS_PER_DAY

    tcr = gcr.pre_process_tcr(case_run_id=case_run_id)
    if not tcr.running_date or not tcr.close_date:
        return

    time = tcr.close_date - tcr.running_date
    time = time.days * SECONDS_PER_DAY + time.seconds
    return time


@log_call(namespace=__xmlrpc_namespace__)
def get_completion_time_s(request, run_id, case_id, build_id, environment_id=0):
    """Returns the time in seconds that it took for this case to complete.

    :param int case_id: case ID.
    :param int run_id: run ID.
    :param int build_id: build ID.
    :param int environment_id: optional environment ID. Defaults to ``0``.
    :return: Seconds since run was started till this case was completed.  Or
        empty hash for insufficent data.
    :rtype: int

    Example::

        TestCaseRun.get_completion_time_s(1, 2, 3, 4)
    """
    from tcms.core.forms.widgets import SECONDS_PER_DAY

    tcr = gcr.pre_process_tcr_s(
        run_id=run_id,
        case_id=case_id,
        build_id=build_id,
        environment_id=environment_id,
    )
    if not tcr.running_date or not tcr.close_date:
        return

    time = tcr.close_date - tcr.running_date
    time = time.days * SECONDS_PER_DAY + time.seconds
    return time


@log_call(namespace=__xmlrpc_namespace__)
def get_history(request, case_run_id):
    """Get the list of case-runs for all runs this case appears in.

    :param int case_run_id: case run ID.
    :return: a list of mappings of :class:`TestCaseRun`.
    :rtype: list[dict]

    .. warning::
       NOT IMPLEMENTED
    """
    raise NotImplementedError("Not implemented RPC method")


@log_call(namespace=__xmlrpc_namespace__)
def get_history_s(request, run_id, build_id, environment_id):
    """Get the list of case-runs for all runs this case appears in.

    :param int case_id: case ID.
    :param int run_id: run ID.
    :param int build_id: build ID.
    :param int environment_id: optional environment ID. Defaults to ``0``.
    :return: a list mappings of :class:`TestCaseRun`.
    :rtype: list[dict]

    .. warning::
       NOT IMPLEMENTED
    """
    raise NotImplementedError("Not implemented RPC method")


@log_call(namespace=__xmlrpc_namespace__)
def lookup_status_name_by_id(request, id):
    """
    DEPRECATED - CONSIDERED HARMFUL Use TestCaseRun.get_case_run_status instead
    """
    return get_case_run_status(request=request, id=id)


@log_call(namespace=__xmlrpc_namespace__)
def lookup_status_id_by_name(request, name):
    """
    DEPRECATED - CONSIDERED HARMFUL Use TestCaseRun.check_case_run_status instead
    """
    return check_case_run_status(request=request, name=name)


@log_call(namespace=__xmlrpc_namespace__)
@permission_required("testruns.change_testcaserun", raise_exception=True)
def update(request, case_run_ids, values):
    """Updates the fields of the selected case-runs.

    :param case_run_ids: give one or more case run IDs. It could be an integer,
        a string containing comma separated IDs, or a list of int each of them
        is a case run ID.
    :type run_ids: int, str or list
    :param dict values: a mapping containing these data to update specified
        case runs.

        * build: (int)
        * assignee: (int)
        * case_run_status: (int)
        * notes: (str)
        * sortkey: (int)

    :return: In the case of a single object, it is returned. If a list was
        passed, it returns an array of object hashes. If the update on any
        particular object failed, the hash will contain a ERROR key and the
        message as to why it failed.

    Example::

        # Update alias to 'tcms' for case 12345 and 23456
        TestCaseRun.update([12345, 23456], {'assignee': 2206})
    """
    from datetime import datetime

    from tcms.core import forms
    from tcms.testruns.forms import XMLRPCUpdateCaseRunForm

    pks_to_update = pre_process_ids(case_run_ids)

    tcrs = TestCaseRun.objects.filter(pk__in=pks_to_update)
    form = XMLRPCUpdateCaseRunForm(values)

    if form.is_valid():
        data = {}

        if form.cleaned_data["build"]:
            data["build"] = form.cleaned_data["build"]

        if form.cleaned_data["assignee"]:
            data["assignee"] = form.cleaned_data["assignee"]

        if form.cleaned_data["case_run_status"]:
            data["case_run_status"] = form.cleaned_data["case_run_status"]
            data["tested_by"] = request.user
            data["close_date"] = datetime.now()

        if "notes" in values:
            if values["notes"] in (None, ""):
                data["notes"] = values["notes"]
            if form.cleaned_data["notes"]:
                data["notes"] = form.cleaned_data["notes"]

        if form.cleaned_data["sortkey"] is not None:
            data["sortkey"] = form.cleaned_data["sortkey"]

        tcrs.update(**data)

    else:
        raise ValueError(forms.errors_to_list(form))

    query = {"pk__in": pks_to_update}
    return TestCaseRun.to_xmlrpc(query)


@log_call(namespace=__xmlrpc_namespace__)
def attach_log(request, case_run_id, name, url):
    """Add new log link to TestCaseRun

    :param int case_run_id: case run ID.
    :param str name: link name.
    :param str url: link URL.
    """
    test_case_run = TestCaseRun.objects.get(pk=case_run_id)
    create_link(name=name, url=url, link_to=test_case_run)


@log_call(namespace=__xmlrpc_namespace__)
def detach_log(request, case_run_id, link_id):
    """Remove log link to TestCaseRun

    :param int case_run_id: case run ID.
    :param int link_id: case run ID.
    """
    TestCaseRun.objects.get(pk=case_run_id)
    LinkReference.unlink(link_id)


@log_call(namespace=__xmlrpc_namespace__)
def get_logs(request, case_run_id):
    """Get log links to TestCaseRun

    :param int case_run_id: case run ID.
    :return: list of mappings of found logs :class:`LinkReference`.
    :rtype: list[dict]
    """
    test_case_run = TestCaseRun.objects.get(pk=case_run_id)
    links = LinkReference.get_from(test_case_run)
    s = XMLRPCSerializer(links)
    return s.serialize_queryset()

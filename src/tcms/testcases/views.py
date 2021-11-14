# -*- coding: utf-8 -*-

import datetime
import itertools
import json
import logging
from operator import attrgetter, itemgetter
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Count
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic.base import TemplateView, View
from django.views.generic.edit import FormView
from django_comments.models import Comment

from tcms.core.db import SQLExecution
from tcms.core.raw_sql import RawSQL
from tcms.core.responses import JsonResponseBadRequest
from tcms.core.utils import DataTableResult, form_error_messages_to_list
from tcms.core.views import prompt
from tcms.issuetracker.models import IssueTracker
from tcms.logs.models import TCMSLogModel
from tcms.management.models import Priority
from tcms.search.order import apply_order
from tcms.search.views import remove_from_request_path
from tcms.testcases import actions, data, sqls
from tcms.testcases.data import get_exported_cases_and_related_data
from tcms.testcases.fields import CC_LIST_DEFAULT_DELIMITER
from tcms.testcases.forms import (
    CaseAutomatedForm,
    CaseComponentForm,
    CaseFilterForm,
    CaseIssueForm,
    CaseNotifyForm,
    CasePlansForm,
    CaseRemoveIssueForm,
    CaseTagForm,
    CloneCaseForm,
    EditCaseForm,
    NewCaseForm,
    SearchCaseForm,
)
from tcms.testcases.models import TestCase, TestCaseComponent, TestCasePlan, TestCaseStatus
from tcms.testplans.forms import SearchPlanForm
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestCaseRun, TestCaseRunStatus

logger = logging.getLogger(__name__)

MODULE_NAME = "testcases"

TESTCASE_OPERATION_ACTIONS = (
    "search",
    "sort",
    "update",
    "remove",  # including remove tag from cases
    "add",  # including add tag to cases
    "change",
    "delete_cases",  # unlink cases from a TestPlan
)


# _____________________________________________________________________________
# helper functions


def plan_from_request_or_none(request, pk_enough=False):
    """Get TestPlan from request data either get or post

    This method relies on the existence of from_plan within REQUEST.

    :param request: the Django HTTPRequest object.
    :param bool pk_enough: indicate whether it is ok to just return the plan
        ID, otherwise, the plan object will be returned.
    :return: the plan ID or corresponding plan object. If ``from_plan`` does
        not exist in the query string or the value of ``from_plan`` is not an
        integer, None will be returned.
    :rtype: int or TestPlan or None
    :raises Http404: if plan ID does not exist in the database.
    """
    tp_id = request.POST.get("from_plan") or request.GET.get("from_plan")
    if not tp_id:
        return None
    if pk_enough:
        return int(tp_id) if tp_id.isdigit() else None
    else:
        return get_object_or_404(TestPlan, plan_id=tp_id)


def update_case_email_settings(tc, n_form):
    """Update testcase's email settings."""

    tc.emailing.notify_on_case_update = n_form.cleaned_data["notify_on_case_update"]
    tc.emailing.notify_on_case_delete = n_form.cleaned_data["notify_on_case_delete"]
    tc.emailing.auto_to_case_author = n_form.cleaned_data["author"]
    # tc.emailing.auto_to_case_tester = n_form.cleaned_data['default_tester_of_case']
    tc.emailing.auto_to_run_manager = n_form.cleaned_data["managers_of_runs"]
    tc.emailing.auto_to_run_tester = n_form.cleaned_data["default_testers_of_runs"]
    tc.emailing.auto_to_case_run_assignee = n_form.cleaned_data["assignees_of_case_runs"]

    default_tester = n_form.cleaned_data["default_tester_of_case"]
    if default_tester and tc.default_tester_id:
        tc.emailing.auto_to_case_tester = True

    tc.emailing.save()

    # Continue to update CC list
    valid_emails = n_form.cleaned_data["cc_list"]
    tc.emailing.update_cc_list(valid_emails)


def group_case_issues(issues):
    """Group issues by issue key."""
    issues = itertools.groupby(issues, attrgetter("issue_key"))
    return [(pk, list(_issues)) for pk, _issues in issues]


class ChangeCaseAutomatedPropertyView(PermissionRequiredMixin, FormView):
    """View of changing cases' is_automated property"""

    permission_required = "testcases.change_testcase"
    form_class = CaseAutomatedForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.populate()
        return form

    def form_valid(self, form):
        cases = form.cleaned_data["case"]
        is_automated = form.cleaned_data["is_automated"]
        is_automated_proposed = form.cleaned_data["is_automated_proposed"]

        if form.cleaned_data["a"] == "change":
            # FIXME: inconsistent operation updating automated property upon
            #        TestCases. Other place to update property upon TestCase
            #        via Model.save, that will trigger model singal handlers.
            kwargs = {}
            if is_automated is not None:
                kwargs["is_automated"] = is_automated
            if is_automated_proposed is not None:
                kwargs["is_automated_proposed"] = is_automated_proposed
            cases.update(**kwargs)
        return JsonResponse({})

    def form_invalid(self, form):
        return JsonResponseBadRequest({"messages": form_error_messages_to_list(form)}, safe=True)


@permission_required("testcases.add_testcase")
def new(request, template_name="case/new.html"):
    """New testcase"""
    tp = plan_from_request_or_none(request)
    # Initial the form parameters when write new case from plan
    if tp:
        default_form_parameters = {
            "product": tp.product_id,
            "component": tp.component.defer("id").values_list("pk", flat=True),
            "is_automated": "0",
        }
    # Initial the form parameters when write new case directly
    else:
        default_form_parameters = {"is_automated": "0"}

    if request.method == "POST":
        post_data = request.POST
        form = NewCaseForm(post_data)
        if post_data.get("product"):
            form.populate(product_id=post_data["product"])
        else:
            form.populate()

        if form.is_valid():
            new_case = TestCase.create(
                author=request.user,
                values=form.cleaned_data,
                plans=[tp] if tp else None,
            )
            new_case.add_text(
                case_text_version=1,
                author=request.user,
                action=form.cleaned_data["action"],
                effect=form.cleaned_data["effect"],
                setup=form.cleaned_data["setup"],
                breakdown=form.cleaned_data["breakdown"],
            )

            if post_data.get("_continue"):
                url = reverse("case-edit", args=[new_case.pk])
                if tp:
                    url = f"{url}?from_plan={tp.pk}"
                return HttpResponseRedirect(url)

            elif post_data.get("_addanother"):
                form = NewCaseForm(initial=default_form_parameters)
                if tp:
                    form.populate(product_id=tp.product_id)

            elif post_data.get("_returntoplan"):
                if tp:
                    url = reverse("plan-get", args=[tp.pk])
                    return HttpResponseRedirect(f"{url}#reviewcases")
                else:
                    raise Http404

            else:
                # Default destination after case is created
                url = reverse("case-get", args=[new_case.pk])
                if tp:
                    url = f"{url}?from_plan={tp.pk}"
                return HttpResponseRedirect(url)

    # Initial NewCaseForm for submit
    else:
        tp = plan_from_request_or_none(request)
        form = NewCaseForm(initial=default_form_parameters)
        if tp:
            form.populate(product_id=tp.product_id)

    context_data = {"test_plan": tp, "form": form}
    return render(request, template_name, context=context_data)


def get_testcaseplan_sortkey_pk_for_testcases(
    plan: TestPlan, tc_ids: List[int]
) -> Dict[int, Dict[int, int]]:
    """Get each TestCase' sortkey and related TestCasePlan's pk"""
    qs = TestCasePlan.objects.filter(case__in=tc_ids)
    if plan is not None:
        qs = qs.filter(plan__pk=plan.pk)
    qs = qs.values("pk", "sortkey", "case")
    return {
        item["case"]: {"testcaseplan_pk": item["pk"], "sortkey": item["sortkey"]} for item in qs
    }


def calculate_for_testcases(plan: Optional[TestPlan], cases: List[TestCase]) -> List[TestCase]:
    """Calculate extra data for TestCases

    Attach TestCasePlan.sortkey and TestCasePlan.pk.

    :param plan: the TestPlan containing searched TestCases. None means
        ``cases`` are not limited to a specific TestPlan.
    :param cases: a queryset of TestCase.
    :type cases: list[TestCase]
    :return: a list of test cases which are modified by adding extra data.
    """
    tc_ids = [tc.pk for tc in cases]
    extra_data = get_testcaseplan_sortkey_pk_for_testcases(plan, tc_ids)

    for case in cases:
        data = extra_data.get(case.pk)
        if data:
            setattr(case, "cal_sortkey", data["sortkey"])
            setattr(case, "cal_testcaseplan_pk", data["testcaseplan_pk"])
        else:
            setattr(case, "cal_sortkey", None)
            setattr(case, "cal_testcaseplan_pk", None)

    return cases


def get_case_status(template_type):
    """Get part or all TestCaseStatus according to template type"""
    confirmed_status_name = "CONFIRMED"
    if template_type == "case":
        d_status = TestCaseStatus.objects.filter(name=confirmed_status_name)
    elif template_type == "review_case":
        d_status = TestCaseStatus.objects.exclude(name=confirmed_status_name)
    else:
        d_status = TestCaseStatus.objects.all()
    return d_status


def build_cases_search_form(request_data, http_session, populate=None, plan=None):
    """Build search form preparing for quering TestCases"""
    # Intial the plan in plan details page
    if request_data.get("from_plan"):
        SearchForm = CaseFilterForm
    else:
        SearchForm = SearchCaseForm

    # Initial the form and template
    action = request_data.get("a")
    if action in TESTCASE_OPERATION_ACTIONS:
        search_form = SearchForm(request_data)
    else:
        d_status = get_case_status(request_data.get("template_type"))
        d_status_ids = d_status.values_list("pk", flat=True)
        search_form = SearchForm(initial={"case_status": d_status_ids})

    if populate:
        if request_data.get("product"):
            search_form.populate(product_id=request_data["product"])
        elif plan and plan.product_id:
            search_form.populate(product_id=plan.product_id)
        else:
            search_form.populate()

    return search_form


def query_testcases(request_data, plan, search_form):
    """Query TestCases according to the criterias along with REQUEST"""
    # FIXME: search_form is not defined before being used.
    action = request_data.get("a")
    if action in TESTCASE_OPERATION_ACTIONS and search_form.is_valid():
        tcs = TestCase.list(search_form.cleaned_data, plan)
    elif action == "initial":
        d_status = get_case_status(request_data.get("template_type"))
        tcs = TestCase.objects.filter(case_status__in=d_status)
    else:
        tcs = TestCase.objects.none()

    # Search the relationship
    if plan:
        tcs = tcs.filter(plan=plan)

    return tcs


def sort_queried_testcases(request, testcases):
    """Sort querid TestCases according to sort key

    Arguments:
    - request: REQUEST object
    - testcases: object of QuerySet containing queried TestCases
    """
    order_by = request.POST.get("order_by", "create_date")
    asc = bool(request.POST.get("asc", None))
    tcs = apply_order(testcases, order_by, asc)
    # default sorted by sortkey
    tcs = tcs.order_by("testcaseplan__sortkey")
    # Resort the order
    # if sorted by 'sortkey'(foreign key field)
    case_sort_by = request.POST.get("case_sort_by")
    if case_sort_by:
        if case_sort_by not in ["sortkey", "-sortkey"]:
            tcs = tcs.order_by(case_sort_by)
        elif case_sort_by == "sortkey":
            tcs = tcs.order_by("testcaseplan__sortkey")
        else:
            tcs = tcs.order_by("-testcaseplan__sortkey")
    return tcs


def query_testcases_from_request(request_data, http_session, plan=None):
    """Query TestCases according to criterias coming within REQUEST

    :param request_data: the HTTP request data, which could be either
        ``request.GET`` or ``request.POST``.
    :param http_session: the HTTP session object.
    :param plan: a TestPlan object to restrict only those TestCases belongs to
        the TestPlan. Can be None. As you know, query from all TestCases.
    """
    search_form = build_cases_search_form(request_data, http_session)
    return query_testcases(request_data, plan, search_form)


def get_selected_testcases(request):
    """Get selected TestCases from client side

    Arguments:
    - request: REQUEST object.
    """
    request_data = request.POST or request.GET
    pks = [int(pk) for pk in request_data.getlist("case")]
    return TestCase.objects.filter(pk__in=pks)


def get_selected_cases_ids(request):
    """Get cases' IDs to restore the checked status after current operation

    The cases whose ID appears in REQUEST is handled, and they should be
    checked when user sees the page returned after current operation.

    If there is no case argument in REQUEST, check all. This is also the
    default behavior.

    Return values:
    - a list of IDs, which should be checked.
    - empty list, representing select all.
    """
    REQUEST = request.POST
    if REQUEST.get("case"):
        # FIXME: why do not use list comprehension.
        return [int(case_id) for case_id in REQUEST.getlist("case")]
    else:
        return []


def get_tags_from_cases(case_ids, plan_id=None):
    """Get all tags from test cases

    :param case_ids: an iterable object containing test cases' ids
    :type case_ids: iterable[int]
    :param plan_id: the plan id.
    :type plan_id: int or None
    :return: a list containing all found tags with id and name
    :rtype: list[str]
    """
    case_id_list = ", ".join((str(item) for item in case_ids))
    if plan_id:
        sql = sqls.GET_TAGS_FROM_CASES_FROM_PLAN.format(case_id_list if case_id_list else "0")

        rows = SQLExecution(sql, (plan_id,)).rows
    else:
        sql = sqls.GET_TAGS_FROM_CASES.format(case_id_list if case_id_list else "0")

        rows = SQLExecution(sql).rows

    return sorted(rows, key=itemgetter("tag_name"))


def all(request, template_name="case/all.html"):
    """Generate the case list in search case and case zone in plan

    Parameters:
    a: Action
       -- search: Search form submitted.
       -- initial: Initial the case filter
    from_plan: Plan ID
       -- [number]: When the plan ID defined, it will build the case
    page in plan.

    """
    # Intial the plan in plan details page
    tp = plan_from_request_or_none(request)
    search_form = build_cases_search_form(request.POST, request.session, populate=True, plan=tp)
    tcs = query_testcases(request.POST, tp, search_form)
    tcs = sort_queried_testcases(request, tcs)
    total_cases_count = tcs.count()

    # Initial the case ids
    selected_case_ids = get_selected_cases_ids(request)

    # Get the tags own by the cases
    if tp:
        ttags = get_tags_from_cases((case.pk for case in tcs), tp.pk)
    else:
        ttags = get_tags_from_cases((case.pk for case in tcs))

    tcs = tcs.prefetch_related("author", "default_tester", "case_status", "category", "priority")

    # There are several extra information related to each TestCase to be shown
    # also. This step must be the very final one, because the calculation of
    # related data requires related TestCases' IDs, that is the queryset of
    # TestCases should be evaluated in advance.
    tcs = calculate_for_testcases(tp, tcs)

    # generating a query_url with order options
    #
    # FIXME: query_url is always equivlant to None&asc=True whatever what
    # criterias specified in filter form, or just with default filter
    # conditions during loading TestPlan page.
    query_url = remove_from_request_path(request, "order_by")
    asc = bool(request.POST.get("asc", None))
    if asc:
        query_url = remove_from_request_path(query_url, "asc")
    else:
        query_url = "%s&asc=True" % query_url

    # Due to this method serves several sort of search requests, so before
    # rendering the search result, template should be adjusted to a proper one.
    if request.POST.get("from_plan"):
        if request.POST.get("template_type") == "case":
            template_name = "plan/get_cases.html"
        elif request.POST.get("template_type") == "review_case":
            template_name = "plan/get_review_cases.html"

    context_data = {
        "module": MODULE_NAME,
        "test_cases": tcs,
        "test_plan": tp,
        "search_form": search_form,
        "selected_case_ids": selected_case_ids,
        "case_status": TestCaseStatus.objects.all(),
        "priorities": Priority.objects.all(),
        "case_own_tags": ttags,
        "query_url": query_url,
        # Load more is a POST request, so POST parameters are required only.
        # Remember this for loading more cases with the same as criterias.
        "search_criterias": request.body.decode("utf-8"),
        "total_cases_count": total_cases_count,
    }
    return render(request, template_name, context=context_data)


@require_GET
def search_cases(request):
    """Generate the case list in search case and case zone in plan"""
    search_form = SearchCaseForm(request.GET)

    if search_form.is_valid():
        cases = (
            TestCase.list(search_form.cleaned_data)
            .select_related("author", "default_tester", "case_status", "priority", "category")
            .only(
                "pk",
                "summary",
                "author__username",
                "default_tester__username",
                "is_automated",
                "case_status__name",
                "category__name",
                "priority__value",
                "is_automated_proposed",  # 'default_tester__id',
                "create_date",
            )
            .order_by("-create_date")
        )
    else:
        cases = TestCase.objects.none()

    # columnIndexNameMap is required for correct sorting behavior, 5 should be
    # product, but we use run.build.product
    column_names = [
        "",
        "",
        "pk",
        "summary",
        "author__username",
        "default_tester__username",
        "is_automated",
        "case_status__name",
        "category__name",
        "priority__value",
        "create_date",
    ]

    if "sEcho" in request.GET:
        dt = DataTableResult(request.GET, cases, column_names, default_order_key="-pk")
        resp_data = get_template("case/common/json_cases.txt").render(
            dt.get_response_data(), request
        )
        return JsonResponse(json.loads(resp_data))
    else:
        context_data = {
            "module": "testruns",
            "sub_module": "cases",
            "object_list": cases[0:20],
            "search_form": search_form,
            "total_count": cases.count(),
        }
        return render(request, "case/all.html", context=context_data)


class SimpleTestCaseView(TemplateView, data.TestCaseViewDataMixin):
    """Simple read-only TestCase View used in TestPlan page"""

    template_name = "case/get_details.html"

    # NOTES: what permission is proper for this request?
    def get(self, request, case_id):
        self.case_id = case_id
        return super().get(request, case_id)

    def get_case(self):
        cases = TestCase.objects.filter(pk=self.case_id).only("notes")
        cases = list(cases.iterator())
        return cases[0] if cases else None

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        case = self.get_case()
        data["test_case"] = case
        if case is not None:
            data.update(
                {
                    "test_case_text": case.get_text_with_version(),
                    "attachments": case.attachments.only("file_name"),
                    "components": case.component.only("name"),
                    "tags": case.tag.only("name"),
                    "case_comments": self.get_case_comments(case),
                }
            )

        return data


class TestCaseReviewPaneView(SimpleTestCaseView):
    """Used in Reviewing Cases tab in test plan page"""

    template_name = "case/get_details_review.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        testcase = data["test_case"]
        if testcase is not None:
            logs = self.get_case_logs(testcase)
            comments = self.get_case_comments(testcase)
            data.update(
                {
                    "logs": logs,
                    "case_comments": comments,
                }
            )
        return data


class TestCaseCaseRunListPaneView(TemplateView):
    """Display case runs list when expand a plan from case page"""

    template_name = "case/get_case_runs_by_plan.html"

    # FIXME: what permission here?
    def get(self, request, case_id):
        self.case_id = case_id

        plan_id = self.request.GET.get("plan_id", None)
        self.plan_id = int(plan_id) if plan_id is not None else None

        this_cls = TestCaseCaseRunListPaneView
        return super(this_cls, self).get(request, case_id)

    def get_case_runs(self):
        qs = TestCaseRun.objects.filter(case=self.case_id, run__plan=self.plan_id)
        qs = qs.values(
            "pk",
            "case_id",
            "run_id",
            "case_text_version",
            "close_date",
            "sortkey",
            "tested_by__username",
            "assignee__username",
            "run__plan_id",
            "run__summary",
            "case__category__name",
            "case__priority__value",
            "case_run_status__name",
        ).order_by("pk")
        return qs

    def get_comments_count(self, caserun_ids):
        ct = ContentType.objects.get_for_model(TestCaseRun)
        qs = (
            Comment.objects.filter(
                content_type=ct,
                object_pk__in=caserun_ids,
                site_id=settings.SITE_ID,
                is_removed=False,
            )
            .order_by("object_pk")
            .values("object_pk")
            .annotate(comment_count=Count("pk"))
        )
        return {int(item["object_pk"]): item["comment_count"] for item in qs.iterator()}

    def get_context_data(self, **kwargs):
        this_cls = TestCaseCaseRunListPaneView
        data = super(this_cls, self).get_context_data(**kwargs)

        case_runs = self.get_case_runs()

        # Get the number of each caserun's comments, and put the count into
        # comments query result.
        caserun_ids = list(map(itemgetter("pk"), case_runs))
        comments_count = self.get_comments_count(caserun_ids)
        for case_run in case_runs:
            case_run["comments_count"] = comments_count.get(case_run["pk"], 0)

        data.update(
            {
                "case_runs": case_runs,
            }
        )
        return data


class TestCaseSimpleCaseRunView(TemplateView, data.TestCaseRunViewDataMixin):
    """Display case run information in Case Runs tab in case page

    This view only shows notes, comments and logs simply. So, call it simple.
    """

    template_name = "case/get_details_case_case_run.html"

    # what permission here?
    def get(self, request, case_id):
        self.case_id = case_id

        val = request.GET.get("case_run_id")
        if not val:
            return HttpResponseBadRequest("Missing case_run_id in the query string.")
        if val.isdigit():
            self.case_run_id = int(val)
        else:
            return HttpResponseBadRequest(f"Invalid case_run_id {val} which should be an integer.")

        this_cls = TestCaseSimpleCaseRunView
        return super(this_cls, self).get(request, case_id)

    def get_context_data(self, **kwargs):
        this_cls = TestCaseSimpleCaseRunView
        data = super(this_cls, self).get_context_data(**kwargs)

        case_run = get_object_or_404(
            TestCaseRun.objects.only("notes"), case=self.case_id, pk=self.case_run_id
        )
        logs = self.get_caserun_logs(case_run)
        comments = self.get_caserun_comments(case_run)

        data.update(
            {
                "test_caserun": case_run,
                "logs": logs.iterator(),
                "comments": comments.iterator(),
            }
        )
        return data


class TestCaseCaseRunDetailPanelView(
    TemplateView, data.TestCaseViewDataMixin, data.TestCaseRunViewDataMixin
):
    """Display case run detail in run page"""

    template_name = "case/get_details_case_run.html"

    def get(self, request, case_id):
        self.case_id = case_id

        val = request.GET.get("case_run_id")
        if not val:
            return HttpResponseBadRequest("Missing case_run_id in the query string.")
        if val.isdigit():
            self.case_run_id = int(val)
        else:
            return HttpResponseBadRequest(f"Invalid case_run_id {val} which should be an integer.")

        val = request.GET.get("case_text_version")
        if not val:
            return HttpResponseBadRequest("Missing case_text_version in query string.")
        if val.isdigit():
            self.case_text_version = int(val)
        else:
            return HttpResponseBadRequest(
                f"Invalid case_text_version {val} which should be an integer."
            )

        this_cls = TestCaseCaseRunDetailPanelView
        return super(this_cls, self).get(request, case_id)

    def get_context_data(self, **kwargs):
        this_cls = TestCaseCaseRunDetailPanelView
        data = super(this_cls, self).get_context_data(**kwargs)

        case: TestCase = get_object_or_404(TestCase.objects.only("pk"), pk=self.case_id)
        case_run = get_object_or_404(TestCaseRun, pk=self.case_run_id, case=case)

        # Data of TestCase
        test_case_text = case.get_text_with_version(self.case_text_version)

        # Data of TestCaseRun
        caserun_comments = self.get_caserun_comments(case_run)
        caserun_logs = self.get_caserun_logs(case_run)

        caserun_status = TestCaseRunStatus.objects.values("pk", "name")
        caserun_status = caserun_status.order_by("sortkey")
        issues = group_case_issues(
            case_run.case.get_issues()
            .order_by("issue_key")
            .only("issue_key", "tracker__name", "tracker__issue_url_fmt", "case_run__run")
        )
        has_issue_trackers = case_run.run.get_issue_trackers().exists()

        data.update(
            {
                "test_case": case,
                "test_case_text": test_case_text,
                "test_case_run": case_run,
                "comments_count": len(caserun_comments),
                "caserun_comments": caserun_comments,
                "caserun_logs": caserun_logs,
                "test_case_run_status": caserun_status,
                "grouped_case_issues": issues,
                "has_issue_trackers": has_issue_trackers,
                "components": case.component.order_by("name"),
                "tags": case.tag.order_by("name"),
            }
        )

        return data


def get(request, case_id, template_name="case/get.html"):
    """Get the case content"""
    # Get the case
    try:
        tc = TestCase.objects.get(case_id=case_id)
    except ObjectDoesNotExist:
        raise Http404

    # Get the test plans
    tps = tc.plan.select_related("author", "product", "type").all()

    # log
    log_id = str(case_id)
    logs = TCMSLogModel.get_logs_for_model(TestCase, log_id)

    # Get the specific test plan
    plan_id_from_request = request.GET.get("from_plan")
    if plan_id_from_request:
        try:
            tp = tps.get(pk=plan_id_from_request)
        except TestPlan.DoesNotExist:
            return prompt.info(
                request,
                "This case has been removed from the plan, but you can view the case detail",
                reverse("case-get", args=[case_id]),
            )
    else:
        tp = None

    # Get the test case runs
    tcrs = tc.case_run.select_related(
        "run",
        "tested_by",
        "assignee",
        "case__category",
        "case__priority",
        "case_run_status",
    ).all()
    tcrs = tcrs.extra(
        select={
            "num_issue": RawSQL.num_case_run_issues,
        }
    ).order_by("run__plan")
    runs_ordered_by_plan = itertools.groupby(tcrs, attrgetter("run.plan"))
    # FIXME: Just don't know why Django template does not evaluate a generator,
    # and had to evaluate the groupby generator manually like below.
    runs_ordered_by_plan = [(k, list(v)) for k, v in runs_ordered_by_plan]
    case_run_plans = [k for k, v in runs_ordered_by_plan]
    # Get the specific test case run
    if request.GET.get("case_run_id"):
        tcr = tcrs.get(pk=request.GET["case_run_id"])
    else:
        tcr = None
    case_run_plan_id = request.GET.get("case_run_plan_id", None)
    if case_run_plan_id:
        for item in runs_ordered_by_plan:
            if item[0].pk == int(case_run_plan_id):
                case_runs_by_plan = item[1]
                break
            else:
                continue
    else:
        case_runs_by_plan = None

    # Get the case texts
    tc_text = tc.get_text_with_version(request.GET.get("case_text_version"))
    # Switch the templates for different module
    template_types = {
        "case": "case/get_details.html",
        # 'review_case': 'case/get_details_review.html',
        "case_run": "case/get_details_case_run.html",
        # 'case_run_list': 'case/get_case_runs_by_plan.html',
        # 'case_case_run': 'case/get_details_case_case_run.html',
        "execute_case_run": "run/execute_case_run.html",
    }

    if request.GET.get("template_type"):
        template_name = template_types.get(request.GET["template_type"], "case")

    issue_trackers = IssueTracker.get_by_case(tc).only("pk", "name", "validate_regex")

    # Render the page
    context_data = {
        "logs": logs,
        "test_case": tc,
        "test_plan": tp,
        "test_plans": tps,
        "test_case_runs": tcrs,
        "case_run_plans": case_run_plans,
        "test_case_runs_by_plan": case_runs_by_plan,
        "test_case_run": tcr,
        "test_case_text": tc_text,
        "test_case_status": TestCaseStatus.objects.all(),
        "test_case_run_status": TestCaseRunStatus.objects.all(),
        "issue_trackers": issue_trackers,
        "module": request.GET.get("from_plan") and "testplans" or MODULE_NAME,
    }
    return render(request, template_name, context=context_data)


# TODO: better to split this method for TestPlan and TestCase respectively.
# NOTE: if you want to print cases according to case_status, you have to pass
# printable_case_status in the REQUEST. Why to do this rather than using
# case_status is that, Select All causes previous filter criteria is
#       passed via REQUEST, whereas case_status must exist. So, we have to find
#       a way to distinguish them for different purpose, respectively.
@require_POST
def printable(request, template_name="case/printable.html"):
    """Create the printable copy for plan/case"""
    case_pks = request.POST.getlist("case")

    if not case_pks:
        return prompt.info(request, "At least one target is required.")

    repeat = len(case_pks)
    params_sql = ",".join(itertools.repeat("%s", repeat))
    sql = sqls.TC_PRINTABLE_CASE_TEXTS % (params_sql, params_sql)
    tcs = SQLExecution(sql, case_pks * 2).rows

    context_data = {
        "test_cases": tcs,
    }
    return render(request, template_name, context=context_data)


@require_POST
def export(request, template_name="case/export.xml"):
    """Export the plan"""
    case_pks = list(map(int, request.POST.getlist("case")))

    if not case_pks:
        return prompt.info(request, "At least one target is required.")

    context_data = {
        "cases_info": get_exported_cases_and_related_data(case_pks=case_pks),
    }

    response = render(request, template_name, context=context_data)

    timestamp = datetime.datetime.now()
    timestamp_str = "%02i-%02i-%02i" % (timestamp.year, timestamp.month, timestamp.day)
    filename = f"tcms-testcases-{timestamp_str}.xml"
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def update_testcase(request, tc, tc_form):
    """Updating information of specific TestCase

    This is called by views.edit internally. Don't call this directly.

    Arguments:
    - tc: instance of a TestCase being updated
    - tc_form: instance of django.forms.Form, holding validated data.
    """

    # Modify the contents
    fields = [
        "summary",
        "case_status",
        "category",
        "priority",
        "notes",
        "is_automated",
        "is_automated_proposed",
        "script",
        "arguments",
        "extra_link",
        "requirement",
        "alias",
    ]

    for field in fields:
        if getattr(tc, field) != tc_form.cleaned_data[field]:
            tc.log_action(
                request.user,
                field=field,
                original_value=getattr(tc, field) or "",
                new_value=tc_form.cleaned_data[field] or "",
            )
            setattr(tc, field, tc_form.cleaned_data[field])
    try:
        if tc.default_tester != tc_form.cleaned_data["default_tester"]:
            tc.log_action(
                request.user,
                field="default tester",
                original_value=tc.default_tester_id and tc.default_tester,
                new_value=tc_form.cleaned_data["default_tester"],
            )
            tc.default_tester = tc_form.cleaned_data["default_tester"]
    except ObjectDoesNotExist:
        pass
    tc.update_tags(tc_form.cleaned_data.get("tag"))
    try:
        fields_text = ["action", "effect", "setup", "breakdown"]
        latest_text = tc.latest_text()

        for field in fields_text:
            form_cleaned = tc_form.cleaned_data[field]
            if not (getattr(latest_text, field) or form_cleaned):
                continue
            if getattr(latest_text, field) != form_cleaned:
                tc.log_action(
                    request.user,
                    field=field,
                    original_value=getattr(latest_text, field) or "",
                    new_value=form_cleaned or "",
                )
    except ObjectDoesNotExist:
        pass

    # FIXME: Bug here, timedelta from form cleaned data need to convert.
    tc.estimated_time = tc_form.cleaned_data["estimated_time"]
    # IMPORTANT! tc.current_user is an instance attribute,
    # added so that in post_save, current logged-in user info
    # can be accessed.
    # Instance attribute is usually not a desirable solution.
    tc.current_user = request.user
    tc.save()


@permission_required("testcases.change_testcase")
def edit(request, case_id, template_name="case/edit.html"):
    """Edit case detail"""
    try:
        tc = TestCase.objects.select_related().get(case_id=case_id)
    except ObjectDoesNotExist:
        raise Http404

    tp = plan_from_request_or_none(request)

    if request.method == "POST":
        form = EditCaseForm(request.POST)
        if request.POST.get("product"):
            form.populate(product_id=request.POST["product"])
        elif tp:
            form.populate(product_id=tp.product_id)
        else:
            form.populate()

        n_form = CaseNotifyForm(request.POST)

        if form.is_valid() and n_form.is_valid():

            update_testcase(request, tc, form)

            tc.add_text(
                author=request.user,
                action=form.cleaned_data["action"],
                effect=form.cleaned_data["effect"],
                setup=form.cleaned_data["setup"],
                breakdown=form.cleaned_data["breakdown"],
            )

            # Notification
            update_case_email_settings(tc, n_form)

            # Returns
            if request.POST.get("_continue"):
                return HttpResponseRedirect(
                    "{}?from_plan={}".format(
                        reverse("case-edit", args=[case_id]),
                        request.POST.get("from_plan", None),
                    )
                )

            if request.POST.get("_continuenext"):
                if not tp:
                    raise Http404

                # find out test case list which belong to the same
                # classification
                confirm_status_name = "CONFIRMED"
                if tc.case_status.name == confirm_status_name:
                    pk_list = tp.case.filter(case_status__name=confirm_status_name)
                else:
                    pk_list = tp.case.exclude(case_status__name=confirm_status_name)
                pk_list = pk_list.order_by("pk").defer("case_id").values_list("pk", flat=True)

                # Get the previous and next case
                p_tc, n_tc = tc.get_previous_and_next(pk_list=pk_list)
                return HttpResponseRedirect(
                    "{}?from_plan={}".format(
                        reverse(
                            "case-edit",
                            args=[
                                n_tc.pk,
                            ],
                        ),
                        tp.pk,
                    )
                )

            if request.POST.get("_returntoplan"):
                if not tp:
                    raise Http404
                confirm_status_name = "CONFIRMED"
                if tc.case_status.name == confirm_status_name:
                    return HttpResponseRedirect(
                        "{}#testcases".format(
                            reverse(
                                "plan-get",
                                args=[
                                    tp.pk,
                                ],
                            ),
                        )
                    )
                else:
                    return HttpResponseRedirect(
                        "{}#reviewcases".format(
                            reverse(
                                "plan-get",
                                args=[
                                    tp.pk,
                                ],
                            ),
                        )
                    )

            return HttpResponseRedirect(
                "{}?from_plan={}".format(
                    reverse("case-get", args=[case_id]),
                    request.POST.get("from_plan", None),
                )
            )

    else:
        tctxt = tc.latest_text()
        # Notification form initial
        n_form = CaseNotifyForm(
            initial={
                "notify_on_case_update": tc.emailing.notify_on_case_update,
                "notify_on_case_delete": tc.emailing.notify_on_case_delete,
                "author": tc.emailing.auto_to_case_author,
                "default_tester_of_case": tc.emailing.auto_to_case_tester,
                "managers_of_runs": tc.emailing.auto_to_run_manager,
                "default_testers_of_runs": tc.emailing.auto_to_run_tester,
                "assignees_of_case_runs": tc.emailing.auto_to_case_run_assignee,
                "cc_list": CC_LIST_DEFAULT_DELIMITER.join(tc.emailing.get_cc_list()),
            }
        )
        if tc.default_tester_id:
            default_tester = tc.default_tester.email
        else:
            default_tester = None
        form = EditCaseForm(
            initial={
                "summary": tc.summary,
                "default_tester": default_tester,
                "requirement": tc.requirement,
                "is_automated": tc.get_is_automated_form_value(),
                "is_automated_proposed": tc.is_automated_proposed,
                "script": tc.script,
                "arguments": tc.arguments,
                "extra_link": tc.extra_link,
                "alias": tc.alias,
                "case_status": tc.case_status_id,
                "priority": tc.priority_id,
                "product": tc.category.product_id,
                "category": tc.category_id,
                "notes": tc.notes,
                "component": [c.pk for c in tc.component.all()],
                "estimated_time": tc.clear_estimated_time,
                "setup": tctxt.setup,
                "action": tctxt.action,
                "effect": tctxt.effect,
                "breakdown": tctxt.breakdown,
                "tag": ",".join(tc.tag.values_list("name", flat=True)),
            }
        )

        form.populate(product_id=tc.category.product_id)

    context_data = {
        "test_case": tc,
        "test_plan": tp,
        "form": form,
        "notify_form": n_form,
        "module": request.GET.get("from_plan") and "testplans" or MODULE_NAME,
    }
    return render(request, template_name, context=context_data)


@require_GET
def text_history(request, case_id, template_name="case/history.html"):
    """View test plan text history"""
    SUB_MODULE_NAME = "cases"

    tc = get_object_or_404(TestCase, case_id=case_id)
    tp = plan_from_request_or_none(request)
    tctxts = tc.text.values(
        "case_id", "case_text_version", "author__email", "create_date"
    ).order_by("-case_text_version")

    context_data = {
        "module": request.GET.get("from_plan") and "testplans" or MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "testplan": tp,
        "testcase": tc,
        "test_case_texts": tctxts.iterator(),
    }

    try:
        case_text_version = int(request.GET.get("case_text_version"))
        text_to_show = tc.text.filter(case_text_version=case_text_version)
        text_to_show = text_to_show.values("action", "effect", "setup", "breakdown")

        context_data.update(
            {
                "select_case_text_version": case_text_version,
                "text_to_show": text_to_show.iterator(),
            }
        )
    except (TypeError, ValueError):
        # If case_text_version is not a valid number, no text to display for a
        # selected text history
        pass

    return render(request, template_name, context=context_data)


@permission_required("testcases.add_testcase")
def clone(request, template_name="case/clone.html"):
    """Clone one case or multiple case into other plan or plans"""

    SUB_MODULE_NAME = "cases"

    request_data = getattr(request, request.method)

    if "case" not in request_data:
        return prompt.info(request, "At least one case is required.")

    # Do the clone action
    if request.method == "POST":
        clone_form = CloneCaseForm(request.POST)
        clone_form.populate(case_ids=request.POST.getlist("case"))

        if clone_form.is_valid():
            form_data = clone_form.cleaned_data
            copy_case = form_data["copy_case"]
            src_cases = form_data["case"]
            dest_plans = form_data["plan"]
            keep_orig_author = form_data["maintain_case_orignal_author"]
            keep_orig_default_tester = form_data["maintain_case_orignal_default_tester"]

            src_plan = plan_from_request_or_none(request)
            dest_case = None

            src_cases: TestCase
            for src_case in src_cases:
                author = None if keep_orig_author else request.user
                default_tester = None if keep_orig_default_tester else request.user

                if copy_case:
                    dest_case = src_case.clone(
                        dest_plans,
                        author=author,
                        default_tester=default_tester,
                        source_plan=src_plan,
                        copy_attachment=form_data["copy_attachment"],
                        copy_component=form_data["copy_component"],
                        component_initial_owner=request.user,
                    )

                else:
                    dest_case = src_case.transition_to_plans(
                        dest_plans,
                        author=author,
                        default_tester=default_tester,
                        source_plan=src_plan,
                    )

            # Detect the number of items and redirect to correct one
            cases_count = len(src_cases)
            plans_count = len(dest_plans)

            if cases_count == 1 and plans_count == 1:
                url = reverse("case-get", args=[dest_case.pk])
                return HttpResponseRedirect(f"{url}?from_plan={dest_plans[0].pk}")

            if cases_count == 1:
                return HttpResponseRedirect(reverse("case-get", args=[dest_case.pk]))

            if plans_count == 1:
                return HttpResponseRedirect(reverse("plan-get", args=[dest_plans[0].pk]))

            # Otherwise it will prompt to user the clone action is successful.
            return prompt.info(
                request,
                "Test case successful to clone, click following link to return to plans page.",
                reverse("plans-all"),
            )
    else:
        selected_cases = get_selected_testcases(request)
        # Initial the clone case form
        clone_form = CloneCaseForm(
            initial={
                # FIXME: reduce query result size of cases
                "case": selected_cases,
                "copy_case": False,
                "maintain_case_orignal_author": False,
                "maintain_case_orignal_default_tester": False,
                "copy_component": True,
                "copy_attachment": True,
            }
        )
        clone_form.populate(case_ids=selected_cases)

    tp = None
    search_plan_form = SearchPlanForm()

    # Generate search plan form
    if request_data.get("from_plan"):
        tp = TestPlan.objects.get(plan_id=request_data["from_plan"])
        search_plan_form = SearchPlanForm(initial={"product": tp.product_id, "is_active": True})
        search_plan_form.populate(product_id=tp.product_id)

    submit_action = request_data.get("submit", None)
    context_data = {
        "module": request_data.get("from_plan") and "testplans" or MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "test_plan": tp,
        "search_form": search_plan_form,
        "clone_form": clone_form,
        "submit_action": submit_action,
    }
    return render(request, template_name, context=context_data)


@require_GET
def tag_candidates_list_for_removal(request):
    """Remove tags from selected cases in plan page"""
    form = CaseTagForm()
    form.populate(get_selected_testcases(request))
    return HttpResponse(form.as_p())


class AddComponentView(PermissionRequiredMixin, View):
    """Add component view"""

    permission_required = "testcases.add_testcasecomponent"

    def post(self, request):
        form = CaseComponentForm(request.POST)
        form.populate(product_id=request.POST["product"])
        if not form.is_valid():
            return JsonResponseBadRequest(
                {
                    "message": form_error_messages_to_list(form),
                },
                safe=True,
            )

        case_ids = [int(case_id) for case_id in request.POST.getlist("case")]

        # Remove duplicate pair of case and component
        existings = set(
            TestCaseComponent.objects.filter(case__in=case_ids).values_list("case", "component")
        )
        cases = TestCase.objects.filter(pk__in=case_ids).only("pk")
        components_to_add = (
            (case, comp)
            for case in cases
            for comp in form.cleaned_data["o_component"]
            if (case.pk, comp.pk) not in existings
        )

        errors = []
        for case, component in components_to_add:
            try:
                case.add_component(component=component)
            except Exception:
                msg = f"Failed to add component {component} to case {case.pk}"
                logger.exception(msg)
                errors.append(msg)

        if errors:
            return JsonResponseBadRequest({"message": errors})
        else:
            components = ", ".join(c.name for c in form.cleaned_data["o_component"])
            return JsonResponse({"message": f"Succeed to add component(s) {components}."})


class RemoveComponentView(PermissionRequiredMixin, View):
    """Remove component view"""

    permission_required = "testcases.delete_testcasecomponent"

    def post(self, request):
        form = CaseComponentForm(request.POST)
        form.populate()

        if not form.is_valid():
            return JsonResponseBadRequest(
                {
                    "message": form_error_messages_to_list(form),
                }
            )

        errors = []
        case_ids = [int(case_id) for case_id in request.POST.getlist("case")]
        cases = TestCase.objects.filter(pk__in=case_ids).only("pk")
        for case in cases:
            for c in form.cleaned_data["o_component"]:
                try:
                    case.remove_component(component=c)
                except Exception:
                    msg = f"Failed to remove component {c} from case {case.pk}."
                    logger.exception(msg)
                    errors.append(msg)

        if errors:
            return JsonResponseBadRequest({"message": errors}, safe=True)
        else:
            components = ", ".join(c.name for c in form.cleaned_data["o_component"])
            return JsonResponse({"message": f"Succeed to remove component(s) {components}."})


class GetComponentFormView(PermissionRequiredMixin, View):
    """Get component form view"""

    permission_required = "testcases.add_testcasecomponent"

    def post(self, request):
        product_id = request.POST["product"]
        form = CaseComponentForm(
            initial={
                "product": product_id,
                "component": request.POST.getlist("o_component"),
            }
        )
        form.populate(product_id=product_id)
        return HttpResponse(form.as_p())


@require_POST
@permission_required("testcases.add_testcasecomponent")
def category(request):
    """Management test case categories"""
    # FIXME: It will update product/category/component at one time so far.
    # We may disconnect the component from case product in future.
    cas = actions.CategoryActions(request)
    func = getattr(cas, request.POST.get("a", "render_form").lower())
    return func()


class ListCaseAttachmentsView(PermissionRequiredMixin, View):
    """View to list a case' attachments"""

    SUB_MODULE_NAME = "cases"

    permission_required = "testcases.add_testcaseattachment"
    template_name = "case/attachment.html"

    def get(self, request, case_id):
        file_size_limit = settings.MAX_UPLOAD_SIZE
        limit_readable = int(file_size_limit) / 2 ** 20  # Mb

        case = get_object_or_404(TestCase, case_id=case_id)
        plan = plan_from_request_or_none(request)

        context_data = {
            "module": request.GET.get("from_plan") and "testplans" or MODULE_NAME,
            "sub_module": self.SUB_MODULE_NAME,
            "testplan": plan,
            "testcase": case,
            "limit": file_size_limit,
            "limit_readable": str(limit_readable) + "Mb",
        }
        return render(request, self.template_name, context=context_data)


def get_log(request, case_id, template_name="management/get_log.html"):
    """Get the case log"""
    tc = get_object_or_404(TestCase, case_id=case_id)

    context_data = {"object": tc}
    return render(template_name, context=context_data)


class CasesIssueActionBaseView(PermissionRequiredMixin, FormView):
    """Base view class of actions on cases' issues"""

    raise_exception = True

    def get_form(self, form_class=None):
        post_data = self.request.POST.copy()
        post_data["case"] = self.kwargs["case_id"]
        return self.form_class(post_data)

    def do(self, form):
        """Do the real action on the issues

        :param form: the form provided by FormView.
        :type form: :class:`django.forms.Form`
        :return: a Django response object if something is wrong, otherwise None is returned.
        :rtype: :class:`JsonResponseBadRequest` or None
        """
        raise NotImplementedError("Must be implemented in subclass.")

    def form_valid(self, form):
        response = self.do(form)

        if response is not None:
            return response

        case = form.cleaned_data["case"]
        context = {
            "test_case": case,
            "issue_trackers": IssueTracker.get_by_case(case),
        }
        return JsonResponse(
            {"html": render_to_string("case/get_issues.html", context, self.request)}
        )

    def form_invalid(self, form):
        return JsonResponseBadRequest({"message": form_error_messages_to_list(form)})


class AddIssueToCases(CasesIssueActionBaseView):
    """Add an issue to a test cases"""

    form_class = CaseIssueForm
    permission_required = "issuetracker.add_issue"

    def do(self, form):
        tracker = form.cleaned_data["tracker"]
        if not tracker.enabled:
            return JsonResponseBadRequest(
                {"message": f'Issue tracker "{tracker.name}" is not enabled.'}
            )
        case = form.cleaned_data["case"]
        try:
            case.add_issue(
                issue_key=form.cleaned_data["issue_key"],
                issue_tracker=tracker,
                summary=form.cleaned_data["summary"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as e:
            return JsonResponseBadRequest({"message": e.messages})
        except Exception as e:
            msg = "Failed to add issue {} to case {}. Error reported: {}".format(
                form.cleaned_data["issue_key"], case.pk, str(e)
            )
            logger.exception(msg)
            return JsonResponseBadRequest({"message": msg})


class DeleteIssueFromCases(CasesIssueActionBaseView):
    """Delete an issue from cases"""

    form_class = CaseRemoveIssueForm
    permission_required = "issuetracker.delete_issue"

    def do(self, form):
        case = form.cleaned_data["case"]
        try:
            case.remove_issue(form.cleaned_data["issue_key"], form.cleaned_data["case_run"])
        except (TypeError, ValueError) as e:
            return JsonResponseBadRequest({"message": str(e)})


class CasePlansOperationView(PermissionRequiredMixin, View):
    """Base view class for operations on case and plan relationship"""

    def post(self, request, case_id):
        form = CasePlansForm({"case": case_id, "plan": request.POST.getlist("plan")})

        if not form.is_valid():
            return JsonResponseBadRequest({"message": form_error_messages_to_list(form)})

        self.operate(form)

        case = form.cleaned_data["case"]
        return JsonResponse(
            {
                "html": render_to_string(
                    "case/get_plan.html",
                    request=request,
                    context={
                        "test_case": case,
                        "test_plans": case.plan.select_related(
                            "author", "type", "product"
                        ).order_by("pk"),
                    },
                )
            }
        )

    def operate(self, cleaned_data):
        raise NotImplementedError()


class AddCaseToPlansView(CasePlansOperationView):
    """Add case to plans"""

    permission_required = "testcases.add_testcaseplan"

    def operate(self, form):
        case = form.cleaned_data["case"]
        for item in form.cleaned_data["plan"]:
            item.add_case(case)


class RemoveCaseFromPlansView(CasePlansOperationView):
    """Remove case from plans"""

    permission_required = "testcases.change_testcaseplan"

    def operate(self, form):
        case = form.cleaned_data["case"]
        for item in form.cleaned_data["plan"]:
            case.remove_plan(item)


@require_GET
def plan(request, case_id):
    """Add and remove plan in plan tab"""
    tc = get_object_or_404(TestCase, case_id=case_id)

    if request.GET.get("a"):
        # Search the plans from database
        if not request.GET.getlist("plan_id"):
            return render(
                request,
                "case/get_plan.html",
                context={
                    "message": "The case must specific one plan at least for some action",
                },
            )

        plan_ids = request.GET.getlist("plan_id")
        tps = TestPlan.objects.filter(pk__in=plan_ids)

        if not tps:
            return render(
                request,
                "case/get_plan.html",
                context={
                    "testplans": tps,
                    "message": f'None of plan IDs {", ".join(plan_ids)} exist.',
                },
            )

        # Add case plan action
        # if request.GET['a'] == 'add':
        #     if not request.user.has_perm('testcases.add_testcaseplan'):
        #         context_data = {
        #             'test_case': tc,
        #             'test_plans': tps,
        #             'message': 'Permission denied',
        #         }
        #         return render(request, 'case/get_plan.html', context=context_data)
        #
        #     for tp in tps:
        #         tc.add_to_plan(tp)

        # Remove case plan action
        if request.GET["a"] == "remove":
            if not request.user.has_perm("testcases.change_testcaseplan"):
                return render(
                    request,
                    "case/get_plan.html",
                    context={
                        "test_case": tc,
                        "test_plans": tps,
                        "message": "Permission denied",
                    },
                )

            for tp in tps:
                tc.remove_plan(tp)

    return render(
        request,
        "case/get_plan.html",
        context={
            "test_case": tc,
            "test_plans": tc.plan.select_related("author", "type", "product"),
        },
    )


@require_GET
def simple_subtotal_by_status(request: HttpRequest) -> HttpResponse:
    plan_ids = [int(item) for item in request.GET.getlist("plan")] or None
    return JsonResponse(TestCase.subtotal_by_status(plan_ids))

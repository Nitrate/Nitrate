# -*- coding: utf-8 -*-

import datetime
import functools
import itertools
import json
import logging
import operator
import time
import urllib
from operator import attrgetter, itemgetter

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.urls import reverse
from django.utils.encoding import smart_str
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.generic import FormView, RedirectView
from django.views.generic.base import TemplateView, View
from django_comments.models import Comment

from tcms.comments.models import add_comment
from tcms.core.raw_sql import RawSQL
from tcms.core.responses import JsonResponseBadRequest
from tcms.core.tcms_router import connection
from tcms.core.utils import (
    DataTableResult,
    clean_request,
    form_error_messages_to_list,
    format_timedelta,
)
from tcms.core.views import prompt
from tcms.issuetracker.models import Issue, IssueTracker
from tcms.issuetracker.services import find_service
from tcms.management.models import Priority, TCMSEnvGroup, TestTag
from tcms.testcases.models import TestCase, TestCasePlan, TestCaseStatus
from tcms.testcases.views import get_selected_testcases
from tcms.testplans.models import TestPlan
from tcms.testruns.data import TestCaseRunDataMixin, stats_case_runs_status
from tcms.testruns.forms import (
    ChangeRunEnvValueForm,
    CommentCaseRunsForm,
    EditRunForm,
    MulitpleRunsCloneForm,
    NewRunForm,
    PlanFilterRunForm,
    RunAndEnvValueForm,
    RunCloneForm,
    SearchRunForm,
)
from tcms.testruns.helpers.serializer import TCR2File
from tcms.testruns.models import TCMSEnvRunValueMap, TestCaseRun, TestCaseRunStatus, TestRun

MODULE_NAME = "testruns"

logger = logging.getLogger(__name__)


@require_POST
@csrf_protect
@permission_required("testruns.add_testrun")
def new(request, template_name="run/new.html"):
    """Display the create test run page."""

    SUB_MODULE_NAME = "new_run"

    # If from_plan does not exist will redirect to plans for select a plan
    if not request.POST.get("from_plan"):
        return HttpResponseRedirect(reverse("plans-all"))

    plan_id = request.POST.get("from_plan")
    # Case is required by a test run
    if not request.POST.get("case"):
        return prompt.info(
            request,
            "At least one case is required by a run.",
            reverse("plan-get", args=[plan_id]),
        )

    # Ready to write cases to test plan
    confirm_status = TestCaseStatus.get("CONFIRMED")
    tcs = get_selected_testcases(request)
    # FIXME: optimize this query, only get necessary columns, not all fields
    # are necessary
    tp = TestPlan.objects.select_related().get(plan_id=plan_id)
    tcrs = TestCaseRun.objects.filter(case_run_id__in=request.POST.getlist("case_run_id"))

    num_unconfirmed_cases = tcs.exclude(case_status=confirm_status).count()
    estimated_time = datetime.timedelta(seconds=0)

    tcs_values = (
        tcs.select_related("author", "case_status", "category", "priority")
        .only(
            "case_id",
            "summary",
            "create_date",
            "estimated_time",
            "author__email",
            "case_status__name",
            "priority__value",
            "category__name",
        )
        .order_by("case_id")
    )

    if request.POST.get("POSTING_TO_CREATE"):
        form = NewRunForm(request.POST)
        if request.POST.get("product"):
            form.populate(product_id=request.POST["product"])
        else:
            form.populate(product_id=tp.product_id)

        if form.is_valid():
            # Process the data in form.cleaned_data
            default_tester = form.cleaned_data["default_tester"]

            tr = TestRun.objects.create(
                product_version=form.cleaned_data["product_version"],
                plan_text_version=tp.latest_text() and tp.latest_text().plan_text_version or 0,
                stop_date=None,
                summary=form.cleaned_data.get("summary"),
                notes=form.cleaned_data.get("notes"),
                plan=tp,
                build=form.cleaned_data["build"],
                manager=form.cleaned_data["manager"],
                default_tester=default_tester,
                estimated_time=form.cleaned_data["estimated_time"],
                auto_update_run_status=form.cleaned_data["auto_update_run_status"],
            )

            keep_status = form.cleaned_data["keep_status"]
            keep_assign = form.cleaned_data["keep_assignee"]

            try:
                assignee_tester = User.objects.get(username=default_tester)
            except ObjectDoesNotExist:
                assignee_tester = None

            loop = 1

            # not reserve assignee and status, assignee will default set to
            # default_tester
            if not keep_assign and not keep_status:
                for case in form.cleaned_data["case"]:
                    try:
                        tcp = TestCasePlan.objects.get(plan=tp, case=case)
                        sortkey = tcp.sortkey
                    except ObjectDoesNotExist:
                        sortkey = loop * 10

                    tr.add_case_run(case=case, sortkey=sortkey, assignee=assignee_tester)
                    loop += 1

            # Add case to the run
            for tcr in tcrs:
                if keep_status and keep_assign:
                    tr.add_case_run(
                        case=tcr.case,
                        assignee=tcr.assignee,
                        case_run_status=tcr.case_run_status,
                        sortkey=tcr.sortkey or loop * 10,
                    )
                    loop += 1
                elif keep_status and not keep_assign:
                    tr.add_case_run(
                        case=tcr.case,
                        case_run_status=tcr.case_run_status,
                        sortkey=tcr.sortkey or loop * 10,
                    )
                    loop += 1
                elif keep_assign and not keep_status:
                    tr.add_case_run(
                        case=tcr.case,
                        assignee=tcr.assignee,
                        sortkey=tcr.sortkey or loop * 10,
                    )
                    loop += 1

            # Write the values into tcms_env_run_value_map table
            env_property_id_set = set(request.POST.getlist("env_property_id"))
            if env_property_id_set:
                args = list()
                for property_id in env_property_id_set:
                    checkbox_name = "select_property_id_%s" % property_id
                    select_name = "select_property_value_%s" % property_id
                    checked = request.POST.getlist(checkbox_name)
                    if checked:
                        env_values = request.POST.getlist(select_name)
                        if not env_values:
                            continue

                        if len(env_values) != len(checked):
                            raise ValueError("Invalid number of env values.")

                        for value_id in env_values:
                            args.append(TCMSEnvRunValueMap(run=tr, value_id=value_id))

                TCMSEnvRunValueMap.objects.bulk_create(args)

            return HttpResponseRedirect(reverse("run-get", args=[tr.run_id]))

    else:
        estimated_time = functools.reduce(operator.add, (tc.estimated_time for tc in tcs_values))
        form = NewRunForm(
            initial={
                "summary": "Test run for {} on {}".format(
                    tp.name,
                    tp.env_group.all() and tp.env_group.all()[0] or "Unknown environment",
                ),
                "estimated_time": format_timedelta(estimated_time),
                "manager": tp.author.email,
                "default_tester": request.user.email,
                "product": tp.product_id,
                "product_version": tp.product_version_id,
            }
        )
        form.populate(product_id=tp.product_id)

    # FIXME: pagination cases within Create New Run page.
    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "from_plan": plan_id,
        "test_plan": tp,
        "test_cases": tcs_values,
        "form": form,
        "num_unconfirmed_cases": num_unconfirmed_cases,
        "run_estimated_time": estimated_time,
    }
    return render(request, template_name, context=context_data)


@permission_required("testruns.delete_testrun")
def delete(request, run_id):
    """Delete the test run

    - Maybe will be not use again

    """
    try:
        tr = TestRun.objects.select_related("manager", "plan__author").get(run_id=run_id)
    except ObjectDoesNotExist:
        raise Http404

    if not tr.belong_to(request.user):
        return prompt.info(request, "Permission denied - The run is not belong to you.")

    if request.GET.get("sure", "no") == "no":
        run_delete_url = reverse("run-delete", args=[run_id])
        return HttpResponse(
            "<script>"
            "if (confirm('Are you sure you want to delete this run %s?\\n\\n"
            "Click OK to delete or cancel to come back'))"
            "{ window.location.href='%s?sure=yes' }"
            "else { history.go(-1) }"
            "</script>" % (run_id, run_delete_url)
        )
    elif request.GET.get("sure") == "yes":
        try:
            plan_id = tr.plan_id
            tr.env_value.clear()
            tr.case_run.all().delete()
            tr.delete()
            return HttpResponseRedirect(reverse("plan-get", args=[plan_id]))
        except Exception:
            return prompt.info(request, "Delete failed.")
    else:
        return prompt.info(request, "Nothing yet")


@require_GET
def all(request):
    """Read the test runs from database and display them."""
    SUB_MODULE_NAME = "runs"

    query_result = len(request.GET) > 0

    if list(request.GET.items()):
        search_form = SearchRunForm(request.GET)
        if request.GET.get("product"):
            search_form.populate(product_id=request.GET["product"])
        else:
            search_form.populate()

        search_form.is_valid()
    else:
        search_form = SearchRunForm()

    return render(
        request,
        "run/all.html",
        context={
            "module": MODULE_NAME,
            "sub_module": SUB_MODULE_NAME,
            "query_result": query_result,
            "search_form": search_form,
        },
    )


@require_GET
def search_runs(request):
    """Search test runs"""
    search_form = SearchRunForm(request.GET)
    product_id = request.GET.get("product")
    search_form.populate(product_id=int(product_id) if product_id else None)

    runs = TestRun.objects.none()

    if search_form.is_valid():
        runs = (
            TestRun.list(search_form.cleaned_data)
            .select_related("manager", "default_tester", "build", "plan", "build__product")
            .only(
                "run_id",
                "summary",
                "manager__username",
                "default_tester__id",
                "default_tester__username",
                "plan__name",
                "build__product__name",
                "stop_date",
                "product_version__value",
            )
            .extra(select={"cases_count": RawSQL.total_num_caseruns})
        )

    column_names = [
        "",
        "run_id",
        "summary",
        "manager__username",
        "default_tester__username",
        "build__product__name",
        "product_version__value",
        "env_groups",
        "cases_count",
        "stop_date",
        "completed",
    ]

    dt = DataTableResult(request.GET, runs, column_names, default_order_key="-pk")
    response_data = dt.get_response_data()
    calculate_associated_data(response_data["querySet"])

    if "sEcho" in request.GET:
        resp_data = get_template("run/common/json_runs.txt").render(response_data, request)
        return JsonResponse(json.loads(resp_data))
    else:
        return render(
            request,
            "run/all.html",
            context={
                "module": MODULE_NAME,
                "sub_module": "runs",
                "object_list": response_data["querySet"],
                "search_form": search_form,
                "total_count": runs.count(),
            },
        )


def run_queryset_from_querystring(querystring):
    """Setup a run queryset from a querystring.

    A querystring is used in several places in front-end
    to query a list of runs.
    """
    # 'name=alice&age=20' => {'name': 'alice', 'age': ''}
    filter_keywords = dict(k.split("=") for k in querystring.split("&"))
    # get rid of empty values and several other noisy names
    if "page_num" in filter_keywords:
        filter_keywords.pop("page_num")
    if "page_size" in filter_keywords:
        filter_keywords.pop("page_size")

    filter_keywords = {str(k): v for k, v in filter_keywords.items() if v.strip()}

    trs = TestRun.objects.filter(**filter_keywords)
    return trs


def magic_convert(queryset, key_name, value_name):
    return {row[key_name]: row[value_name] for row in queryset}


def load_runs_of_one_plan(request, plan_id, template_name="plan/common/json_plan_runs.txt"):
    """A dedicated view to return a set of runs of a plan

    This view is used in a plan detail page, for the contained testrun tab. It
    replaces the original solution, with a paginated resultset in return,
    serves as a performance healing. Also, in order for user to locate the
    data, it accepts field lookup parameters collected from the filter panel
    in the UI.
    """
    column_names = [
        "",
        "run_id",
        "summary",
        "manager__username",
        "default_tester__username",
        "start_date",
        "build__name",
        "stop_date",
        "total_num_caseruns",
        "failure_caseruns_percent",
        "successful_caseruns_percent",
    ]

    tp = TestPlan.objects.get(plan_id=plan_id)
    form = PlanFilterRunForm(request.GET)

    if form.is_valid():
        queryset = tp.run.filter(**form.cleaned_data)
        queryset = queryset.select_related("build", "manager", "default_tester").order_by("-pk")

        dt = DataTableResult(request.GET, queryset, column_names)
        response_data = dt.get_response_data()
        searched_runs = response_data["querySet"]

        # Get associated statistics data
        run_filters = {f"run__{key}": value for key, value in form.cleaned_data.items()}

        qs = (
            TestCaseRun.objects.filter(
                case_run_status=TestCaseRunStatus.name_to_id("FAILED"), **run_filters
            )
            .values("run", "case_run_status")
            .annotate(count=Count("pk"))
            .order_by("run", "case_run_status")
        )
        failure_subtotal = magic_convert(qs, key_name="run", value_name="count")

        qs = (
            TestCaseRun.objects.filter(
                case_run_status=TestCaseRunStatus.name_to_id("PASSED"), **run_filters
            )
            .values("run", "case_run_status")
            .annotate(count=Count("pk"))
            .order_by("run", "case_run_status")
        )
        success_subtotal = magic_convert(qs, key_name="run", value_name="count")

        qs = (
            TestCaseRun.objects.filter(**run_filters)
            .values("run")
            .annotate(count=Count("case"))
            .order_by("run")
        )
        cases_subtotal = magic_convert(qs, key_name="run", value_name="count")

        for run in searched_runs:
            run_id = run.pk
            cases_count = cases_subtotal.get(run_id, 0)
            if cases_count:
                failure_percent = failure_subtotal.get(run_id, 0) * 1.0 / cases_count * 100
                success_percent = success_subtotal.get(run_id, 0) * 1.0 / cases_count * 100
            else:
                failure_percent = success_percent = 0
            run.nitrate_stats = {
                "cases": cases_count,
                "failure_percent": failure_percent,
                "success_percent": success_percent,
            }
    else:
        response_data = {
            "sEcho": int(request.GET.get("sEcho", 0)),
            "iTotalRecords": 0,
            "iTotalDisplayRecords": 0,
            "querySet": TestRun.objects.none(),
        }

    resp_data = get_template(template_name).render(response_data, request)
    return JsonResponse(json.loads(resp_data))


def calculate_associated_data(runs: QuerySet) -> None:
    """Calculate associated data and set to each run in place

    The associated data include:

    * completed progress of each test run
    * the environment of each test run
    """
    run_ids = [run.pk for run in runs]
    qs = (
        TestCaseRun.objects.filter(
            case_run_status=TestCaseRunStatus.name_to_id("FAILED"), run__in=run_ids
        )
        .values("run", "case_run_status")
        .annotate(count=Count("pk"))
        .order_by("run", "case_run_status")
    )
    failure_subtotal = magic_convert(qs, key_name="run", value_name="count")

    completed_status_ids = TestCaseRunStatus.completed_status_ids()
    qs = (
        TestCaseRun.objects.filter(case_run_status__in=completed_status_ids, run__in=run_ids)
        .values("run", "case_run_status")
        .annotate(count=Count("pk"))
        .order_by("run", "case_run_status")
    )
    completed_subtotal = {
        run_id: sum((item["count"] for item in stats_rows))
        for run_id, stats_rows in itertools.groupby(qs.iterator(), key=itemgetter("run"))
    }

    qs = (
        TestCaseRun.objects.filter(run__in=run_ids)
        .values("run")
        .annotate(cases_count=Count("case"))
    )
    cases_subtotal = magic_convert(qs, key_name="run", value_name="cases_count")

    # Relative env groups to runs
    result = TCMSEnvGroup.objects.filter(plans__run__in=run_ids).values("plans__run", "name")
    runs_env_groups = {item["plans__run"]: item["name"] for item in result}

    for run in runs:
        run_id = run.pk
        cases_count = cases_subtotal.get(run_id, 0)
        if cases_count:
            completed_percent = completed_subtotal.get(run_id, 0) * 1.0 / cases_count * 100
            failure_percent = failure_subtotal.get(run_id, 0) * 1.0 / cases_count * 100
        else:
            completed_percent = failure_percent = 0

        run.associated_data = {
            "stats": {
                "cases": cases_count,
                "completed_percent": completed_percent,
                "failure_percent": failure_percent,
            },
            "env_group": runs_env_groups.get(run_id),
        }


def open_run_get_case_runs(request, run):
    """Prepare for case runs list in a TestRun page

    This is an internal method. Do not call this directly.
    """
    tcrs = run.case_run.select_related("run", "case", "case__priority", "case__category")
    tcrs = tcrs.only(
        "run__run_id",
        "run__plan",
        "case_run_status",
        "assignee",
        "tested_by",
        "case_text_version",
        "sortkey",
        "case__summary",
        "case__is_automated_proposed",
        "case__is_automated",
        "case__priority",
        "case__category__name",
    )
    # Continue to search the case runs with conditions
    # 4. case runs preparing for render case runs table
    tcrs = tcrs.filter(**clean_request(request))
    order_by = request.GET.get("order_by")
    if order_by:
        tcrs = tcrs.order_by(order_by)
    else:
        tcrs = tcrs.order_by("sortkey", "pk")
    return tcrs


def open_run_get_comments_subtotal(case_run_ids):
    ct = ContentType.objects.get_for_model(TestCaseRun)
    qs = Comment.objects.filter(
        content_type=ct,
        site_id=settings.SITE_ID,
        object_pk__in=case_run_ids,
        is_removed=False,
    )
    qs = qs.values("object_pk").annotate(comment_count=Count("pk"))
    qs = qs.order_by("object_pk").iterator()
    return {int(row["object_pk"]): row["comment_count"] for row in qs}


def open_run_get_users(case_runs):
    tester_ids = set()
    assignee_ids = set()
    for case_run in case_runs:
        if case_run.tested_by_id:
            tester_ids.add(case_run.tested_by_id)
        if case_run.assignee_id:
            assignee_ids.add(case_run.assignee_id)
    testers = User.objects.filter(pk__in=tester_ids).values_list("pk", "username")
    assignees = User.objects.filter(pk__in=assignee_ids).values_list("pk", "username")
    return (dict(testers.iterator()), dict(assignees.iterator()))


class RunStatisticsView(TemplateView):
    """A simple view for refreshing the statistics by case run status in a test run page"""

    template_name = "run/status_statistics.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data()
        run_id = self.kwargs["run_id"]
        run: TestRun = get_object_or_404(TestRun.objects.only("pk"), pk=run_id)
        data.update(
            {
                "test_run": run,
                "status_stats": stats_case_runs_status([run_id])[run_id],
                "test_case_run_issues_count": run.get_issues_count(),
            }
        )
        return data


@require_GET
def get(request, run_id, template_name="run/get.html"):
    """Display testrun's detail"""

    SUB_MODULE_NAME = "runs"

    # Get the test run
    tr: TestRun = get_object_or_404(TestRun.objects.select_related(), pk=run_id)

    # Get the test case runs belong to the run
    # 2. get test run's all case runs
    tcrs = open_run_get_case_runs(request, tr)

    case_run_statuss = TestCaseRunStatus.objects.only("pk", "name").order_by("pk")

    # Count the status
    # 3. calculate number of case runs of each status
    status_stats_result = stats_case_runs_status([run_id])[run_id]

    # Get the test case run bugs summary
    # 6. get the number of bugs of this run
    tcr_issues_count = tr.get_issues_count()

    # Get tag list of testcases
    # 7. get tags
    # Get the list of testcases belong to the run
    tcs = [tcr.case_id for tcr in tcrs]
    ttags = TestTag.objects.filter(cases__in=tcs).values_list("name", flat=True)
    ttags = list(set(ttags.iterator()))
    ttags.sort()

    def walk_case_runs():
        """Walking case runs for helping rendering case runs table"""
        priorities = Priority.get_values()
        testers, assignees = open_run_get_users(tcrs)
        comments_subtotal = open_run_get_comments_subtotal([cr.pk for cr in tcrs])
        case_run_status = TestCaseRunStatus.as_dict()
        issues_subtotal = tr.subtotal_issues_by_case_run()

        for case_run in tcrs:
            yield (
                case_run,
                testers.get(case_run.tested_by_id, None),
                assignees.get(case_run.assignee_id, None),
                priorities.get(case_run.case.priority_id),
                case_run_status[case_run.case_run_status_id],
                comments_subtotal.get(case_run.pk, 0),
                issues_subtotal.get(case_run.pk, 0),
            )

    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "test_run": tr,
        "from_plan": request.GET.get("from_plan", False),
        "test_case_runs": walk_case_runs(),
        "test_case_runs_count": len(tcrs),
        "status_stats": status_stats_result,
        "test_case_run_issues_count": tcr_issues_count,
        "test_case_run_status": case_run_statuss,
        "priorities": Priority.objects.all(),
        "case_own_tags": ttags,
        "issue_trackers": tr.get_issue_trackers(),
    }
    return render(request, template_name, context=context_data)


@permission_required("testruns.change_testrun")
def edit(request, run_id, template_name="run/edit.html"):
    """Edit test plan view"""
    # Define the default sub module
    SUB_MODULE_NAME = "runs"

    try:
        tr = TestRun.objects.select_related().get(run_id=run_id)
    except ObjectDoesNotExist:
        raise Http404

    # If the form is submitted
    if request.method == "POST":
        form = EditRunForm(request.POST)
        if request.POST.get("product"):
            form.populate(product_id=request.POST.get("product"))
        else:
            form.populate(product_id=tr.plan.product_id)

        # FIXME: Error handler
        if form.is_valid():
            # detect if auto_update_run_status field is changed by user when
            # edit testrun.
            auto_update_changed = False
            if tr.auto_update_run_status != form.cleaned_data["auto_update_run_status"]:
                auto_update_changed = True

            # detect if finished field is changed by user when edit testrun.
            finish_field_changed = False
            if tr.stop_date and not form.cleaned_data["finished"]:
                finish_field_changed = True
                is_finish = False
            elif not tr.stop_date and form.cleaned_data["finished"]:
                finish_field_changed = True
                is_finish = True

            tr.summary = form.cleaned_data["summary"]
            # Permission hack
            if tr.manager == request.user or tr.plan.author == request.user:
                tr.manager = form.cleaned_data["manager"]
            tr.default_tester = form.cleaned_data["default_tester"]
            tr.build = form.cleaned_data["build"]
            tr.product_version = form.cleaned_data["product_version"]
            tr.notes = form.cleaned_data["notes"]
            tr.estimated_time = form.cleaned_data["estimated_time"]
            tr.auto_update_run_status = form.cleaned_data["auto_update_run_status"]
            tr.save()
            if auto_update_changed:
                tr.update_completion_status(is_auto_updated=True)
            if finish_field_changed:
                tr.update_completion_status(is_auto_updated=False, is_finish=is_finish)
            return HttpResponseRedirect(reverse("run-get", args=[run_id]))
    else:
        # Generate a blank form
        form = EditRunForm(
            initial={
                "summary": tr.summary,
                "manager": tr.manager.email,
                "default_tester": (tr.default_tester and tr.default_tester.email or None),
                "product": tr.build.product_id,
                "product_version": tr.product_version_id,
                "build": tr.build_id,
                "notes": tr.notes,
                "finished": tr.stop_date,
                "estimated_time": tr.clear_estimated_time,
                "auto_update_run_status": tr.auto_update_run_status,
            }
        )
        form.populate(product_id=tr.build.product_id)

    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "test_run": tr,
        "form": form,
    }
    return render(request, template_name, context=context_data)


@permission_required("testruns.change_testcaserun")
def execute(request, run_id, template_name="run/execute.html"):
    """Execute test run"""
    return get(request, run_id, template_name)


class TestRunReportView(TemplateView, TestCaseRunDataMixin):
    """Test Run report"""

    template_name = "run/report.html"

    def get_context_data(self, **kwargs):
        """Generate report for specific TestRun

        There are four data source to generate this report.
        1. TestRun
        2. Test case runs included in the TestRun
        3. Comments associated with each test case run
        4. Statistics
        5. Issues
        """
        run_id = int(self.kwargs["run_id"])
        run = TestRun.objects.select_related("manager", "plan").get(pk=run_id)
        case_runs = (
            TestCaseRun.objects.filter(run=run)
            .select_related("case_run_status", "case", "tested_by", "case__category")
            .only(
                "close_date",
                "case_run_status__name",
                "case__category__name",
                "case__summary",
                "case__is_automated",
                "case__is_automated_proposed",
                "tested_by__username",
            )
        )
        comments = self.get_caseruns_comments(run.pk)

        run_stats = stats_case_runs_status([run.pk])[run.pk]

        run_issues = Issue.objects.filter(case_run__run=run_id).select_related("tracker")

        by_case_run_pk = attrgetter("case_run.pk")
        issues_by_case_run = {
            case_run_id: [(item.issue_key, item.get_absolute_url()) for item in issues]
            for case_run_id, issues in itertools.groupby(
                sorted(run_issues, key=by_case_run_pk), by_case_run_pk
            )
        }

        manual_count = 0
        automated_count = 0
        manual_automated_count = 0

        case_run: TestCaseRun
        for case_run in case_runs:
            case_run.display_issues = issues_by_case_run.get(case_run.pk, ())
            user_comments = comments.get(case_run.pk, [])
            case_run.user_comments = user_comments

            is_automated = case_run.case.is_automated
            if is_automated == 1:
                automated_count += 1
            elif is_automated == 0:
                manual_count += 1
            else:
                manual_automated_count += 1

        display_issues_by_tracker = [
            (
                tracker.name,
                find_service(tracker).make_issues_display_url(
                    sorted(map(attrgetter("issue_key"), issues))
                ),
            )
            for tracker, issues in itertools.groupby(
                sorted(run_issues, key=attrgetter("tracker.pk")), attrgetter("tracker")
            )
        ]
        display_issues_by_tracker.sort(key=itemgetter(0))

        run_issues_display_info = [
            (issue.issue_key, issue.get_absolute_url()) for issue in run_issues
        ]

        context = super().get_context_data(**kwargs)
        context.update(
            {
                "test_run": run,
                "test_case_runs": case_runs,
                "display_issues_by_tracker": display_issues_by_tracker,
                "test_case_runs_count": len(case_runs),
                "test_case_run_issues": run_issues_display_info,
                "test_case_run_mode_stats": {
                    "manual": manual_count,
                    "automated": automated_count,
                    "manual_automated": manual_automated_count,
                },
                "test_run_stats": run_stats,
            }
        )

        return context


@require_POST
def new_run_with_caseruns(request, run_id, template_name="run/clone.html"):
    """Clone cases from filter caserun"""

    SUB_MODULE_NAME = "runs"
    tr = get_object_or_404(TestRun, run_id=run_id)

    if request.POST.get("case_run"):
        tcrs = tr.case_run.filter(pk__in=request.POST.getlist("case_run"))
    else:
        tcrs = []

    if not tcrs:
        return prompt.info(request, "At least one case is required by a run")
    estimated_time = functools.reduce(operator.add, [tcr.case.estimated_time for tcr in tcrs])

    if not request.POST.get("submit"):
        form = RunCloneForm(
            initial={
                "summary": tr.summary,
                "notes": tr.notes,
                "manager": tr.manager.email,
                "product": tr.plan.product_id,
                "product_version": tr.product_version_id,
                "build": tr.build_id,
                "default_tester": tr.default_tester_id and tr.default_tester.email or "",
                "estimated_time": format_timedelta(estimated_time),
                "use_newest_case_text": True,
            }
        )

        form.populate(product_id=tr.plan.product_id)

        context_data = {
            "module": MODULE_NAME,
            "sub_module": SUB_MODULE_NAME,
            "clone_form": form,
            "test_run": tr,
            "cases_run": tcrs,
        }
        return render(request, template_name, context=context_data)


@require_http_methods(["GET", "POST"])
def clone(request, template_name="run/clone.html"):
    """Clone test run to another build"""

    SUB_MODULE_NAME = "runs"

    trs = TestRun.objects.select_related()

    req_data = request.GET or request.POST

    filter_str = req_data.get("filter_str")
    if filter_str:
        trs = run_queryset_from_querystring(filter_str)
    else:
        trs = trs.filter(pk__in=req_data.getlist("run"))

    if not trs:
        return prompt.info(request, "At least one run is required")

    # Generate the clone run page for one run
    if trs.count() == 1 and not req_data.get("submit"):
        tr = trs[0]
        tcrs = tr.case_run.all()
        form = RunCloneForm(
            initial={
                "summary": tr.summary,
                "notes": tr.notes,
                "manager": tr.manager.email,
                "product": tr.plan.product_id,
                "product_version": tr.product_version_id,
                "build": tr.build_id,
                "default_tester": tr.default_tester_id and tr.default_tester.email or "",
                "use_newest_case_text": True,
            }
        )
        form.populate(product_id=tr.plan.product_id)

        context_data = {
            "module": MODULE_NAME,
            "sub_module": SUB_MODULE_NAME,
            "clone_form": form,
            "test_run": tr,
            "cases_run": tcrs,
        }
        return render(request, template_name, context=context_data)

    # Process multiple runs clone page
    template_name = "run/clone_multiple.html"

    if request.method == "POST":
        form = MulitpleRunsCloneForm(request.POST)
        form.populate(trs=trs, product_id=request.POST.get("product"))
        if form.is_valid():
            for tr in trs:
                n_tr = TestRun.objects.create(
                    product_version=form.cleaned_data["product_version"],
                    plan_text_version=tr.plan_text_version,
                    summary=tr.summary,
                    notes=tr.notes,
                    estimated_time=tr.estimated_time,
                    plan=tr.plan,
                    build=form.cleaned_data["build"],
                    manager=(
                        form.cleaned_data["update_manager"]
                        and form.cleaned_data["manager"]
                        or tr.manager
                    ),
                    default_tester=(
                        form.cleaned_data["update_default_tester"]
                        and form.cleaned_data["default_tester"]
                        or tr.default_tester
                    ),
                )

                for tcr in tr.case_run.all():
                    if form.cleaned_data["update_case_text"]:
                        text_versions = list(tcr.get_text_versions())
                        if text_versions:
                            case_text_version = text_versions[-1]
                        else:
                            case_text_version = tcr.case_text_version
                    else:
                        case_text_version = tcr.case_text_version

                    n_tr.add_case_run(
                        case=tcr.case,
                        assignee=tcr.assignee,
                        case_text_version=case_text_version,
                        build=form.cleaned_data["build"],
                        notes=tcr.notes,
                        sortkey=tcr.sortkey,
                    )

                for env_value in tr.env_value.all():
                    n_tr.add_env_value(env_value)

                if form.cleaned_data["clone_cc"]:
                    for cc in tr.cc.all():
                        n_tr.add_cc(user=cc)

                if form.cleaned_data["clone_tag"]:
                    for tag in tr.tag.all():
                        n_tr.add_tag(tag=tag)

            if len(trs) == 1:
                return HttpResponseRedirect(reverse("run-get", args=[n_tr.pk]))

            params = {
                "product": form.cleaned_data["product"].pk,
                "product_version": form.cleaned_data["product_version"].pk,
                "build": form.cleaned_data["build"].pk,
            }

            return HttpResponseRedirect(
                "{}?{}".format(reverse("runs-all"), urllib.parse.urlencode(params, True))
            )
    else:
        form = MulitpleRunsCloneForm(
            initial={
                "run": trs.values_list("pk", flat=True),
                "manager": request.user,
                "default_tester": request.user,
                "assignee": request.user,
                "update_manager": False,
                "update_default_tester": True,
                "update_assignee": True,
                "update_case_text": True,
                "clone_cc": True,
                "clone_tag": True,
            }
        )
        form.populate(trs=trs)

    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "clone_form": form,
    }
    return render(request, template_name, context=context_data)


@require_POST
def order_case(request, run_id):
    """Resort case with new order"""
    # Current we should rewrite all of cases belong to the plan.
    # Because the cases sortkey in database is chaos,
    # Most of them are None.
    get_object_or_404(TestRun, run_id=run_id)

    if "case_run" not in request.POST:
        return prompt.info(
            request,
            "At least one case is required by re-oder in run.",
            reverse("run-get", args=[run_id]),
        )

    case_run_ids = request.POST.getlist("case_run")
    sql = "UPDATE test_case_runs SET sortkey = %s WHERE test_case_runs.case_run_id = %s"
    # sort key begin with 10, end with length*10, step 10.
    # e.g.
    # case_run_ids = [10334, 10294, 10315, 10443]
    #                      |      |      |      |
    #          sort key -> 10     20     30     40
    # then zip case_run_ids and new_sort_keys to pairs
    # e.g.
    #    sort_key, case_run_id
    #         (10, 10334)
    #         (20, 10294)
    #         (30, 10315)
    #         (40, 10443)
    new_sort_keys = range(10, (len(case_run_ids) + 1) * 10, 10)
    key_id_pairs = zip(new_sort_keys, (int(pk) for pk in case_run_ids))
    with transaction.atomic():
        for key_id_pair in key_id_pairs:
            cursor = connection.writer_cursor
            cursor.execute(sql, key_id_pair)

    return HttpResponseRedirect(reverse("run-get", args=[run_id]))


class ChangeRunStatusView(PermissionRequiredMixin, View):
    """View to change a run status"""

    permission_required = "testruns.change_testrun"

    def get(self, request, run_id):
        is_finish = request.GET.get("finished") == "1"
        tr = get_object_or_404(TestRun, run_id=run_id)
        tr.update_completion_status(is_auto_updated=False, is_finish=is_finish)
        return HttpResponseRedirect(reverse("run-get", args=[run_id]))


class RemoveCaseRunView(PermissionRequiredMixin, View):
    """View to remove case run from a test run"""

    permission_required = "testruns.delete_testcaserun"

    def post(self, request, run_id):
        case_run_ids = []
        for item in request.POST.getlist("case_run"):
            try:
                case_run_ids.append(int(item))
            except (ValueError, TypeError):
                logger.warning(
                    "Ignore case run id %s to remove it from run %s, "
                    "because %s is not an integer.",
                    item,
                    run_id,
                    item,
                )

        # If no case run to remove, no further operation is required, just
        # return back to run page immediately.
        if not case_run_ids:
            return HttpResponseRedirect(reverse("run-get", args=[run_id]))

        run = get_object_or_404(TestRun.objects.only("pk"), pk=run_id)

        # Restrict to delete those case runs that belongs to run
        TestCaseRun.objects.filter(run_id=run.pk, pk__in=case_run_ids).delete()

        caseruns_exist = TestCaseRun.objects.filter(run_id=run.pk).exists()
        if caseruns_exist:
            redirect_to = "run-get"
        else:
            redirect_to = "add-cases-to-run"

        return HttpResponseRedirect(reverse(redirect_to, args=[run_id]))


class AddCasesToRunView(PermissionRequiredMixin, View):
    """Add cases to a TestRun"""

    template_name = "run/assign_case.html"
    permission_required = "testruns.add_testcaserun"

    def post(self, request, run_id):
        # Selected cases' ids to add to run
        ncs_id = request.POST.getlist("case")
        if not ncs_id:
            return prompt.info(
                request,
                "At least one case is required by a run.",
                reverse("add-cases-to-run", args=[run_id]),
            )

        try:
            ncs_id = [int(item) for item in ncs_id]
        except (ValueError, TypeError):
            return prompt.info(
                request,
                "At least one case id is invalid.",
                reverse("add-cases-to-run", args=[run_id]),
            )

        try:
            qs = TestRun.objects.select_related("plan").only("plan__plan_id")
            tr = qs.get(run_id=run_id)
        except ObjectDoesNotExist:
            raise Http404

        etcrs_id = tr.case_run.values_list("case", flat=True)

        # avoid add cases that are already in current run with pk run_id
        ncs_id = set(ncs_id) - set(etcrs_id)

        tp = tr.plan
        tcs = tr.plan.case.filter(case_status__name="CONFIRMED")
        tcs = tcs.select_related("default_tester").only("default_tester__id", "estimated_time")
        ncs = tcs.filter(case_id__in=ncs_id)

        estimated_time = functools.reduce(operator.add, (nc.estimated_time for nc in ncs))
        tr.estimated_time = tr.estimated_time + estimated_time
        tr.save(update_fields=["estimated_time"])

        if request.POST.get("_use_plan_sortkey"):
            case_pks = (case.pk for case in ncs)
            qs = TestCasePlan.objects.filter(plan=tp, case__in=case_pks).values("case", "sortkey")
            sortkeys_in_plan = {row["case"]: row["sortkey"] for row in qs.iterator()}
            for nc in ncs:
                sortkey = sortkeys_in_plan.get(nc.pk, 0)
                tr.add_case_run(case=nc, sortkey=sortkey)
        else:
            for nc in ncs:
                tr.add_case_run(case=nc)

        return HttpResponseRedirect(reverse("run-get", args=[tr.run_id]))

    def get(self, request, run_id):
        # information about TestRun, used in the page header
        tr = (
            TestRun.objects.select_related("plan", "manager", "build")
            .only("plan", "plan__name", "manager__email", "build__name")
            .get(run_id=run_id)
        )

        # select all CONFIRMED cases from the TestPlan that is a parent
        # of this particular TestRun

        confirmed_status = TestCaseStatus.objects.get(name="CONFIRMED")
        confirmed_cases = (
            TestCase.objects.filter(plan=tr.plan, case_status=confirmed_status)
            .values(
                "case_id",
                "summary",
                "create_date",
                "category__name",
                "priority__value",
                "author__username",
            )
            .order_by("pk")
        )

        # also grab a list of all TestCase IDs which are already present in the
        # current TestRun so we can mark them as disabled and not allow them to
        # be selected
        etcrs_id = TestCaseRun.objects.filter(run=run_id).values_list("case", flat=True)

        data = {
            "test_run": tr,
            "confirmed_cases": confirmed_cases,
            "confirmed_cases_count": len(confirmed_cases),
            "test_case_runs_count": len(etcrs_id),
            "exist_case_run_ids": etcrs_id,
        }

        return render(request, self.template_name, context=data)


@require_GET
def cc(request, run_id):
    """Add or remove cc from a test run"""

    tr = get_object_or_404(TestRun, run_id=run_id)
    do = request.GET.get("do")
    username_or_email = request.GET.get("user")
    context_data = {"test_run": tr, "is_ajax": True}

    if do:
        if not username_or_email:
            context_data["message"] = "User name or email is required by this operation"
        else:
            try:
                user = User.objects.get(Q(username=username_or_email) | Q(email=username_or_email))
            except ObjectDoesNotExist:
                context_data["message"] = "The user you typed does not exist in database"
            else:
                if do == "add":
                    tr.add_cc(user=user)

                if do == "remove":
                    tr.remove_cc(user=user)

    return render(request, "run/get_cc.html", context=context_data)


@require_POST
def update_case_run_text(request, run_id):
    """Update the IDLE cases to newest text"""

    tr = get_object_or_404(TestRun, run_id=run_id)

    if request.POST.get("case_run"):
        tcrs = tr.case_run.filter(pk__in=request.POST.getlist("case_run"))
    else:
        tcrs = tr.case_run.all()

    tcrs = tcrs.filter(case_run_status__name="IDLE")

    count = 0
    updated_tcrs = ""
    for tcr in tcrs:
        lctv = tcr.latest_text().case_text_version
        if tcr.case_text_version != lctv:
            count += 1
            updated_tcrs += "<li>{}: {} -> {}</li>".format(
                tcr.case.summary, tcr.case_text_version, lctv
            )
            tcr.case_text_version = lctv
            tcr.save()

    return prompt.info(
        request,
        f"<p>{count} case run(s) succeed to update, following is the list:</p>"
        f"<ul>{updated_tcrs}</ul>",
        reverse("run-get", args=[run_id]),
    )


@require_GET
def export(request, run_id):
    timestamp_str = time.strftime("%Y-%m-%d")
    case_runs = request.GET.getlist("case_run")
    format = request.GET.get("format", "csv")
    # Export selected case runs
    if case_runs:
        tcrs = TestCaseRun.objects.filter(case_run_id__in=case_runs)
    # Export all case runs
    else:
        tcrs = TestCaseRun.objects.filter(run=run_id)
    response = HttpResponse()
    writer = TCR2File(tcrs)
    if format == "csv":
        writer.write_to_csv(response)
        filename = f"tcms-testcase-runs-{timestamp_str}.csv"
    else:
        writer.write_to_xml(response)
        filename = f"tcms-testcase-runs-{timestamp_str}.xml"
    response["Content-Disposition"] = f"attachment; filename={filename}"

    return response


class AddEnvValueToRunView(PermissionRequiredMixin, FormView):
    """Add env value to test runs"""

    form_class = RunAndEnvValueForm
    permission_required = "testruns.add_tcmsenvrunvaluemap"
    raise_exception = True

    def form_valid(self, form):
        for run in form.cleaned_data["runs"]:
            run.add_env_value(form.cleaned_data["env_value"])

        fragment = render(
            self.request,
            "run/get_environment.html",
            context={"test_run": form.cleaned_data["runs"][0], "is_ajax": True},
        )
        return JsonResponse({"fragment": smart_str(fragment.content)})

    def form_invalid(self, form):
        return JsonResponseBadRequest({"message": form_error_messages_to_list(form.errors)})


class DeleteRunEnvValueView(PermissionRequiredMixin, FormView):
    """Delete a test run's env value"""

    form_class = RunAndEnvValueForm
    permission_required = "testruns.delete_tcmsenvrunvaluemap"
    raise_exception = True

    def form_valid(self, form):
        for run in form.cleaned_data["runs"]:
            run.remove_env_value(form.cleaned_data["env_value"])
        return JsonResponse({})

    def form_invalid(self, form):
        return JsonResponseBadRequest({"message": form_error_messages_to_list(form.errors)})


class ChangeRunEnvValueView(PermissionRequiredMixin, FormView):
    """Change a test run's env value"""

    form_class = ChangeRunEnvValueForm
    permission_required = "testruns.change_tcmsenvrunvaluemap"
    raise_exception = True

    def form_valid(self, form):
        for run in form.cleaned_data["runs"]:
            run.remove_env_value(form.cleaned_data["old_env_value"])
            run.add_env_value(form.cleaned_data["new_env_value"])
        return JsonResponse({})

    def form_invalid(self, form):
        return JsonResponseBadRequest({"message": form_error_messages_to_list(form.errors)})


class FileIssueForCaseRun(RedirectView):
    """Construct an issue report URL and redirect to it"""

    def get_redirect_url(self, *args, **kwargs):
        case_run_id = self.kwargs["case_run_id"]
        tracker_id = int(self.request.GET["issueTrackers"])
        case_run = get_object_or_404(TestCaseRun, pk=case_run_id)
        bz_model = IssueTracker.objects.get(pk=tracker_id)
        return find_service(bz_model).make_issue_report_url(case_run)


@require_POST
def comment_case_runs(request):
    """Add comment to one or more case runs at a time."""
    form = CommentCaseRunsForm(request.POST)
    if not form.is_valid():
        return JsonResponseBadRequest({"message": form_error_messages_to_list(form)})
    add_comment(
        request.user,
        "testruns.testcaserun",
        [cr.pk for cr in form.cleaned_data["run"]],
        form.cleaned_data["comment"],
        request.META.get("REMOTE_ADDR"),
    )
    return JsonResponse({})

# -*- coding: utf-8 -*-

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView, View
from django_comments.models import Comment

from tcms.core.db import workaround_single_value_for_in_clause
from tcms.issuetracker.models import Issue
from tcms.management.models import Priority, Product
from tcms.report import data as stats
from tcms.report.data import (
    CustomDetailsReportData,
    CustomReportData,
    TestingReportByCasePriorityData,
    TestingReportByCaseRunTesterData,
    TestingReportByPlanBuildData,
    TestingReportByPlanBuildDetailData,
    TestingReportByPlanTagsData,
    TestingReportByPlanTagsDetailData,
    TestingReportCaseRunsData,
    overview_view_get_running_runs_count,
)
from tcms.report.forms import CustomSearchForm, TestingReportCaseRunsListForm, TestingReportForm
from tcms.search.views import fmt_queries, remove_from_request_path
from tcms.testruns.models import TestCaseRun, TestCaseRunStatus

from .forms import CustomSearchDetailsForm

MODULE_NAME = "report"

# To cache report view for 10 minutes.
# FIXME: this value is chosen in a very short thinking, not evaluated
# enough. Choose a proper one in the future.
REPORT_VIEW_CACHE_DURATION = 0  # 60 * 10


def overall(request):
    """Overall of products report"""
    products = {item["pk"]: item["name"] for item in Product.objects.values("pk", "name")}
    plans_count = stats.subtotal_plans(by="product")
    runs_count = stats.subtotal_test_runs(by="plan__product")
    cases_count = stats.subtotal_cases(by="plan__product")

    def generate_product_stats():
        for product_id, product_name in products.items():
            yield (
                product_id,
                product_name,
                plans_count.get(product_id, 0),
                runs_count.get(product_id, 0),
                cases_count.get(product_id, 0),
            )

    context_data = {
        "module": MODULE_NAME,
        "sub_module": "overall",
        "products": generate_product_stats(),
    }
    return render(request, "report/list.html", context=context_data)


@cache_page(REPORT_VIEW_CACHE_DURATION)
def overview(request, product_id, template_name="report/overview.html"):
    """Product for a product"""
    try:
        product = Product.objects.only("name").get(pk=product_id)
    except Product.DoesNotExist as error:
        raise Http404(error)

    runs_count = overview_view_get_running_runs_count(product.pk)
    caserun_status_count = stats.subtotal_case_run_status(
        filter_={"case_runs__run__plan__product": product.pk}
    )

    context_data = {
        "module": MODULE_NAME,
        "SUB_MODULE_NAME": "overview",
        "product": product,
        "runs_count": runs_count,
        "case_run_count": caserun_status_count,
    }
    return render(request, template_name, context=context_data)


class ProductVersionReport(TemplateView):
    submodule_name = "version"
    template_name = "report/version.html"

    @method_decorator(cache_page(REPORT_VIEW_CACHE_DURATION))
    def get(self, request, product_id):
        try:
            self.product = Product.objects.only("name").get(pk=product_id)

            version_id = request.GET.get("version_id")
            if version_id is not None:
                qs = self.product.version.only("value")
                self.selected_version = qs.get(pk=int(version_id))
        except (TypeError, ValueError, ObjectDoesNotExist) as error:
            raise Http404(error)

        return super().get(request, product_id)

    def get_context_data(self, **kwargs):
        versions = self.product.version.only("product", "value")
        product_id = self.product.pk

        plans_subtotal = stats.subtotal_plans(filter_={"product": product_id}, by="product_version")

        running_runs_subtotal = stats.subtotal_test_runs(
            filter_={
                "plan__product": product_id,
                "stop_date__isnull": True,
            },
            by="plan__product_version",
        )

        finished_runs_subtotal = stats.subtotal_test_runs(
            filter_={
                "plan__product": product_id,
                "stop_date__isnull": False,
            },
            by="plan__product_version",
        )

        cases_subtotal = stats.subtotal_cases(
            filter_={"plan__product": product_id}, by="plan__product_version"
        )

        case_runs_subtotal = stats.subtotal_case_runs(
            filter_={"run__plan__product": product_id}, by="run__plan__product_version"
        )

        finished_case_runs_subtotal = stats.subtotal_case_runs(
            filter_={
                "run__plan__product": product_id,
                "case_run_status__name__in": TestCaseRunStatus.complete_status_names,
            },
            by="run__plan__product_version",
        )

        failed_case_runs_subtotal = stats.subtotal_case_runs(
            filter_={
                "run__plan__product": product_id,
                "case_run_status__name": "FAILED",
            },
            by="run__plan__product_version",
        )

        for version in versions:
            vid = version.pk
            version.plans_count = plans_subtotal.get(vid, 0)
            version.running_runs_count = running_runs_subtotal.get(vid, 0)
            version.finished_runs_count = finished_runs_subtotal.get(vid, 0)
            version.cases_count = cases_subtotal.get(vid, 0)
            version.failed_case_runs_count = failed_case_runs_subtotal.get(vid, 0)

            m = finished_case_runs_subtotal.get(vid, 0)
            n = case_runs_subtotal.get(vid, 0)
            if m and n:
                version.case_run_percent = round(m * 100.0 / n, 1)
            else:
                version.case_run_percent = 0.0

        case_runs_status_subtotal = None
        selected_version = getattr(self, "selected_version", None)
        if selected_version is not None:
            case_runs_status_subtotal = stats.subtotal_case_run_status(
                filter_={
                    "case_runs__run__plan__product": product_id,
                    "case_runs__run__plan__product_version": selected_version,
                }
            )

        data = super().get_context_data(**kwargs)
        data.update(
            {
                "module": MODULE_NAME,
                "SUB_MODULE_NAME": "version",
                "product": self.product,
                "versions": versions,
                "version": selected_version,
                "case_runs_status_subtotal": case_runs_status_subtotal,
            }
        )

        return data


class ProductBuildReport(TemplateView):
    submodule_name = "build"
    template_name = "report/build.html"

    @method_decorator(cache_page(REPORT_VIEW_CACHE_DURATION))
    def get(self, request, product_id):
        try:
            self.product = Product.objects.only("name").get(pk=product_id)

            build_id = request.GET.get("build_id")
            if build_id is not None:
                qs = self.product.build.only("name")
                self.selected_build = qs.get(pk=int(build_id))
        except (TypeError, ValueError, ObjectDoesNotExist) as error:
            raise Http404(error)

        return super().get(request, product_id)

    def get_context_data(self, **kwargs):
        builds = self.product.build.only("product", "name")

        pid = self.product.pk

        builds_total_runs = stats.subtotal_test_runs(filter_={"build__product": pid}, by="build")

        builds_finished_runs = stats.subtotal_test_runs(
            filter_={"build__product": pid, "stop_date__isnull": False}, by="build"
        )

        builds_finished_caseruns = stats.subtotal_case_runs(
            filter_={
                "run__build__product": pid,
                "case_run_status__name__in": TestCaseRunStatus.complete_status_names,
            },
            by="run__build",
        )

        builds_caseruns = stats.subtotal_case_runs(
            filter_={"run__build__product": pid}, by="run__build"
        )

        builds_failed_caseruns = stats.subtotal_case_runs(
            filter_={
                "run__build__product": pid,
                "case_run_status__name": "FAILED",
            },
            by="run__build",
        )

        for build in builds:
            bid = build.pk
            build.total_runs = builds_total_runs.get(bid, 0)
            build.finished_runs = builds_finished_runs.get(bid, 0)
            build.failed_case_run_count = builds_failed_caseruns.get(bid, 0)

            n = builds_finished_caseruns.get(bid, 0)
            m = builds_caseruns.get(bid, 0)
            if n and m:
                build.finished_case_run_percent = round(n * 100.0 / m, 1)
            else:
                build.finished_case_run_percent = 0.0

        case_runs_status_subtotal = None
        selected_build = getattr(self, "selected_build", None)
        if selected_build is not None:
            case_runs_status_subtotal = stats.subtotal_case_run_status(
                filter_={
                    "case_runs__run__build__product": pid,
                    "case_runs__run__build": selected_build.pk,
                }
            )

        data = super().get_context_data(**kwargs)
        data.update(
            {
                "module": MODULE_NAME,
                "SUB_MODULE_NAME": "build",
                "product": self.product,
                "builds": builds,
                "build": selected_build,
                "case_runs_status_subtotal": case_runs_status_subtotal,
            }
        )

        return data


class ProductComponentReport(TemplateView):
    submodule_name = "component"
    template_name = "report/component.html"

    @method_decorator(cache_page(REPORT_VIEW_CACHE_DURATION))
    def get(self, request, product_id):
        try:
            self.product = Product.objects.only("name").get(pk=product_id)

            component_id = request.GET.get("component_id")
            if component_id is not None:
                qs = self.product.component.only("name")
                self.selected_component = qs.get(pk=int(component_id))
        except (TypeError, ValueError, Product.DoesNotExist) as error:
            raise Http404(error)

        return super().get(request, product_id)

    def get_context_data(self, **kwargs):
        components = self.product.component.select_related("product")
        components = components.only("name", "product__name")

        pid = self.product.pk

        subtotal_case_runs = stats.subtotal_case_runs(
            {"case__component__product": pid}, by="case__component"
        )

        failed_case_runs_count = stats.subtotal_case_runs(
            {"case__component__product": pid, "case_run_status__name": "FAILED"},
            by="case__component",
        )

        finished_case_runs_count = stats.subtotal_case_runs(
            {
                "case__component__product": pid,
                "case_run_status__name__in": TestCaseRunStatus.complete_status_names,
            },
            by="case__component",
        )

        for component in components:
            cid = component.pk
            component.case_runs_count = subtotal_case_runs.get(cid, 0)
            component.failed_case_run_count = failed_case_runs_count.get(cid, 0)

            n = finished_case_runs_count.get(cid, 0)
            m = subtotal_case_runs.get(cid, 0)
            if n and m:
                component.finished_case_run_percent = round(n * 100.0 / m, 1)
            else:
                component.finished_case_run_percent = 0

        # To show detail statistics upon case run status if user clicks a
        # component
        case_runs_status_subtotal = None
        selected_component = getattr(self, "selected_component", None)
        if selected_component is not None:
            case_runs_status_subtotal = stats.subtotal_case_run_status(
                {"case_runs__case__component": selected_component.pk}
            )

        data = super().get_context_data(**kwargs)
        data.update(
            {
                "module": MODULE_NAME,
                "SUB_MODULE_NAME": self.submodule_name,
                "product": self.product,
                "components": components,
                "component": selected_component,
                "case_runs_status_subtotal": case_runs_status_subtotal,
            }
        )

        return data


class CustomReport(TemplateView):
    submodule_name = "custom_search"
    template_name = "report/custom_search.html"
    form_class = CustomSearchForm
    data_class = CustomReportData

    @method_decorator(cache_page(REPORT_VIEW_CACHE_DURATION))
    def get(self, request):
        return super().get(request)

    def _get_search_form(self):
        req = self.request.GET
        form = self.form_class(req)
        form.populate(product_id=req.get("product"))
        return form

    def _do_search(self):
        return self.request.GET.get("a", "").lower() == "search"

    def _report_data_context(self):
        form = self._get_search_form()
        context = {"form": form}

        if not form.is_valid():
            context.update({"builds": ()})
            return context

        _data = self.data_class(form)
        self._data = _data

        builds = _data._get_builds()
        build_ids = [build.pk for build in builds]

        # TODO: remove this after upgrading MySQL-python to 1.2.5
        build_ids = workaround_single_value_for_in_clause(build_ids)

        if build_ids:
            # Summary header data
            runs_subtotal = _data.runs_subtotal()
            plans_subtotal = _data.plans_subtotal()
            case_runs_subtotal = _data.case_runs_subtotal()
            isautomated_subtotal = _data.cases_isautomated_subtotal()

            # Staus matrix used to render progress bar for each build
            case_runs_status_matrix = _data.status_matrix()

            # FIXME: this would raise KeyError once status names are modified
            # to other ones.
            passed_id = TestCaseRunStatus.name_to_id("PASSED")
            failed_id = TestCaseRunStatus.name_to_id("FAILED")

            for build in builds:
                bid = build.pk
                build.runs_count = runs_subtotal.get(bid, 0)
                build.plans_count = plans_subtotal.get(bid, 0)
                build.case_runs_count = case_runs_subtotal.get(bid, 0)

                status_subtotal = case_runs_status_matrix.get(bid, {})
                passed_count = status_subtotal.get(passed_id, 0)
                failed_count = status_subtotal.get(failed_id, 0)

                c = case_runs_subtotal.get(bid, 0)

                if c:
                    build.passed_case_runs_percent = passed_count * 100.0 / c
                    build.failed_case_runs_percent = failed_count * 100.0 / c
                else:
                    build.passed_case_runs_percent = 0.0
                    build.failed_case_runs_percent = 0.0

                build.passed_case_runs_count = passed_count
                build.failed_case_runs_count = failed_count
                build.case_runs_count = c

            context.update(
                {
                    # method invocation.
                    "total_runs_count": runs_subtotal.total,
                    "total_plans_count": plans_subtotal.total,
                    "total_count": isautomated_subtotal.total,
                    "manual_count": isautomated_subtotal.get(0, 0),
                    "auto_count": isautomated_subtotal.get(1, 0),
                    "both_count": isautomated_subtotal.get(2, 0),
                }
            )

        context.update({"builds": builds})
        return context

    def _initial_context(self):
        return {
            "form": self.__class__.form_class(),
            "builds": (),
        }

    def _get_report_data_context(self):
        if self._do_search():
            return self._report_data_context()
        else:
            return self._initial_context()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data.update(self._get_report_data_context())
        data.update(
            {
                "module": MODULE_NAME,
                "sub_module": self.submodule_name,
            }
        )
        return data


class CustomDetailReport(CustomReport):
    """Custom detail report

    Reuse CustomReport._search_context to get build and its summary statistics
    """

    template_name = "report/custom_details.html"
    form_class = CustomSearchDetailsForm
    data_class = CustomDetailsReportData

    def _get_report_data_context(self):
        """Override to generate report by disabling check of argument a"""
        return self._report_data_context()

    def walk_matrix_row_by_row(self, matrix_dataset):
        status_total_line = None
        if None in matrix_dataset:
            status_total_line = matrix_dataset[None]
            del matrix_dataset[None]

        prev_plan = None
        # TODO: replace this with collections.OrderedDict after
        # upgrading to Python 2.7
        ordered_plans = sorted(matrix_dataset.items(), key=lambda item: item[0].pk)
        for plan, runs in ordered_plans:
            plan_runs_count = len(runs)
            # TODO: and also this line
            ordered_runs = sorted(runs.items(), key=lambda item: item[0].pk)
            for run, status_subtotal in ordered_runs:
                if plan == prev_plan:
                    yield None, run, status_subtotal
                else:
                    yield (plan, plan_runs_count), run, status_subtotal
                    prev_plan = plan

        # Finally, yield the total line for rendering the complete report
        if status_total_line is not None:
            yield None, None, status_total_line

    def read_case_runs(self, build_ids, status_ids):
        """Generator for reading case runs and related objects"""

        return (
            TestCaseRun.objects.filter(run__build__in=build_ids, case_run_status_id__in=status_ids)
            .select_related("run", "case", "case__category", "tested_by")
            .prefetch_related(
                Prefetch(
                    "comments",
                    queryset=Comment.objects.select_related("user").only(
                        "pk", "comment", "object_pk", "user__username", "submit_date"
                    ),
                ),
                Prefetch(
                    "issues",
                    queryset=Issue.objects.select_related("tracker").only(
                        "pk", "tracker__issue_url_fmt", "case_run"
                    ),
                ),
            )
            .only(
                "run",
                "case__summary",
                "case__category__name",
                "tested_by__username",
                "close_date",
            )
            .order_by("case")
        )

    def _report_data_context(self):
        data = {}
        form = self._get_search_form()

        if form.is_valid():
            summary_header_data = super()._report_data_context()
            data.update(summary_header_data)

            build_ids = [build.pk for build in data["builds"]]
            # TODO: remove this after upgrading MySQL-python to 1.2.5
            build_ids = tuple(workaround_single_value_for_in_clause(build_ids))

            status_matrix = self.walk_matrix_row_by_row(
                self._data.generate_status_matrix(build_ids)
            )

            # TODO: remove this after upgrading MySQL-python to 1.2.5
            status_ids = workaround_single_value_for_in_clause(
                (TestCaseRunStatus.name_to_id("FAILED"),)
            )
            failed_case_runs = self.read_case_runs(build_ids, status_ids)
            # TODO: remove this after upgrading MySQL-python to 1.2.5
            status_ids = workaround_single_value_for_in_clause(
                (TestCaseRunStatus.name_to_id("BLOCKED"),)
            )
            blocked_case_runs = self.read_case_runs(build_ids, status_ids)

            data.update(
                {
                    "status_matrix": status_matrix,
                    "failed_case_runs": failed_case_runs,
                    "blocked_case_runs": blocked_case_runs,
                }
            )
        else:
            data["report_errors"] = form.errors

        data["form"] = form
        return data


class TestingReportBase(TemplateView):
    """Base class for each type of report"""

    form_class = TestingReportForm

    @method_decorator(cache_page(REPORT_VIEW_CACHE_DURATION))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def _get_form(self, data=None):
        product_id = self.request.GET.get("r_product")
        if data is not None:
            form = self.form_class(data)
        else:
            form = self.form_class()
        form.populate(product_id)
        return form

    def _init_context(self):
        """Provide very initial page without any report data

        Basically, in 2 senariors, user will be lead to this context

            - no parameters in query string
            - no report_type parameter in query string
        """
        return {
            "run_form": self._get_form(),
        }

    def _report_context(self):
        errors = None
        report_data = None
        queries = self.request.GET

        if queries:
            form = self._get_form(self.request.GET)

            if form.is_valid():
                queries = form.cleaned_data
                report_data = self.get_report_data(form)
            else:
                errors = form.errors

        queries = fmt_queries(queries)
        del queries["report type"]
        request_path = remove_from_request_path(self.request, "report_type")

        data = {
            "errors": errors,
            "queries": queries,
            "request_path": request_path,
            "run_form": form,
            "report_data": report_data,
        }

        if request_path:
            data["path_without_build"] = remove_from_request_path(request_path, "r_build")

        return data

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        if "report_type" not in self.request.GET:
            context = self._init_context()
        else:
            context = self._report_context()

        data.update(context)
        data.update(
            {
                "report_url": reverse("testing-report-case-runs"),
                "module": MODULE_NAME,
            }
        )
        return data


class TestingReportByCaseRunTester(TestingReportBase, TestingReportByCaseRunTesterData):
    template_name = "report/testing-report/per_build_report.html"


class TestingReportByCasePriority(TestingReportBase, TestingReportByCasePriorityData):
    template_name = "report/testing-report/per_priority_report.html"


class TestingReportByPlanTags(TestingReportBase, TestingReportByPlanTagsData):
    template_name = "report/testing-report/by_plan_tag_with_rates.html"


class TestingReportByPlanTagsDetail(TestingReportBase, TestingReportByPlanTagsDetailData):
    template_name = "report/testing-report/per_plan_tag.html"


class TestingReportByPlanBuild(TestingReportBase, TestingReportByPlanBuildData):
    template_name = "report/testing-report/by_plan_build_with_rates.html"


class TestingReportByPlanBuildDetail(TestingReportBase, TestingReportByPlanBuildDetailData):
    template_name = "report/testing-report/per_plan_build.html"


class TestingReport(View):
    """Dispatch testing report according to report type"""

    testing_report_views = {
        None: TestingReportByCaseRunTester,
        "per_build_report": TestingReportByCaseRunTester,
        "per_priority_report": TestingReportByCasePriority,
        "runs_with_rates_per_plan_tag": TestingReportByPlanTags,
        "per_plan_tag_report": TestingReportByPlanTagsDetail,
        "runs_with_rates_per_plan_build": TestingReportByPlanBuild,
        "per_plan_build_report": TestingReportByPlanBuildDetail,
    }

    def _get_testing_report_view(self, report_type):
        view_class = self.testing_report_views.get(report_type, None)
        if view_class is None:
            return self.testing_report_views[None].as_view()
        else:
            return view_class.as_view()

    @method_decorator(cache_page(REPORT_VIEW_CACHE_DURATION))
    def get(self, request, *args, **kwargs):
        report_type = request.GET.get("report_type", None)
        view = self._get_testing_report_view(report_type)
        return view(request, *args, **kwargs)


class TestingReportCaseRuns(TestingReportBase, TestingReportCaseRunsData):
    template_name = "report/caseruns.html"
    form_class = TestingReportCaseRunsListForm

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        query_args = self.request.GET
        form = self._get_form(query_args)

        if form.is_valid():
            test_case_runs = self.get_case_runs(form)
            status_names = TestCaseRunStatus.as_dict()
            priority_values = Priority.get_values()

            testers_ids, assignees_ids = self._get_testers_assignees_ids(test_case_runs)
            testers = self.get_related_testers(testers_ids)
            assignees = self.get_related_assignees(assignees_ids)

            data["test_case_runs_count"] = len(test_case_runs)
            data["test_case_runs"] = self.walk_case_runs(
                test_case_runs, status_names, priority_values, testers, assignees
            )
        else:
            data["form_errors"] = form.errors

        return data

    def _get_testers_assignees_ids(self, case_runs):
        testers_ids = set()
        assignees_ids = set()
        for case_run in case_runs:
            pk = case_run.tested_by_id
            if pk:
                testers_ids.add(case_run.tested_by_id)
            pk = case_run.assignee_id
            if pk:
                assignees_ids.add(case_run.assignee_id)
        return list(testers_ids), list(assignees_ids)

    def walk_case_runs(self, case_runs, status_names, priority_values, testers, assignees):
        for case_run in case_runs:
            status_name = status_names[case_run.case_run_status_id]
            priority_value = priority_values[case_run.case.priority_id]
            tester_username = testers.get(case_run.tested_by_id, None)
            assignee_username = assignees.get(case_run.assignee_id, None)
            yield case_run, status_name, priority_value, (
                case_run.assignee_id,
                assignee_username,
            ), (case_run.tested_by_id, tester_username)

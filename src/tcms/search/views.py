# -*- coding: utf-8 -*-

"""
Advance search implementations
"""
import json
import time
from collections import namedtuple
from typing import Dict, List, Union
from urllib.parse import parse_qsl, urlencode, urlparse

from django.db.models.query import QuerySet
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.views.decorators.http import require_GET

from tcms.core.raw_sql import RawSQL
from tcms.core.utils import DataTableResult
from tcms.management.models import Priority, Product
from tcms.search.forms import CaseForm, PlanForm, RunForm
from tcms.search.order import order_targets
from tcms.search.query import SmartDjangoQuery
from tcms.testcases.models import TestCase
from tcms.testplans.models import TestPlan, TestPlanType
from tcms.testruns.models import TestRun

SearchInfo = namedtuple("SearchInfo", ["column_names", "template_file"])


@require_GET
def advance_search(request, tmpl="search/advanced_search.html"):
    """View of /advance-search/"""
    errors = None
    data = request.GET
    target = data.get("target")
    plan_form = PlanForm(data)
    case_form = CaseForm(data)
    run_form = RunForm(data)

    # Update MultipleModelChoiceField on each form dynamically
    plan_form.populate(data)
    case_form.populate(data)
    run_form.populate(data)

    all_forms = (plan_form, case_form, run_form)
    errors = [f.errors for f in all_forms if not f.is_valid()]

    if errors or not data:
        products = Product.objects.order_by("pk").only("pk", "name")
        plan_types = TestPlanType.objects.order_by("name").only("pk", "name")
        priorities = Priority.objects.filter(is_active=True).order_by("value")
        errors = fmt_errors(errors)
        return render(request, tmpl, context=locals())

    start_time = time.time()
    results = search_objects(
        request,
        plan_form.cleaned_data,
        run_form.cleaned_data,
        case_form.cleaned_data,
        target,
    )
    results = order_targets(results, data)
    queries = fmt_queries(*[f.cleaned_data for f in all_forms])
    queries["Target"] = target

    search_infos = {
        "plan": SearchInfo(
            column_names=[
                "",
                "plan_id",
                "name",
                "author__username",
                "owner__username",
                "product",
                "product_version",
                "type",
                "cases_count",
                "runs_count",
                "",
            ],
            template_file="plan/common/json_plans.txt",
        ),
        "case": SearchInfo(
            column_names=[
                "",
                "",
                "case_id",
                "summary",
                "author__username",
                "default_tester__username",
                "",
                "case_status__name",
                "category__name",
                "priority__value",
                "create_date",
            ],
            template_file="case/common/json_cases.txt",
        ),
        "run": SearchInfo(
            column_names=[
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
            ],
            template_file="run/common/json_runs.txt",
        ),
    }

    search_info = search_infos[target]

    dt = DataTableResult(request.GET, results, search_info.column_names, default_order_key="-pk")
    response_data = dt.get_response_data()

    if target == "run":
        from tcms.testruns.views import calculate_associated_data

        calculate_associated_data(response_data["querySet"])

    if "sEcho" in request.GET:
        resp_data = get_template(search_info.template_file).render(response_data, request)
        return JsonResponse(json.loads(resp_data))
    else:
        end_time = time.time()
        time_cost = round(end_time - start_time, 3)

        return render(
            request,
            "search/results.html",
            context={
                "search_target": target,
                "time_cost": time_cost,
                "queries": queries,
                # FIXME: choose another name rather than this_page
                "object_list": response_data["querySet"],
                "total_count": response_data["iTotalRecords"],
            },
        )


def search_objects(
    request: HttpRequest,
    plan_query: Dict,
    run_query: Dict,
    case_query: Dict,
    target: str,
    using: str = "orm",
) -> QuerySet:
    """Query plans, cases or runs according to the target

    :param request: Django HTTP request object.
    :type request: HttpRequest
    :param dict plan_query: a mapping containing cleaned criteria used to query plans.
    :param dict case_query: a mapping containing cleaned criteria used to query cases.
    :param dict run_query: a mapping containing cleaned criteria used to query runs.
    :param str target: query target, plan, case or run.
    :param bool using: the name of query method. Default is ``orm``.
    :return: a Django queryset object containing the query result.
    :rtype: QuerySet
    """
    USING = {"orm": {"query": SmartDjangoQuery, "sum": sum_orm_queries}}
    Query = USING[using]["query"]
    Sum = USING[using]["sum"]
    plans = Query(plan_query, TestPlan.__name__)
    runs = Query(run_query, TestRun.__name__)
    cases = Query(case_query, TestCase.__name__)
    results = Sum(plans, cases, runs, target)
    return results


def sum_orm_queries(
    plans: SmartDjangoQuery,
    cases: SmartDjangoQuery,
    runs: SmartDjangoQuery,
    target: str,
) -> QuerySet:
    """Search target objects together with selected relatives

    :return: a QuerySet object representing queried target objects.
    :rtype: QuerySet
    """
    plans = plans.evaluate()
    cases = cases.evaluate()
    runs = runs.evaluate()

    if target == "run":
        if plans is None and cases is None:
            if runs is None:
                runs = TestRun.objects.none()
        if runs is None:
            runs = TestRun.objects.all()
        if cases is not None:
            runs = runs.filter(case_run__case__in=cases).distinct()
        if plans is not None:
            runs = runs.filter(plan__in=plans).distinct()
        runs = runs.extra(select={"cases_count": RawSQL.total_num_caseruns})
        return runs.select_related(
            "manager", "default_tester", "build__product", "product_version"
        ).only(
            "pk",
            "summary",
            "stop_date",
            "manager__username",
            "default_tester__username",
            "build__product__name",
            "product_version__value",
        )

    if target == "plan":
        if cases is None and runs is None:
            if plans is None:
                plans = TestPlan.objects.none()
        if plans is None:
            plans = TestPlan.objects.all()
        if cases is not None:
            plans = plans.filter(case__in=cases).distinct()
        if runs is not None:
            plans = plans.filter(run__in=runs).distinct()
        return (
            TestPlan.apply_subtotal(plans, cases_count=True, runs_count=True)
            .select_related("author", "owner", "type", "product")
            .only(
                "pk",
                "name",
                "is_active",
                "author__username",
                "owner__username",
                "product__name",
                "type__name",
            )
        )

    if target == "case":
        if plans is None and runs is None:
            if cases is None:
                cases = TestCase.objects.none()
        if cases is None:
            cases = TestCase.objects.all()
        if runs is not None:
            cases = cases.filter(case_run__run__in=runs).distinct()
        if plans is not None:
            cases = cases.filter(plan__in=plans).distinct()
        return cases.select_related(
            "author", "default_tester", "case_status", "category", "priority"
        ).only(
            "pk",
            "summary",
            "create_date",
            "is_automated",
            "is_automated_proposed",
            "author__username",
            "default_tester__username",
            "case_status__name",
            "category__name",
            "priority__value",
        )


def remove_from_request_path(request: Union[HttpRequest, str], names: List[str]) -> str:
    """
    Remove a parameter from request.get_full_path() and return the modified
    path afterwards.
    """
    url_info = urlparse(request.get_full_path() if isinstance(request, HttpRequest) else request)
    return "?" + urlencode(
        {name: value for name, value in parse_qsl(url_info.query) if name not in names}
    )


def make_name_prefix_meaningful(s: str) -> str:
    return (
        s.replace("p_product", "product")
        .replace("p_", "product ")
        .replace("cs_", "case ")
        .replace("pl_", "plan ")
        .replace("r_", "run ")
        .replace("_", " ")
    )


def fmt_errors(form_errors):
    """
    Format errors collected in a Django Form for a better appearance.
    """
    errors = []
    for error in form_errors:
        for k, v in error.items():
            if isinstance(v, list):
                v = ", ".join(map(str, v))
            errors.append((make_name_prefix_meaningful(k), v))
    return errors


def fmt_queries(*queries):
    """Format the queries string."""
    results = {}
    for query in queries:
        for k, v in query.items():
            if isinstance(v, bool) or v:
                if isinstance(v, QuerySet):
                    try:
                        v = ", ".join(o.name for o in v)
                    except AttributeError:
                        try:
                            v = ", ".join(o.value for o in v)
                        except AttributeError:
                            v = ", ".join(v)
                if isinstance(v, list):
                    v = ", ".join(map(str, v))
                results[make_name_prefix_meaningful(k)] = v
    return results

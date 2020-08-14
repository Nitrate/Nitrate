# -*- coding: utf-8 -*-

"""
Advance search implementations
"""

import time
from typing import Dict, List, Union, Any
from urllib.parse import urlparse, parse_qsl, urlencode

from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator
from django.core.paginator import PageNotAnInteger

from tcms.core.raw_sql import RawSQL
from tcms.management.models import Priority
from tcms.management.models import Product
from tcms.search.forms import CaseForm, RunForm, PlanForm
from tcms.search.order import order_targets
from tcms.search.query import SmartDjangoQuery
from tcms.testcases.models import TestCase
from tcms.testplans.models import TestPlan
from tcms.testplans.models import TestPlanType
from tcms.testruns.models import TestRun


@require_GET
def advance_search(request, tmpl='search/advanced_search.html'):
    """View of /advance-search/"""
    errors = None
    data = request.GET
    target = data.get('target')
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
        products = Product.objects.order_by('pk').only('pk', 'name')
        plan_types = TestPlanType.objects.order_by('name').only('pk', 'name')
        priorities = Priority.objects.filter(is_active=True).order_by('value')
        errors = fmt_errors(errors)
        return render(request, tmpl, context=locals())

    start_time = time.time()
    results = query(request,
                    plan_form.cleaned_data,
                    run_form.cleaned_data,
                    case_form.cleaned_data,
                    target)
    results = order_targets(target, results, data)
    queries = fmt_queries(*[f.cleaned_data for f in all_forms])
    queries['Target'] = target
    return render_results(request, results, start_time, queries)


def query(request: HttpRequest,
          plan_query: Dict,
          run_query: Dict,
          case_query: Dict,
          target: str,
          using: str = 'orm') -> QuerySet:
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
    USING = {
        'orm': {
            'query': SmartDjangoQuery,
            'sum': sum_orm_queries
        }
    }
    Query = USING[using]['query']
    Sum = USING[using]['sum']
    plans = Query(plan_query, TestPlan.__name__)
    runs = Query(run_query, TestRun.__name__)
    cases = Query(case_query, TestCase.__name__)
    results = Sum(plans, cases, runs, target)
    return results


def sum_orm_queries(plans: SmartDjangoQuery,
                    cases: SmartDjangoQuery,
                    runs: SmartDjangoQuery,
                    target: str) -> QuerySet:
    """Search target objects together with selected relatives

    :return: a QuerySet object representing queried target objects.
    :rtype: QuerySet
    """
    plans = plans.evaluate()
    cases = cases.evaluate()
    runs = runs.evaluate()
    if target == 'run':
        if not plans and not cases:
            if runs is None:
                runs = TestRun.objects.none()
        if runs is None:
            runs = TestRun.objects.all()
        if cases:
            runs = runs.filter(case_run__case__in=cases).distinct()
        if plans:
            runs = runs.filter(plan__in=plans).distinct()
        return runs
    if target == 'plan':
        if not cases and not runs:
            if plans is None:
                plans = TestPlan.objects.none()
        if plans is None:
            plans = TestPlan.objects.all()
        if cases:
            plans = plans.filter(case__in=cases).distinct()
        if runs:
            plans = plans.filter(run__in=runs).distinct()
        plans = plans.extra(select={
            'num_cases': RawSQL.num_cases,
            'num_runs': RawSQL.num_runs,
            'num_children': RawSQL.num_plans,
        })
        return plans
    if target == 'case':
        if not plans and not runs:
            if cases is None:
                cases = TestCase.objects.none()
        if cases is None:
            cases = TestCase.objects.all()
        if runs:
            cases = cases.filter(case_run__run__in=runs).distinct()
        if plans:
            cases = cases.filter(plan__in=plans).distinct()
        return cases


def render_results(request: HttpRequest,
                   results: QuerySet,
                   start_time: float,
                   queries: Dict[str, Any],
                   tmpl: str = 'search/results.html') -> HttpResponse:
    """Using a SQL "in" query and PKs as the arguments"""
    klasses = {
        'plan': {'class': TestPlan, 'result_key': 'test_plans'},
        'case': {'class': TestCase, 'result_key': 'test_cases'},
        'run': {'class': TestRun, 'result_key': 'test_runs'}
    }
    asc = bool(request.GET.get('asc', None))
    navigate_url = remove_from_request_path(request, ['page'])
    query_url = remove_from_request_path(request, ['order_by'])
    if asc:
        query_url = remove_from_request_path(query_url, ['asc'])
    else:
        query_url = '%s&asc=True' % query_url

    paginator = Paginator(results, 20)
    page = request.GET.get('page')
    try:
        this_page = paginator.page(page)
    except PageNotAnInteger:
        this_page = paginator.page(1)

    page_start = paginator.per_page * (this_page.number - 1) + 1
    page_end = (
        page_start + min(len(this_page.object_list), paginator.per_page) - 1
    )

    calculate_associated_data(list(this_page), queries['Target'])

    end_time = time.time()
    time_cost = round(end_time - start_time, 3)
    context_data = {
        'search_target': klasses[request.GET['target']]['result_key'],
        'time_cost': time_cost,
        'queries': queries,
        'query_url': query_url,
        # For navigation
        'navigate_url': navigate_url,
        'this_page': this_page,
        'page_start': page_start,
        'page_end': page_end,
    }
    return render(request, tmpl, context=context_data)


def remove_from_request_path(request: Union[HttpRequest, str],
                             names: List[str]) -> str:
    """
    Remove a parameter from request.get_full_path() and return the modified
    path afterwards.
    """
    url_info = urlparse(
        request.get_full_path() if isinstance(request, HttpRequest) else request
    )
    return '?' + urlencode({
        name: value for name, value in parse_qsl(url_info.query)
        if name not in names
    })


def make_name_prefix_meaningful(s: str) -> str:
    return (
        s
        .replace('p_product', 'product')
        .replace('p_', 'product ')
        .replace('cs_', 'case ')
        .replace('pl_', 'plan ')
        .replace('r_', 'run ')
        .replace('_', ' ')
    )


def fmt_errors(form_errors):
    """
    Format errors collected in a Django Form for a better appearance.
    """
    errors = []
    for error in form_errors:
        for k, v in error.items():
            if isinstance(v, list):
                v = ', '.join(map(str, v))
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
                        v = ', '.join(o.name for o in v)
                    except AttributeError:
                        try:
                            v = ', '.join(o.value for o in v)
                        except AttributeError:
                            v = ', '.join(v)
                if isinstance(v, list):
                    v = ', '.join(map(str, v))
                results[make_name_prefix_meaningful(k)] = v
    return results


def calculate_associated_data(queryset: List, query_target: str) -> None:
    """Calculate associated data and attach to objects in queryset"""

    # FIXME: Maybe plan and case associated data could be calculated here as well.

    if query_target == 'run':
        for run in queryset:
            env_groups = run.plan.env_group.values_list('name', flat=True)
            if env_groups:
                run.associated_data = {'env_group': env_groups[0]}
            else:
                run.associated_data = {'env_group': None}

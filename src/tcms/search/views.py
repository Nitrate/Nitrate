# -*- coding: utf-8 -*-

"""
Advance search implementations
"""

import time
from typing import List

from django.db.models.query import QuerySet
from django.http import HttpRequest
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


def query(request, plan_query, run_query, case_query, target, using='orm'):
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


def sum_orm_queries(plans, cases, runs, target):
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


def render_results(request, results, start_time, queries,
                   tmpl='search/results.html'):
    """Using a SQL "in" query and PKs as the arguments"""
    klasses = {
        'plan': {'class': TestPlan, 'result_key': 'test_plans'},
        'case': {'class': TestCase, 'result_key': 'test_cases'},
        'run': {'class': TestRun, 'result_key': 'test_runs'}
    }
    asc = bool(request.GET.get('asc', None))
    navigate_url = remove_from_request_path(request, 'page')
    query_url = remove_from_request_path(request, 'order_by')
    if asc:
        query_url = remove_from_request_path(query_url, 'asc')
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


def remove_from_request_path(request, name):
    """
    Remove a parameter from request.get_full_path() and return the modified
    path afterwards.
    """
    if isinstance(request, HttpRequest):
        path = request.get_full_path()
    else:
        path = request
    path = path.split('?')
    if len(path) > 1:
        path = path[1].split('&')
    else:
        return None
    path = [p for p in path if not p.startswith(name)]
    path = '&'.join(path)
    return '?' + path


def fmt_errors(form_errors):
    """
    Format errors collected in a Django Form for a better appearance.
    """
    errors = []
    for error in form_errors:
        for k, v in error.items():
            k = k.replace('p_product', 'product')
            k = k.replace('p_', 'product ')
            k = k.replace('cs_', 'case ')
            k = k.replace('pl_', 'plan ')
            k = k.replace('r_', 'run ')
            k = k.replace('_', ' ')
            if isinstance(v, list):
                v = ', '.join(map(str, v))
            errors.append((k, v))
    return errors


def fmt_queries(*queries):
    """Format the queries string."""
    results = {}
    for query in queries:
        for k, v in query.items():
            k = k.replace('p_product', 'product')
            k = k.replace('p_', 'product ')
            k = k.replace('cs_', 'case ')
            k = k.replace('pl_', 'plan ')
            k = k.replace('r_', 'run ')
            k = k.replace('_', ' ')
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
                results[k] = v
    return results


def calculate_associated_data(queryset: List, query_target):
    """Calculate associated data and attach to objects in queryset"""

    # FIXME: Maybe plan and case associated data could be calculated here as well.

    if query_target == 'run':
        for run in queryset:
            env_groups = run.plan.env_group.values_list('name', flat=True)
            if env_groups:
                run.associated_data = {'env_group': env_groups[0]}
            else:
                run.associated_data = {'env_group': None}

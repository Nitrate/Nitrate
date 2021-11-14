# -*- coding: utf-8 -*-

from typing import Dict

from django.db.models import QuerySet


def order_targets(queryset: QuerySet, queries: Dict) -> QuerySet:
    """
    Designed to work with advance search module.
    Ordering queryset of testplan, testcase, or testrun.

    Each kind of objects, plan, case and run, are ordered by created date by
    default if ``order_by`` is missing from argument ``queries``.

    :param queryset: the queryset of objects to be ordered.
    :type queryset: QuerySet
    :param dict queries: the ``Form.cleaned_data``.
    :return: ordered queryset.
    :rtype: QuerySet.
    """
    order_by = queries.get("order_by", "create_date")
    asc = bool(queries.get("asc", None))
    return apply_order(queryset, order_by, asc)


ORDERABLE_FIELDS = {
    "TestPlan": (
        "plan_id",
        "name",
        "author__username",
        "owner__username",
        "create_date",
        "product__name",
        "type",
        "cases_count",
        "runs_count",
        "children_count",
    ),
    "TestCase": (
        "case_id",
        "summary",
        "author__username",
        "default_tester__username",
        "priority",
        "is_automated",
        "category__name",
        "case_status",
        "create_date",
    ),
    "TestRun": (
        "run_id",
        "summary",
        "manager__username",
        "default_tester__username",
        "env_groups",
        "build__product__name",
        "product_version",
        "plan__name",
    ),
}


def apply_order(queryset: QuerySet, field: str, asc: bool = False) -> QuerySet:
    orderable_fields = ORDERABLE_FIELDS[queryset.model.__name__]
    if field in orderable_fields:
        order_by = field
        if not asc:
            order_by = "-%s" % order_by
        queryset = queryset.order_by(order_by)
    return queryset

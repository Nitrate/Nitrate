# -*- coding: utf-8 -*-

import re
import warnings
from typing import Any, Dict

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Count

from tcms.management.models import Product

COUNT_DISTINCT = 0
QUERY_DISTINCT = 1

ACCEPTABLE_BOOL_VALUES = ("0", "1", 0, 1, True, False)


def parse_bool_value(value):
    if value in ACCEPTABLE_BOOL_VALUES:
        if value == "0":
            return False
        elif value == "1":
            return True
        else:
            return value
    else:
        raise ValueError("Unacceptable bool value.")


def pre_check_product(values):
    if isinstance(values, dict):
        if not values.get("product"):
            raise ValueError("No product name to know what product to get.")
        product_str = values["product"]
    else:
        product_str = values

    if isinstance(product_str, str):
        if not product_str:
            raise ValueError("Got empty product name.")
        return Product.objects.get(name=product_str)
    elif isinstance(product_str, bool):
        raise ValueError("The type of product is not recognizable.")
    elif isinstance(product_str, int):
        return Product.objects.get(pk=product_str)
    else:
        raise ValueError("The type of product is not recognizable.")


def pre_process_ids(value):
    # FIXME: Add more type checks, e.g. value cannot be a boolean value.

    if isinstance(value, list):
        return [isinstance(c, int) and c or int(c.strip()) for c in value if c]

    if isinstance(value, str):
        return [int(c.strip()) for c in value.split(",") if c]

    if isinstance(value, int):
        return [value]

    raise TypeError("Unrecognizable type of ids")


def compare_list(src_list, dest_list):
    return list(set(src_list) - set(dest_list))


def _lookup_fields_in_model(cls, fields):
    """Lookup ManyToMany fields in current table and related tables. For
    distinct duplicate rows when using inner join

    Example:
        cls is TestRun (<class 'tcms.testruns.models.TestRun'>)
        fields is 'plan__case__is_automated'
                    |     |         |----- Normal Field in TestCase
                    |     |--------------- ManyToManyKey in TestPlan
                    |--------------------- ForeignKey in TestRun

    1. plan is a ForeignKey field of TestRun and it will trigger getting the
    related model TestPlan by django orm framework.
    2. case is a ManyToManyKey field of TestPlan and it will trigger using
    INNER JOIN to join TestCase, here will be many duplicated rows.
    3. is_automated is a local field of TestCase only filter the rows (where
    condition).

    So this method will find out that case is a m2m field and notice the
    outer method use distinct to avoid duplicated rows.

    :param cls: table model class
    :type cls: subclass of django.db.models.Model
    :param fields: fields in where condition.
    :type fields: list[str]
    :return: whether use distinct or not
    :rtype: iterable
    """
    for field in fields:
        try:
            field = cls._meta.get_field(field)
            if field.many_to_many:
                yield True
            else:
                if getattr(field, "related_model", None):
                    cls = field.related_model
        except FieldDoesNotExist:
            pass


def _need_distinct_m2m_rows(cls, fields):
    """Check whether the query string has ManyToMany field or not, return
    False if the query string is empty.

    :param cls: table model class
    :type cls: subclass of django.db.models.Model
    :param fields: fields in where condition.
    :type fields: list[str]
    :return: whether use distinct or not
    :rtype: bool
    """
    return next(_lookup_fields_in_model(cls, fields), False) if fields else False


def distinct_m2m_rows(cls, values, op_type):
    """By django model field looking up syntax, loop values and check the
    condition if there is a multi-tables query.

    :param cls: table model class
    :type cls: subclass of django.db.models.Model
    :param values: fields in where condition.
    :type values: dict
    :param int op_type: the operation type.
    :return: QuerySet
    :rtype: django.db.models.query.QuerySet
    """
    flag = False
    for field in values.keys():
        if "__" in field:
            if _need_distinct_m2m_rows(cls, field.split("__")):
                flag = True
                break

    qs = cls.objects.filter(**values)
    if op_type == COUNT_DISTINCT:
        if flag:
            return qs.aggregate(Count("pk", distinct=True))["pk__count"]
        else:
            return qs.count()
    elif op_type == QUERY_DISTINCT:
        return qs.distinct() if flag else qs
    else:
        raise TypeError("Not implement op type %s" % op_type)


def distinct_count(cls, values):
    return distinct_m2m_rows(cls, values, op_type=COUNT_DISTINCT)


def distinct_filter(cls, values):
    return distinct_m2m_rows(cls, values, op_type=QUERY_DISTINCT)


estimated_time_re = re.compile(r"^(\d+[d])?(\d+[h])?(\d+[m])?(\d+[s])?$")
estimated_time_hms_re = re.compile(r"^(\d+):(\d+):(\d+)$")


def pre_process_estimated_time(value):
    """pre process estiamted_time.

    support value - HH:MM:SS & xdxhxmxs
    return xdxhxmxs
    """
    if isinstance(value, str):
        match = estimated_time_re.match(value.replace(" ", ""))
        if match:
            return value
        else:
            match = estimated_time_hms_re.match(value)
            if not match:
                raise ValueError("Invaild estimated_time format.")
            else:
                return "{}h{}m{}s".format(*match.groups())
    else:
        raise ValueError("Invaild estimated_time format.")


def deprecate_critetion_attachment(query: Dict[str, Any]):
    """Deprecate filter criterion attachment

    If there is a filter criterion on the attachments relationship but it
    starts with old relationship name ``attachment``, a deprecation message
    will be displayed and it will be replaced with the new name in the query
    mapping in place.

    :param dict query: the input query mapping to the plan and case filter API.
    """
    attachment_criterion = None
    attachments_critesion = None

    for key in query:
        if key.startswith("attachment__"):
            attachment_criterion = key
        elif key.startswith("attachments__"):
            attachments_critesion = key

    if attachment_criterion and attachments_critesion:
        raise ValueError(
            "Filter criterion attachment and attachments cannot be used "
            "together. Please use attachments."
        )

    if attachment_criterion:
        warnings.warn(
            "Filter criterion attachment is deprecated. Please use attachments.",
            DeprecationWarning,
        )

        new_key = attachment_criterion.replace("attachment", "attachments")
        query[new_key] = query[attachment_criterion]
        # The old one is useless, so remove it.
        del query[attachment_criterion]

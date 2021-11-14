# -*- coding: utf-8 -*-

from itertools import groupby
from operator import itemgetter

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django_comments.models import Comment

from tcms.logs.models import TCMSLogModel
from tcms.management.models import Component
from tcms.testcases import sqls
from tcms.testcases.models import NoneText, TestCase, TestCaseStatus, TestCaseTag, TestCaseText
from tcms.testruns.models import TestCaseRun


class TestCaseViewDataMixin:
    """Mixin class to get view data of test case"""

    def get_case_contenttype(self):
        return ContentType.objects.get_for_model(TestCase)

    def get_case_logs(self, testcase):
        ct = self.get_case_contenttype()
        logs = TCMSLogModel.objects.filter(
            content_type=ct, object_pk=testcase.pk, site=settings.SITE_ID
        )
        logs = logs.values("date", "who__username", "field", "original_value", "new_value")
        return logs.order_by("date")

    def get_case_comments(self, case):
        """Get a case' comments"""
        ct = self.get_case_contenttype()
        comments = Comment.objects.filter(
            content_type=ct, object_pk=case.pk, site=settings.SITE_ID, is_removed=False
        )
        comments = comments.select_related("user").only(
            "submit_date", "user__email", "user__username", "comment"
        )
        comments.order_by("pk")
        return comments


class TestCaseRunViewDataMixin:
    """Mixin class to get view data of test case run"""

    def get_caserun_contenttype(self):
        return ContentType.objects.get_for_model(TestCaseRun)

    def get_caserun_logs(self, caserun):
        caserun_ct = self.get_caserun_contenttype()
        return (
            TCMSLogModel.objects.filter(
                content_type=caserun_ct, object_pk=caserun.pk, site_id=settings.SITE_ID
            )
            .order_by("pk")
            .select_related("who")
            .only("date", "who__username", "field", "original_value", "new_value")
        )

    def get_caserun_comments(self, caserun):
        caserun_ct = self.get_caserun_contenttype()
        comments = Comment.objects.filter(
            content_type=caserun_ct,
            object_pk=caserun.pk,
            site_id=settings.SITE_ID,
            is_removed=False,
        )
        return comments.values("user__email", "submit_date", "comment", "pk", "user__pk")


def get_exported_cases_and_related_data(plan_pks=None, case_pks=None):
    case_status = [
        TestCaseStatus.name_to_id("PROPOSED"),
        TestCaseStatus.name_to_id("CONFIRMED"),
        TestCaseStatus.name_to_id("NEED_UPDATE"),
    ]
    criteria = {"case_status__in": case_status}
    if plan_pks is not None:
        criteria["plan__in"] = plan_pks
    elif case_pks is not None:
        criteria["pk__in"] = case_pks
    cases = (
        TestCase.objects.filter(**criteria)
        .prefetch_related("plan")
        .select_related("priority", "case_status", "author", "default_tester", "category")
        .only(
            "pk",
            "summary",
            "is_automated",
            "notes",
            "priority__value",
            "case_status__name",
            "author__email",
            "default_tester__email",
            "category__name",
        )
        .order_by("pk")
    )

    # cases' components
    # {
    #   case_pk: [{component_name: xxx, product_name: xxx}, ...],
    #   ...
    # }
    if plan_pks is not None:
        criteria = {"cases__plan__in": plan_pks}
    elif case_pks is not None:
        criteria = {"cases__in": case_pks}
    components = (
        Component.objects.filter(**criteria)
        .select_related("product")
        .values_list("cases__pk", "name", "product__name")
        .order_by("cases__pk", "name")
    )
    components = {
        case_pk: [{"component_name": row[1], "product_name": row[2]} for row in rows]
        for case_pk, rows in groupby(components, itemgetter(0))
    }

    # cases' text
    if plan_pks is not None:
        sql = sqls.CASES_TEXT_BY_PLANS.format(", ".join(["%s"] * len(plan_pks)))
        case_texts = TestCaseText.objects.raw(sql, plan_pks)
    elif case_pks is not None:
        sql = sqls.TC_EXPORT_ALL_CASE_TEXTS.format(", ".join(["%s"] * len(case_pks)))
        case_texts = TestCaseText.objects.raw(sql, case_pks)

    case_texts = {text.case_id: text for text in case_texts}

    # cases' tags
    if plan_pks is not None:
        criteria = {"case__plan__in": plan_pks}
    elif case_pks is not None:
        criteria = {"case__in": case_pks}
    tags = TestCaseTag.objects.filter(**criteria).values_list("case", "tag__name").order_by("case")
    tags = {
        case_pk: list(map(itemgetter(1), rows)) for case_pk, rows in groupby(tags, itemgetter(0))
    }

    for case in cases:
        pk = case.pk
        yield (
            case,
            components.get(pk, []),
            case_texts.get(pk, NoneText),
            tags.get(pk, []),
        )

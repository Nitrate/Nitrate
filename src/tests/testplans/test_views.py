# -*- coding: utf-8 -*-

import json
import os
import tempfile
import urllib
import xml.etree.ElementTree as et
from http import HTTPStatus
from textwrap import dedent
from typing import Dict, List, Optional
from unittest.mock import Mock

import pytest
from django import test
from django.db.models import Max
from django.test.client import Client
from django.urls import reverse
from pytest_django.asserts import assertContains, assertNotContains
from uuslug.uuslug import slugify

from tcms.logs.models import TCMSLogModel
from tcms.management.models import Product, TCMSEnvGroup, Version
from tcms.testcases.models import TestCase, TestCasePlan
from tcms.testplans.models import TCMSEnvPlanMap, TestPlan, TestPlanAttachment
from tcms.testplans.views import update_plan_email_settings
from tcms.testruns.models import TestCaseRun
from tests import AuthMixin, BaseCaseRun, BaseDataContext, BasePlanCase, HelperAssertions
from tests import factories as f
from tests import remove_perm_from_user, user_should_have_perm
from tests.testcases.test_views import PlanCaseExportTestHelper


class PlanTests(HelperAssertions, test.TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory(username="admin", email="admin@example.com")
        cls.user.set_password("admin")
        cls.user.is_superuser = True
        cls.user.save()

        cls.c = Client()
        cls.c.login(username="admin", password="admin")

        cls.classification = f.ClassificationFactory(name="Auto")
        cls.product = f.ProductFactory(name="Nitrate", classification=cls.classification)
        cls.product_version = f.VersionFactory(value="0.1", product=cls.product)
        cls.plan_type = f.TestPlanTypeFactory()

        cls.test_plan = f.TestPlanFactory(
            name="another test plan for testing",
            product_version=cls.product_version,
            owner=cls.user,
            author=cls.user,
            product=cls.product,
            type=cls.plan_type,
        )
        cls.plan_id = cls.test_plan.pk

    def test_open_plans_search(self):
        location = reverse("plans-all")
        response = self.c.get(location)
        self.assert200(response)

    def test_search_plans(self):
        location = reverse("plans-all")
        response = self.c.get(location, {"action": "search", "type": self.test_plan.type.pk})
        self.assert200(response)

    def test_plan_delete(self):
        tp_pk = self.test_plan.pk

        location = reverse("plan-delete", args=[tp_pk])
        response = self.c.get(location)
        self.assert200(response)

        response = self.c.get(location, {"sure": "no"})
        self.assert200(response)

        response = self.c.get(location, {"sure": "yes"})
        self.assert200(response)
        deleted = not TestPlan.objects.filter(pk=tp_pk).exists()
        self.assertTrue(deleted, f"TestPlan {tp_pk} should be deleted. But, not.")

    def test_plan_edit(self):
        location = reverse("plan-edit", args=[self.plan_id])
        response = self.c.get(location)
        self.assert200(response)

    def test_plan_printable(self):
        location = reverse("plans-printable")
        response = self.c.get(location, {"plan_id": self.plan_id})
        self.assert200(response)

    def test_plan_attachment(self):
        location = reverse("plan-attachment", args=[self.plan_id])
        response = self.c.get(location)
        self.assert200(response)

    def test_plan_history(self):
        location = reverse("plan-text-history", args=[self.plan_id])
        response = self.c.get(location)
        self.assert200(response)

        response = self.c.get(location, {"plan_text_version": 1})
        self.assert200(response)


class TestPlanModel(test.TestCase):
    """Test some model operations directly without a view"""

    @classmethod
    def setUpTestData(cls):
        cls.plan_1 = f.TestPlanFactory()
        cls.testcase_1 = f.TestCaseFactory()
        cls.testcase_2 = f.TestCaseFactory()

        cls.plan_1.add_case(cls.testcase_1)
        cls.plan_1.add_case(cls.testcase_2)

    def test_plan_delete(self):
        self.plan_1.delete_case(self.testcase_1)
        cases_left = TestCasePlan.objects.filter(plan=self.plan_1.pk)
        self.assertEqual(1, cases_left.count())
        self.assertEqual(self.testcase_2.pk, cases_left[0].case.pk)


# ### Test cases for view methods ### #

TESTS_DATA_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "data"))


class TestImportCasesToPlan(BasePlanCase):
    """Test import cases to a plan"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, "testcases.add_testcaseplan")
        cls.url = reverse("plan-import-cases", args=[cls.plan.pk])

    def test_import_cases(self):
        filename = os.path.join(TESTS_DATA_DIR, "cases-to-import.xml")

        with open(filename, "r") as fin:
            response = self.client.post(self.url, {"xml_file": fin})

        self.assertRedirects(
            response,
            reverse("plan-get", args=[self.plan.pk]) + "#testcases",
            target_status_code=301,
        )

        summary = "Remove this case from a test plan"
        has_case = TestCase.objects.filter(summary=summary).exists()
        self.assertTrue(has_case)

    def test_invalid_input_xml_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = os.path.join(tmp_dir, "input.xml")
            with open(input_file, "w") as f:
                f.write(
                    dedent(
                        """\
                        <?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
                        <testopia version="1.1"></testopia>
                        """
                    )
                )
            with open(input_file, "r") as f:
                response = self.client.post(self.url, {"xml_file": f})
            self.assertContains(response, "No case found")


class TestDeleteCasesFromPlan(BasePlanCase):
    """Test case for deleting cases from a plan"""

    auto_login = True

    def setUp(self):
        super().setUp()
        self.cases_url = reverse("plan-delete-cases", args=[self.plan.pk])

    def test_missing_cases_ids(self):
        response = self.client.post(self.cases_url, {})
        self.assertJsonResponse(
            response,
            {"message": "At least one case is required to delete."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_delete_cases(self):
        post_data = {"case": [self.case_1.pk, self.case_3.pk]}
        response = self.client.post(self.cases_url, post_data)
        data = json.loads(response.content)

        self.assertDictEqual({}, data)
        self.assertFalse(self.plan.case.filter(pk__in=[self.case_1.pk, self.case_3.pk]).exists())

        # Assert action logs are recorded for plan and case correctly

        expected_log = f"Remove from plan {self.plan.pk}"
        for pk in (self.case_1.pk, self.case_3.pk):
            log = TCMSLogModel.get_logs_for_model(TestCase, pk)[0]
            self.assertEqual(expected_log, log.new_value)

        for plan_pk, case_pk in (
            (self.plan.pk, self.case_1.pk),
            (self.plan.pk, self.case_3.pk),
        ):
            expected_log = "Remove case {} from plan {}".format(case_pk, plan_pk)
            self.assertTrue(TCMSLogModel.objects.filter(new_value=expected_log).exists())


class TestSortCases(BasePlanCase):
    """Test case for sorting cases"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cases_url = reverse("plan-reorder-cases", args=[cls.plan.pk])

    def test_missing_cases_ids(self):
        response = self.client.post(self.cases_url, {})
        self.assertJsonResponse(
            response,
            {"message": "At least one case is required to re-order."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_order_cases(self):
        post_data = {"case": [self.case_3.pk, self.case_1.pk]}
        response = self.client.post(self.cases_url, post_data)
        data = json.loads(response.content)

        self.assertEqual({}, data)

        case_plan_rel = TestCasePlan.objects.get(plan=self.plan, case=self.case_3)
        self.assertEqual(10, case_plan_rel.sortkey)

        case_plan_rel = TestCasePlan.objects.get(plan=self.plan, case=self.case_1)
        self.assertEqual(20, case_plan_rel.sortkey)


class TestLinkCases(BasePlanCase):
    """Test case for linking cases from other plans"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.another_plan = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        cls.another_case_1 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            plan=[cls.another_plan],
        )

        cls.another_case_2 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            plan=[cls.another_plan],
        )

        cls.search_cases_for_link_url = reverse("plan-search-cases-for-link", args=[cls.plan.pk])
        cls.link_cases_url = reverse("plan-link-cases", args=[cls.plan.pk])

    def tearDown(self):
        # Ensure permission is removed whenever it was added during tests
        remove_perm_from_user(self.tester, "testcases.add_testcaseplan")

    def assert_quick_search_is_shown(self, response):
        self.assertContains(response, '<li class="profile_tab_active" id="quick_tab">')

    def assert_normal_search_is_shown(self, response):
        self.assertContains(response, '<li class="profile_tab_active" id="normal_tab">')

    def test_show_quick_search_by_default(self):
        response = self.client.post(self.search_cases_for_link_url, {})
        self.assert_quick_search_is_shown(response)

    def assert_search_result(self, response):
        self.assertContains(
            response,
            '<a href="{}">{}</a>'.format(
                reverse("case-get", args=[self.another_case_2.pk]),
                self.another_case_2.pk,
            ),
        )

        # Assert: Do not list case that already belongs to the plan
        self.assertNotContains(
            response,
            '<a href="{}">{}</a>'.format(
                reverse("case-get", args=[self.case_2.pk]), self.case_2.pk
            ),
        )

    def test_quick_search(self):
        post_data = {
            "search_mode": "quick",
            "case_id_set": ",".join(map(str, [self.case_1.pk, self.another_case_2.pk])),
        }
        response = self.client.post(self.search_cases_for_link_url, post_data)

        self.assert_quick_search_is_shown(response)
        self.assert_search_result(response)

    def test_normal_search(self):
        post_data = {
            "search_mode": "normal",
            "case_id_set": ",".join(map(str, [self.case_1.pk, self.another_case_2.pk])),
        }
        response = self.client.post(self.search_cases_for_link_url, post_data)

        self.assert_normal_search_is_shown(response)
        self.assert_search_result(response)

    def test_link_cases(self):
        user_should_have_perm(self.tester, "testcases.add_testcaseplan")

        post_data = {"case": [self.another_case_1.pk, self.another_case_2.pk]}
        response = self.client.post(self.link_cases_url, post_data)

        self.assertRedirects(
            response,
            reverse("plan-get", args=[self.plan.pk]),
            target_status_code=HTTPStatus.MOVED_PERMANENTLY,
        )

        self.assertTrue(
            TestCasePlan.objects.filter(plan=self.plan, case=self.another_case_1).exists()
        )
        self.assertTrue(
            TestCasePlan.objects.filter(plan=self.plan, case=self.another_case_2).exists()
        )


class TestCloneView(BasePlanCase):
    """Test case for cloning a plan"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.another_plan = f.TestPlanFactory(
            name="Another plan for test",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )
        cls.another_case_1 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            plan=[cls.another_plan],
        )
        cls.another_case_2 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            plan=[cls.another_plan],
        )

        cls.third_plan = f.TestPlanFactory(
            name="Third plan for test",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )
        cls.third_case_1 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            plan=[cls.third_plan],
        )
        cls.third_case_2 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            plan=[cls.third_plan],
        )

        cls.totally_new_plan = f.TestPlanFactory(
            name="Test clone plan with copying cases",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )
        cls.case_maintain_original_author = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            plan=[cls.totally_new_plan],
        )
        cls.case_keep_default_tester = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            plan=[cls.totally_new_plan],
        )

        user_should_have_perm(cls.tester, "testplans.add_testplan")
        cls.plan_clone_url = reverse("plans-clone")

    def test_refuse_if_missing_a_plan(self):
        data_missing_plan = {}  # No plan is passed
        response = self.client.get(self.plan_clone_url, data_missing_plan)
        self.assertContains(response, "At least one plan is required by clone function")

    def test_refuse_if_give_nonexisting_plan(self):
        response = self.client.get(self.plan_clone_url, {"plan": 99999})
        self.assertContains(response, "The plan you specify does not exist in database")

    def test_open_clone_page_to_clone_one_plan(self):
        response = self.client.get(self.plan_clone_url, {"plan": self.plan.pk})

        self.assertContains(
            response,
            '<label class="strong" for="id_name">New Plan Name</label>',
            html=True,
        )

        self.assertContains(
            response,
            '<input id="id_name" name="name" type="text" value="Copy of {}">'.format(
                self.plan.name
            ),
            html=True,
        )

    def test_open_clone_page_to_clone_multiple_plans(self):
        response = self.client.get(
            self.plan_clone_url, {"plan": [self.plan.pk, self.another_plan.pk]}
        )

        plans_li = [
            """\
            <li>
                <span class="lab-50">{}</span>
                <span class="lab-100">{}</span>
                <span>
                    <a href="" title="{} ({})">{}</a>
                </span>
            </li>
            """.format(
                plan.pk, plan.type, plan.name, plan.author.email, plan.name
            )
            for plan in (self.another_plan, self.plan)
        ]

        self.assertContains(
            response,
            '<ul class="ul-no-format">{}</ul>'.format("".join(plans_li)),
            html=True,
        )

    def verify_cloned_plan(
        self,
        original_plan,
        cloned_plan,
        link_cases=True,
        copy_cases=None,
        maintain_case_orignal_author=None,
        keep_case_default_tester=None,
    ):
        self.assertIsNotNone(cloned_plan.email_settings)

        self.assertEqual(f"Copy of {original_plan.name}", cloned_plan.name)
        self.assertEqual(Product.objects.get(pk=self.product.pk), cloned_plan.product)
        self.assertEqual(Version.objects.get(pk=self.version.pk), cloned_plan.product_version)

        # Verify option set_parent
        self.assertEqual(TestPlan.objects.get(pk=original_plan.pk), cloned_plan.parent)

        # Verify option copy_texts
        self.assertEqual(cloned_plan.text.count(), original_plan.text.count())
        for copied_text, original_text in zip(cloned_plan.text.all(), original_plan.text.all()):
            self.assertEqual(copied_text.plan_text_version, original_text.plan_text_version)
            self.assertEqual(copied_text.author, original_text.author)
            self.assertEqual(copied_text.create_date, original_text.create_date)
            self.assertEqual(copied_text.plan_text, original_text.plan_text)

        # Verify option copy_attachments
        for attachment in original_plan.attachments.all():
            added = TestPlanAttachment.objects.filter(
                plan=cloned_plan, attachment=attachment
            ).exists()
            self.assertTrue(added)

        # Verify option copy_environment_groups
        for env_group in original_plan.env_group.all():
            added = TCMSEnvPlanMap.objects.filter(plan=cloned_plan, group=env_group).exists()
            self.assertTrue(added)

        # Verify options link_testcases and copy_testcases
        if link_cases and not copy_cases:
            for case in original_plan.case.all():
                is_case_linked = TestCasePlan.objects.filter(plan=cloned_plan, case=case).exists()
                self.assertTrue(is_case_linked)

        if link_cases and copy_cases:
            # Ensure cases of original plan are not linked to cloned plan
            for case in original_plan.case.all():
                original_case_not_linked_to_cloned_plan = TestCasePlan.objects.filter(
                    plan=cloned_plan, case=case
                ).exists()
                self.assertFalse(original_case_not_linked_to_cloned_plan)

            self.assertEqual(cloned_plan.case.count(), original_plan.case.count())

            # Verify if case' author and default tester are set properly
            for original_case, copied_case in zip(original_plan.case.all(), cloned_plan.case.all()):
                if maintain_case_orignal_author:
                    self.assertEqual(original_case.author, copied_case.author)
                else:
                    me = self.tester
                    self.assertEqual(me, copied_case.author)

                if keep_case_default_tester:
                    self.assertEqual(original_case.default_tester, copied_case.default_tester)
                else:
                    me = self.tester
                    self.assertEqual(me, copied_case.default_tester)

    def test_clone_a_plan_with_default_options(self):
        post_data = {
            "name": self.third_plan.make_cloned_name(),
            "plan": self.third_plan.pk,
            "product": self.product.pk,
            "product_version": self.version.pk,
            "set_parent": "on",
            "copy_texts": "on",
            "copy_attachments": "on",
            "copy_environment_groups": "on",
            "link_testcases": "on",
            "maintain_case_orignal_author": "on",
            "keep_case_default_tester": "on",
            "submit": "Clone",
        }
        response = self.client.post(self.plan_clone_url, post_data)

        cloned_plan = TestPlan.objects.get(name=self.third_plan.make_cloned_name())

        self.assertRedirects(
            response,
            reverse("plan-get", args=[cloned_plan.pk]),
            target_status_code=HTTPStatus.MOVED_PERMANENTLY,
        )

        self.verify_cloned_plan(self.third_plan, cloned_plan)

    def test_clone_a_plan_by_copying_cases(self):
        post_data = {
            "name": self.totally_new_plan.make_cloned_name(),
            "plan": self.totally_new_plan.pk,
            "product": self.product.pk,
            "product_version": self.version.pk,
            "set_parent": "on",
            "copy_texts": "on",
            "copy_attachments": "on",
            "copy_environment_groups": "on",
            "link_testcases": "on",
            "maintain_case_orignal_author": "on",
            "keep_case_default_tester": "on",
            "submit": "Clone",
            "copy_testcases": "on",
        }
        self.client.post(self.plan_clone_url, post_data)
        cloned_plan = TestPlan.objects.get(name=self.totally_new_plan.make_cloned_name())
        self.verify_cloned_plan(
            self.totally_new_plan,
            cloned_plan,
            copy_cases=True,
            maintain_case_orignal_author=True,
            keep_case_default_tester=True,
        )

    def test_clone_a_plan_by_setting_me_to_copied_cases_author_default_tester(self):
        post_data = {
            "name": self.totally_new_plan.make_cloned_name(),
            "plan": self.totally_new_plan.pk,
            "product": self.product.pk,
            "product_version": self.version.pk,
            "set_parent": "on",
            "copy_texts": "on",
            "copy_attachments": "on",
            "copy_environment_groups": "on",
            "link_testcases": "on",
            "submit": "Clone",
            "copy_testcases": "on",
            # Do not pass maintain_case_orignal_author and keep_case_default_tester
        }
        self.client.post(self.plan_clone_url, post_data)
        cloned_plan = TestPlan.objects.get(name=self.totally_new_plan.make_cloned_name())
        self.verify_cloned_plan(self.totally_new_plan, cloned_plan, copy_cases=True)

    def test_clone_multiple_plans_with_default_options(self):
        post_data = {
            "plan": [self.plan.pk, self.another_plan.pk],
            "product": self.product.pk,
            "product_version": self.version.pk,
            "set_parent": "on",
            "copy_texts": "on",
            "copy_attachments": "on",
            "copy_environment_groups": "on",
            "link_testcases": "on",
            "maintain_case_orignal_author": "on",
            "keep_case_default_tester": "on",
            "submit": "Clone",
        }
        response = self.client.post(self.plan_clone_url, post_data)

        url_querystr = urllib.parse.urlencode(
            {
                "action": "search",
                "product": self.product.pk,
                "product_version": self.version.pk,
            }
        )
        self.assertRedirects(response, "{}?{}".format(reverse("plans-all"), url_querystr))

        for origin_plan in (self.plan, self.another_plan):
            cloned_plan = TestPlan.objects.get(name=origin_plan.make_cloned_name())
            self.verify_cloned_plan(origin_plan, cloned_plan)


class TestPlansPagesView(BasePlanCase):
    """Test ajax_search view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Add more plans for testing search
        for i in range(25):
            f.TestPlanFactory(
                author=cls.tester,
                owner=cls.tester,
                product=cls.product,
                product_version=cls.version,
            )

        # So far, each test has 26 plans

        cls.search_url = reverse("plans-pages")

        # By default, search active plans. Search by other fields if needed,
        # copy this dict and add other fields.
        cls.search_data = {
            # Search plans
            "is_active": "on",
            # DataTable properties: pagination and sorting
            "sEcho": 1,
            "iDisplayStart": 0,
            "iDisplayLength": 3,
            "iSortCol_0": 1,
            "sSortDir_0": "asc",
            "iSortingCols": 1,
            # In the view, first column is not sortable.
            "bSortable_0": "false",
            "bSortable_1": "true",
            "bSortable_2": "true",
            "bSortable_3": "true",
            "bSortable_4": "true",
        }

    def test_get_first_page_order_by_pk(self):
        search_data = self.search_data.copy()

        response = self.client.get(self.search_url, search_data)

        data = json.loads(response.content)

        # Sort for assertion easily
        data["aaData"] = sorted(
            data["aaData"], key=lambda item: int(item["DT_RowId"].split("_")[1])
        )

        plans_count = TestPlan.objects.count()
        self.assertEqual(1, data["sEcho"])
        self.assertEqual(plans_count, data["iTotalRecords"])
        self.assertEqual(plans_count, data["iTotalDisplayRecords"])
        self.assertEqual(search_data["iDisplayLength"], len(data["aaData"]))

        expected_plans = TestPlan.objects.order_by("pk")[0:3]

        for i, plan in enumerate(expected_plans):
            self.assertEqual(
                "<a href='{}'>{}</a>".format(plan.get_absolute_url(), plan.pk),
                data["aaData"][i]["1"],
            )

    def test_get_last_page_order_by_name(self):
        search_data = self.search_data.copy()
        plans_count = TestPlan.objects.count()
        # To request last page
        search_data["iDisplayStart"] = int((round(plans_count / 3.0) - 1) * 3)
        search_data["iSortCol_0"] = 2

        response = self.client.get(self.search_url, search_data)

        data = json.loads(response.content)

        self.assertEqual(1, data["sEcho"])
        self.assertEqual(plans_count, data["iTotalRecords"])
        self.assertEqual(plans_count, data["iTotalDisplayRecords"])
        self.assertEqual(2, len(data["aaData"]))

        expected_plans = TestPlan.objects.order_by("name")[
            search_data["iDisplayStart"] : plans_count
        ]

        for i, plan in enumerate(expected_plans):
            self.assertEqual(
                "<a href='{}'>{}</a>".format(plan.get_absolute_url(), plan.pk),
                data["aaData"][i]["1"],
            )

    def test_get_second_page_order_by_pk_desc(self):
        search_data = self.search_data.copy()
        # To request second page
        search_data["iDisplayStart"] = 3
        search_data["sSortDir_0"] = "desc"

        response = self.client.get(self.search_url, search_data)

        data = json.loads(response.content)

        plans_count = TestPlan.objects.count()
        self.assertEqual(1, data["sEcho"])
        self.assertEqual(plans_count, data["iTotalRecords"])
        self.assertEqual(plans_count, data["iTotalDisplayRecords"])
        self.assertEqual(search_data["iDisplayLength"], len(data["aaData"]))

        expected_plans = TestPlan.objects.order_by("-pk")[3:6]

        for i, plan in enumerate(expected_plans):
            self.assertEqual(
                "<a href='{}'>{}</a>".format(plan.get_absolute_url(), plan.pk),
                data["aaData"][i]["1"],
            )


class TestExportView(PlanCaseExportTestHelper, BasePlanCase):
    """Test export view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.plan_export = f.TestPlanFactory(
            name="Test export from plan",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        cls.case_export = f.TestCaseFactory(
            summary="Export from a plan",
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_export],
        )
        cls.case_export_more = f.TestCaseFactory(
            summary="Export more",
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_export],
        )

        cls.url = reverse("plans-export")

    def test_no_plan_is_passed(self):
        response = self.client.get(self.url)
        self.assertContains(response, "At least one target is required")

    def test_export(self):
        response = self.client.get(self.url, {"plan": self.plan_export.pk})
        self.assert200(response)

        xmldoc = et.fromstring(response.content)

        for elem_case in xmldoc.findall("testcase"):
            summary = elem_case.find("summary").text.strip()
            if summary == self.case_export.summary:
                self.assert_exported_case(
                    self.case_export,
                    elem_case,
                    {
                        "action": None,
                        "effect": None,
                        "setup": None,
                        "breakdown": None,
                    },
                    # No components and tags are set to case
                    [],
                    [],
                    [],
                )
            elif summary == self.case_export_more.summary:
                self.assert_exported_case(
                    self.case_export_more,
                    elem_case,
                    {
                        "action": None,
                        "effect": None,
                        "setup": None,
                        "breakdown": None,
                    },
                    # No components and tags are set to case
                    [],
                    [],
                    [],
                )


class TestChooseCasesToRun(BaseCaseRun):
    """Test choose_run view"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create an empty run for test
        cls.test_run_2 = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            build=cls.build,
            manager=cls.tester,
            default_tester=cls.tester,
        )

        user_should_have_perm(cls.tester, "testruns.change_testrun")
        cls.url = reverse("plan-choose-run", args=[cls.plan.pk])

    def test_plan_id_does_not_exist(self):
        max_pk = TestPlan.objects.aggregate(max_pk=Max("pk"))["max_pk"]
        url = reverse("plan-choose-run", args=[max_pk + 1])
        resp = self.client.get(url)
        self.assert404(resp)

    def test_show_page(self):
        resp = self.client.get(self.url, data={"case": [self.case_1.pk, self.case_2.pk]})

        expected_content = [
            '<td><a href="/run/{0}/">{0}</a></td>'.format(self.test_run_1.pk),
            f"<td>{self.test_run_1.summary}</td>",
            '<td><a href="/run/{0}/">{0}</a></td>'.format(self.test_run_2.pk),
            f"<td>{self.test_run_2.summary}</td>",
            "<b>Cases to be added: 2</b>",
            '<td><a href="/case/{0}/">{0}</a>'
            '<input type="hidden" name="case" value="{0}">'
            "</td>".format(self.case_1.pk),
            '<td><a href="/case/{0}/">{0}</a>'
            '<input type="hidden" name="case" value="{0}">'
            "</td>".format(self.case_2.pk),
        ]

        for item in expected_content:
            self.assertContains(resp, item, html=True)

    def test_add_cases_to_runs(self):
        resp = self.client.post(
            self.url,
            data={
                "testrun_ids": self.test_run_2.pk,
                "case_ids": [self.case_1.pk, self.case_2.pk],
            },
        )

        self.assertRedirects(
            resp,
            reverse("plan-get", args=[self.plan.pk]),
            fetch_redirect_response=False,
        )

        for run_id, case_id in (
            (self.test_run_2.pk, self.case_1.pk),
            (self.test_run_2.pk, self.case_2.pk),
        ):
            self.assertTrue(TestCaseRun.objects.filter(run=run_id, case=case_id).exists())

    def test_empty_selected_runs(self):
        resp = self.client.post(self.url, data={"case_ids": [self.case_1.pk, self.case_2.pk]})

        self.assertContains(
            resp,
            "At least one test run and one case is required to add cases to runs.",
        )

    def test_404_if_some_run_id_does_not_exist(self):
        resp = self.client.post(
            self.url,
            data={
                "testrun_ids": self.test_run_2.pk + 1,
                "case_ids": [self.case_1.pk, self.case_2.pk],
            },
        )

        self.assert404(resp)

    def test_no_selected_cases(self):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        max_pk = result["max_pk"]

        resp = self.client.post(
            self.url,
            data={
                "testrun_ids": self.test_run_2.pk,
                "case_ids": [max_pk + 1, max_pk + 2],
            },
        )

        self.assertContains(
            resp,
            "At least one test run and one case is required to add cases to runs.",
        )


class TestTreeViewAddChildPlan(BasePlanCase):
    """Test plan's treeview"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_treeview_data()

    def setUp(self):
        self.login_tester()

    def test_plan_id_does_not_exist(self):
        max_plan_id = self.get_max_plan_id()
        self.url = reverse("plan-treeview-add-children", args=[max_plan_id + 1])
        response = self.client.post(self.url, {"children": [1]})
        self.assertJsonResponse(
            response,
            {"message": f"Plan {max_plan_id + 1} does not exist."},
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_child_plan_id_does_not_exist(self):
        max_plan_id = self.get_max_plan_id()
        self.url = reverse("plan-treeview-add-children", args=[self.plan_2.pk])
        response = self.client.post(self.url, {"children": [max_plan_id + 1]})
        self.assertJsonResponse(
            response,
            {"message": f"Child plan {max_plan_id + 1} does not exist."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_add_child_that_is_an_ancestor_already(self):
        plan_id = self.plan_6.pk
        child_plan_id = self.plan_3.pk
        self.url = reverse("plan-treeview-add-children", args=[plan_id])
        response = self.client.post(self.url, {"children": [child_plan_id]})
        self.assertJsonResponse(
            response,
            {"message": f"Plan {child_plan_id} is an ancestor of " f"plan {plan_id} already."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_add_child_that_is_already_a_descendant(self):
        plan_id = self.plan_2.pk
        child_plan_id = self.plan_4.pk
        self.url = reverse("plan-treeview-add-children", args=[plan_id])
        response = self.client.post(self.url, {"children": [child_plan_id]})
        self.assertJsonResponse(
            response,
            {"message": f"Plan {child_plan_id} is a descendant of " f"plan {plan_id} already."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_add_a_child(self):
        plan_id = self.plan_4.pk
        child_plan_id = self.plan_9.pk
        self.url = reverse("plan-treeview-add-children", args=[plan_id])
        response = self.client.post(self.url, {"children": [child_plan_id]})

        plan = TestPlan.objects.get(pk=child_plan_id)
        self.assertEqual(plan_id, plan.parent.pk)

        self.assertJsonResponse(
            response, {"parent_plan": plan_id, "children_plans": [self.plan_9.pk]}
        )


class TestTreeViewRemoveChildPlan(BasePlanCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_treeview_data()

    def test_parent_plan_does_not_exist(self):
        self.login_tester()

        nonexisting = self.get_max_plan_id() + 1
        url = reverse("plan-treeview-remove-children", args=[nonexisting])
        resp = self.client.post(url)
        self.assertJsonResponse(
            resp,
            {"message": f"Plan {nonexisting} does not exist."},
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_remove_children(self):
        self.login_tester()

        max_plan_id = self.get_max_plan_id()

        test_data = [
            [
                self.plan_4.pk,
                [self.plan_5.pk, self.plan_6.pk],
                {
                    "parent_plan": self.plan_4.pk,
                    "removed": [self.plan_5.pk, self.plan_6.pk],
                    "non_descendants": [],
                },
            ],
            [
                self.plan_2.pk,
                [self.plan_8.pk, max_plan_id + 1],
                {
                    "parent_plan": self.plan_2.pk,
                    "removed": [self.plan_8.pk],
                    "non_descendants": [max_plan_id + 1],
                },
            ],
            [
                self.plan_4.pk,
                [max_plan_id + 1, max_plan_id + 2],
                {
                    "parent_plan": self.plan_4.pk,
                    "removed": [],
                    "non_descendants": [max_plan_id + 1, max_plan_id + 2],
                },
            ],
        ]

        for parent_plan, post_data, expected_json in test_data:
            url = reverse("plan-treeview-remove-children", args=[parent_plan])
            resp = self.client.post(url, data={"children": post_data})
            self.assertJsonResponse(resp, expected_json)


class TestTreeViewChangeParent(BasePlanCase):
    """Test change plan parent"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_treeview_data()
        user_should_have_perm(cls.tester, "testplans.change_testplan")

    @staticmethod
    def _construct_url(plan_id: int) -> str:
        return reverse("plan-treeview-change-parent", args=[plan_id])

    def test_non_existing_target_plan(self):
        result = TestPlan.objects.aggregate(max_pk=Max("pk"))
        resp = self.client.patch(
            self._construct_url(result["max_pk"] + 1),
            data={
                "parent": self.plan_3.pk,
            },
            content_type="application/json",
        )
        self.assert404(resp)
        json_data = json.loads(resp.content)
        self.assertIn("Cannot change parent of plan", json_data["message"])

    def test_parent_id_is_not_integer(self):
        resp = self.client.patch(
            self._construct_url(self.plan_5.pk),
            data={"parent": "an id"},
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {"message": 'The given parent plan id "an id" is not a positive integer.'},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_missing_parent_id(self):
        resp = self.client.patch(
            self._construct_url(self.plan_5.pk),
            data={},
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {"message": "Missing parent plan id."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_parent_does_not_exist(self):
        result = TestPlan.objects.aggregate(max_pk=Max("pk"))
        non_existing_id = result["max_pk"] + 1
        resp = self.client.patch(
            self._construct_url(self.plan_5.pk),
            data={"parent": non_existing_id},
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {"message": f"The parent plan id {non_existing_id} does not exist."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_parent_is_a_descendant_already(self):
        resp = self.client.patch(
            self._construct_url(self.plan_4.pk),
            data={"parent": self.plan_6.pk},
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {
                "message": f"The parent plan {self.plan_6.pk} is a descendant "
                f"of plan {self.plan_4.pk} already."
            },
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_change_parent(self):
        targets = (
            (self.plan_5, str(self.plan_5.parent.pk)),
            (self.plan_9, "None"),
        )
        new_parent: TestPlan = self.plan_3

        target_plan: TestPlan
        expected_original_value: str

        for target_plan, expected_original_value in targets:
            resp = self.client.patch(
                self._construct_url(target_plan.pk),
                data={"parent": new_parent.pk},
                content_type="application/json",
            )
            self.assert200(resp)

            self.assertEqual(new_parent, TestPlan.objects.get(pk=target_plan.pk).parent)
            self.assertTrue(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="parent",
                    original_value=expected_original_value,
                    new_value=str(new_parent.pk),
                ).exists(),
                msg=f"Log does not exist for plan {target_plan.pk}",
            )


class TestEnableDisablePlanViews(AuthMixin, HelperAssertions, test.TestCase):
    """Test enable or disable a plan"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plan = f.TestPlanFactory()
        cls.plan_1 = f.TestPlanFactory(is_active=False)
        user_should_have_perm(cls.tester, "testplans.change_testplan")

    def test_target_plan_does_not_exist(self):
        result = TestPlan.objects.aggregate(max_pk=Max("pk"))
        plan_id = result["max_pk"] + 1
        resp = self.client.patch(reverse("plan-set-enable", args=[plan_id]))
        self.assertJsonResponse(
            resp,
            {"message": f"Plan id {plan_id} does not exist."},
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_enable_plan(self):
        resp = self.client.patch(reverse("plan-set-enable", args=[self.plan_1.pk]))
        self.assert200(resp)
        self.assertTrue(TestPlan.objects.get(pk=self.plan_1.pk).is_active)
        self.assertTrue(
            TCMSLogModel.objects.filter(
                who=self.tester,
                field="is_active",
                original_value="False",
                new_value="True",
            ).exists()
        )

    def test_disable_plan(self):
        resp = self.client.patch(reverse("plan-set-disable", args=[self.plan.pk]))
        self.assert200(resp)
        self.assertFalse(TestPlan.objects.get(pk=self.plan.pk).is_active)
        self.assertTrue(
            TCMSLogModel.objects.filter(
                who=self.tester,
                field="is_active",
                original_value="True",
                new_value="False",
            ).exists()
        )


@pytest.mark.parametrize("plan_id", [1, 2])
@pytest.mark.parametrize("slug", [None, "plan---1", slugify("plan 1")])
def test_plan_get(plan_id: int, slug: Optional[str], base_data: BaseDataContext, client):
    plan = base_data.plan_creator(pk=1, name="plan 1")

    urlconf_args = [plan_id]
    if slug is not None:
        urlconf_args.append(slug)

    response = client.get(reverse("plan-get", args=urlconf_args))

    if plan_id == 2:
        assert HTTPStatus.NOT_FOUND == response.status_code
        return

    if slug is None or slug == "plan---1":
        assert HTTPStatus.MOVED_PERMANENTLY == response.status_code
        assert plan.get_absolute_url() == response.url
        return

    assert HTTPStatus.OK == response.status_code


@pytest.mark.parametrize("notify_on_plan_update", [True, False])
@pytest.mark.parametrize("notify_on_plan_delete", [True, False])
@pytest.mark.parametrize("notify_on_case_update", [True, False])
@pytest.mark.parametrize("auto_to_plan_owner", [True, False])
@pytest.mark.parametrize("auto_to_plan_author", [True, False])
@pytest.mark.parametrize("auto_to_case_owner", [True, False])
@pytest.mark.parametrize("auto_to_case_default_tester", [True, False])
def test_update_plan_email_settings(
    notify_on_plan_update: bool,
    notify_on_plan_delete: bool,
    notify_on_case_update: bool,
    auto_to_plan_owner: bool,
    auto_to_plan_author: bool,
    auto_to_case_owner: bool,
    auto_to_case_default_tester: bool,
    base_data: BaseDataContext,
):
    plan = base_data.plan_creator(pk=1, name="plan 1")

    form = Mock(
        cleaned_data={
            "notify_on_plan_update": notify_on_plan_update,
            "notify_on_plan_delete": notify_on_plan_delete,
            "notify_on_case_update": notify_on_case_update,
            "auto_to_plan_owner": auto_to_plan_owner,
            "auto_to_plan_author": auto_to_plan_author,
            "auto_to_case_owner": auto_to_case_owner,
            "auto_to_case_default_tester": auto_to_case_default_tester,
        }
    )
    update_plan_email_settings(plan, form)

    plan: TestPlan = TestPlan.objects.get(pk=1)

    for var_name, var_value in locals().items():
        if var_name.startswith("notify_on_") or var_name.startswith("auto_to_"):
            assert var_value == getattr(plan.email_settings, var_name)


@pytest.mark.parametrize("query_args", [None, {"plan": [1]}, {"plan": [1, 2]}])
def test_plan_printable_page(
    query_args: Optional[Dict[str, List[int]]], client, tester, base_data: BaseDataContext
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    case_1: TestCase = base_data.case_creator(pk=1, summary="case 1")
    plan.add_case(case_1)
    case_2: TestCase = base_data.case_creator(pk=2, summary="case 2")
    plan.add_case(case_2)
    case_2.add_text(
        "case 2 action", "case 2 effect", "case 2 setup", "case 2 breakdown", author=tester
    )

    plan_2: TestPlan = base_data.plan_creator(pk=2, name="plan 2")
    case_3: TestCase = base_data.case_creator(pk=3, summary="case 3")
    plan_2.add_case(case_3)
    case_3.add_text("action", "effect", "setup", "breakdown", author=tester)
    case_3.add_text("action 3", "effect 3", "setup 3", "breakdown 3", author=tester)

    response = client.get(reverse("plans-printable"), data=query_args)

    if query_args is None:
        assertContains(response, "At least one target is required")
        return

    for plan_id in query_args["plan"]:
        if plan_id == 1:
            assertContains(response, f"<h1>[{plan.pk}] <b>{plan.name}</b></h1>", html=True)
            assertContains(response, f"<li>[{case_2.pk}] {case_2.summary}</li>", html=True)
            assertContains(response, "case 2 action")
            assertContains(response, "case 2 effect")
            assertContains(response, "case 2 setup")
            assertContains(response, "case 2 breakdown")

        elif plan_id == 2:
            assertContains(response, f"<h1>[{plan_2.pk}] <b>{plan_2.name}</b></h1>", html=True)
            assertContains(response, f"<li>[{case_3.pk}] {case_3.summary}</li>", html=True)
            assertContains(response, "action 3")
            assertContains(response, "effect 3")
            assertContains(response, "setup 3")
            assertContains(response, "breakdown 3")

    # case 1 does not have text, so not included in the printable page.
    assertNotContains(response, f"<li>[{case_1.pk}] {case_1.summary}</li>", html=True)


def test_get_create_new_plan_page(logged_in_tester, client):
    user_should_have_perm(logged_in_tester, "testplans.add_testplan")
    user_should_have_perm(logged_in_tester, "testplans.add_testplantext")
    user_should_have_perm(logged_in_tester, "testplans.add_tcmsenvplanmap")
    response = client.get(reverse("plans-new"))
    assertContains(response, "<h2>Create New Test Plan</h2>", html=True)


@pytest.mark.parametrize("extra_link", [None, "https://srv1.example.com/"])
@pytest.mark.parametrize("env_group", [None, 1])
def test_creat_a_new_plan(
    extra_link: Optional[str],
    env_group: Optional[int],
    logged_in_tester,
    base_data: BaseDataContext,
    client,
):
    user_should_have_perm(logged_in_tester, "testplans.add_testplan")
    user_should_have_perm(logged_in_tester, "testplans.add_testplantext")
    user_should_have_perm(logged_in_tester, "testplans.add_tcmsenvplanmap")

    env_group: TCMSEnvGroup = TCMSEnvGroup.objects.create(pk=1, name="os", manager=logged_in_tester)

    data = {
        "name": "A new plan",
        "product": base_data.product.pk,
        "product_version": base_data.product_version.pk,
        "type": base_data.plan_type_smoke.pk,
    }
    if extra_link is not None:
        data["extra_link"] = extra_link
    if env_group is not None:
        data["env_group"] = env_group.pk
    response = client.post(reverse("plans-new"), data=data)

    assert HTTPStatus.FOUND == response.status_code

    new_plan: Optional[TestPlan] = TestPlan.objects.order_by("-pk").first()
    assert reverse("plan-get", args=[new_plan.pk]) == response.url

    assert "A new plan" == new_plan.name
    assert base_data.product == new_plan.product
    assert base_data.product_version == new_plan.product_version
    assert base_data.plan_type_smoke == new_plan.type
    assert new_plan.text_exist()
    assert "" == new_plan.text.first().plan_text
    assert logged_in_tester == new_plan.author
    assert logged_in_tester == new_plan.owner
    assert new_plan.parent is None

    if extra_link is None:
        assert "" == new_plan.extra_link
    else:
        assert extra_link == new_plan.extra_link

    has = TCMSEnvPlanMap.objects.filter(plan=new_plan, group=env_group).exists()
    if env_group is None:
        assert not has
    else:
        assert has


DATA_DIR: str = os.path.join(os.path.dirname(__file__), "data")
PLAN_DOCUMENT_ODT: str = os.path.join(DATA_DIR, "plan-document.odt")
PLAN_DOCUMENT_TXT: str = os.path.join(DATA_DIR, "plan-document.txt")
PLAN_DOCUMENT_HTML: str = os.path.join(DATA_DIR, "plan-document.html")


@pytest.mark.parametrize("upload_file", [PLAN_DOCUMENT_ODT, PLAN_DOCUMENT_TXT, PLAN_DOCUMENT_HTML])
def test_upload_a_plan_document_to_create_new_plan(
    upload_file: str, logged_in_tester, base_data: BaseDataContext, client
):
    user_should_have_perm(logged_in_tester, "testplans.add_testplan")
    user_should_have_perm(logged_in_tester, "testplans.add_testplantext")
    user_should_have_perm(logged_in_tester, "testplans.add_tcmsenvplanmap")

    with open(upload_file, "rb") as f:
        data = {
            "name": "A new plan",
            "product": base_data.product.pk,
            "product_version": base_data.product_version.pk,
            "type": base_data.plan_type_smoke.pk,
            "upload_plan_text": f,
        }
        response = client.post(reverse("plans-new"), data=data)

        assert HTTPStatus.OK == response.status_code
        assert "This is a cool Web application" in response.content.decode()


def test_create_new_plan_with_invalid_args(logged_in_tester, base_data: BaseDataContext, client):
    user_should_have_perm(logged_in_tester, "testplans.add_testplan")
    user_should_have_perm(logged_in_tester, "testplans.add_testplantext")
    user_should_have_perm(logged_in_tester, "testplans.add_tcmsenvplanmap")

    # Missing product_vesion
    data = {
        "name": "A new plan",
        "product": base_data.product.pk,
        "type": base_data.plan_type_smoke.pk,
    }
    response = client.post(reverse("plans-new"), data=data)

    assert HTTPStatus.OK == response.status_code

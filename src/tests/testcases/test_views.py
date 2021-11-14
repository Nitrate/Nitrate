# -*- coding: utf-8 -*-

import json
import unittest
import xml.etree.ElementTree
from datetime import datetime, timedelta
from operator import attrgetter, itemgetter
from unittest.mock import patch

from bs4 import BeautifulSoup
from django import test
from django.db.models import Max
from django.forms import ValidationError
from django.http import Http404
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django_comments.models import Comment
from uuslug import slugify

from tcms.comments.models import add_comment
from tcms.core.utils import timedelta2int
from tcms.issuetracker.models import Issue, IssueTracker
from tcms.logs.models import TCMSLogModel
from tcms.management.models import Component, Priority, TestTag
from tcms.testcases.fields import MultipleEmailField
from tcms.testcases.forms import CaseNotifyForm
from tcms.testcases.models import (
    TestCase,
    TestCaseCategory,
    TestCaseComponent,
    TestCasePlan,
    TestCaseStatus,
)
from tcms.testcases.views import (
    calculate_for_testcases,
    plan_from_request_or_none,
    update_case_email_settings,
)
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestCaseRun
from tests import BaseCaseRun, BasePlanCase
from tests import factories as f
from tests import remove_perm_from_user, user_should_have_perm
from tests.testcases import assert_new_case


class TestGetPlanFromRequest(test.TestCase):
    """Test function plan_from_request_or_none"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_plan_id_from_get_request(self):
        request = self.factory.get("/uri", data={"from_plan": 1})
        pk = plan_from_request_or_none(request, pk_enough=True)
        self.assertEqual(1, pk)

    def test_get_plan_id_from_post_request(self):
        request = self.factory.post("/uri", data={"from_plan": 1})
        pk = plan_from_request_or_none(request, pk_enough=True)
        self.assertEqual(1, pk)

    @patch("tcms.testcases.views.get_object_or_404")
    def test_get_plan_object_from_get_request(self, get_object_or_404):
        request = self.factory.get("/uri", data={"from_plan": 1})
        plan = plan_from_request_or_none(request)
        self.assertEqual(get_object_or_404.return_value, plan)

    @patch("tcms.testcases.views.get_object_or_404")
    def test_get_plan_object_from_post_request(self, get_object_or_404):
        request = self.factory.post("/uri", data={"from_plan": 1})
        plan = plan_from_request_or_none(request)
        self.assertEqual(get_object_or_404.return_value, plan)

    def test_missing_plan_id_in_get_request(self):
        request = self.factory.get("/uri")
        plan = plan_from_request_or_none(request)
        self.assertIsNone(plan)

    def test_missing_plan_id_in_post_request(self):
        request = self.factory.post("/uri")
        plan = plan_from_request_or_none(request)
        self.assertIsNone(plan)

    @patch("tcms.testcases.views.get_object_or_404")
    def test_nonexisting_plan_id_from_get_request(self, get_object_or_404):
        get_object_or_404.side_effect = Http404

        request = self.factory.get("/uri", data={"from_plan": 1})
        self.assertRaises(Http404, plan_from_request_or_none, request)

    @patch("tcms.testcases.views.get_object_or_404")
    def test_nonexisting_plan_id_from_post_request(self, get_object_or_404):
        get_object_or_404.side_effect = Http404

        request = self.factory.post("/uri", data={"from_plan": 1})
        self.assertRaises(Http404, plan_from_request_or_none, request)

    def test_invalid_plan_id(self):
        request = self.factory.post("/uri", data={"from_plan": "a"})
        self.assertIsNone(plan_from_request_or_none(request, pk_enough=True))


class TestUpdateCaseNotificationList(test.TestCase):
    """Test update_case_email_settings"""

    @classmethod
    def setUpTestData(cls):
        cls.case = f.TestCaseFactory(summary="Test notify")
        cls.case_1 = f.TestCaseFactory(summary="Test notify 2", default_tester=None)

    @staticmethod
    def update_the_notify_settings(case):
        form = CaseNotifyForm(
            {
                "notify_on_case_update": "On",
                "notify_on_case_delete": "On",
                "author": "On",
                "managers_of_runs": "On",
                "default_testers_of_runs": "On",
                "assignees_of_case_runs": "On",
                "default_tester_of_case": "On",
            }
        )
        form.is_valid()
        update_case_email_settings(case, form)

    def test_update_notifications(self):
        self.update_the_notify_settings(self.case)
        emailing = self.case.emailing
        self.assertTrue(emailing.notify_on_case_update)
        self.assertTrue(emailing.notify_on_case_delete)
        self.assertTrue(emailing.auto_to_case_author)
        self.assertTrue(emailing.auto_to_run_manager)
        self.assertTrue(emailing.auto_to_run_tester)
        self.assertTrue(emailing.auto_to_case_run_assignee)
        self.assertTrue(emailing.auto_to_case_tester)

    def test_not_notify_default_tester(self):
        self.update_the_notify_settings(self.case_1)
        self.assertFalse(self.case_1.emailing.auto_to_case_tester)


class TestMultipleEmailField(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_delimiter = ","
        cls.field = MultipleEmailField(delimiter=cls.default_delimiter)

    def test_to_python(self):
        value = "zhangsan@localhost"
        pyobj = self.field.to_python(value)
        self.assertEqual(pyobj, [value])

        value = "zhangsan@localhost,,lisi@example.com,"
        pyobj = self.field.to_python(value)
        self.assertEqual(pyobj, ["zhangsan@localhost", "lisi@example.com"])

        for value in ("", None, []):
            pyobj = self.field.to_python(value)
            self.assertEqual(pyobj, [])

    def test_clean(self):
        value = "zhangsan@localhost"
        data = self.field.clean(value)
        self.assertEqual(data, [value])

        value = "zhangsan@localhost,lisi@example.com"
        data = self.field.clean(value)
        self.assertEqual(data, ["zhangsan@localhost", "lisi@example.com"])

        value = ",zhangsan@localhost, ,lisi@example.com, \n"
        data = self.field.clean(value)
        self.assertEqual(data, ["zhangsan@localhost", "lisi@example.com"])

        value = ",zhangsan,zhangsan@localhost, \n,lisi@example.com, "
        self.assertRaises(ValidationError, self.field.clean, value)

        value = ""
        self.field.required = True
        self.assertRaises(ValidationError, self.field.clean, value)

        value = ""
        self.field.required = False
        data = self.field.clean(value)
        self.assertEqual(data, [])

        self.assertRaisesRegex(
            ValidationError, "is not a valid string value", self.field.clean, object()
        )


# ### Test cases for view methods ###


class TestOperateComponentView(BasePlanCase):
    """Tests for operating components on cases"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.comp_application = f.ComponentFactory(
            name="Application",
            product=cls.product,
            initial_owner=cls.tester,
            initial_qa_contact=cls.tester,
        )
        cls.comp_database = f.ComponentFactory(
            name="Database",
            product=cls.product,
            initial_owner=cls.tester,
            initial_qa_contact=cls.tester,
        )
        cls.comp_cli = f.ComponentFactory(
            name="CLI",
            product=cls.product,
            initial_owner=cls.tester,
            initial_qa_contact=cls.tester,
        )
        cls.comp_api = f.ComponentFactory(
            name="API",
            product=cls.product,
            initial_owner=cls.tester,
            initial_qa_contact=cls.tester,
        )

        f.TestCaseComponentFactory(case=cls.case_1, component=cls.comp_cli)
        f.TestCaseComponentFactory(case=cls.case_1, component=cls.comp_api)

        user_should_have_perm(cls.tester, "testcases.add_testcasecomponent")

    def tearDown(self):
        remove_perm_from_user(self.tester, "testcases.delete_testcasecomponent")

    def test_show_components_form(self):
        response = self.client.post(
            reverse("cases-get-component-form"), {"product": self.product.pk}
        )

        self.assertContains(
            response,
            '<option value="{}" selected="selected">{}</option>'.format(
                self.product.pk, self.product.name
            ),
            html=True,
        )

        comp_options = (
            f'<option value="{comp.pk}">{comp.name}</option>'
            for comp in (
                self.comp_application,
                self.comp_database,
                self.comp_cli,
                self.comp_api,
            )
        )
        self.assertContains(
            response,
            f'<select multiple="multiple" id="id_o_component" name="o_component">'
            f'{"".join(comp_options)}</select>',
            html=True,
        )

    def test_add_components(self):
        post_data = {
            "product": self.product.pk,
            "o_component": [self.comp_application.pk, self.comp_database.pk],
            "case": [self.case_1.pk],
            "a": "add",
            "from_plan": self.plan.pk,
        }
        response = self.client.post(reverse("cases-add-component"), post_data)

        self.assertJsonResponse(
            response,
            {
                "message": "Succeed to add component(s) Application, Database.",
            },
        )

        for comp in (self.comp_application, self.comp_database):
            case_components = TestCaseComponent.objects.filter(case=self.case_1, component=comp)
            self.assertTrue(case_components.exists())

    def test_remove_components(self):
        user_should_have_perm(self.tester, "testcases.delete_testcasecomponent")

        post_data = {
            "o_component": [self.comp_cli.pk, self.comp_api.pk],
            "case": [self.case_1.pk],
            "a": "remove",
        }
        response = self.client.post(reverse("cases-remove-component"), post_data)

        self.assertJsonResponse(response, {"message": "Succeed to remove component(s) CLI, API."})

        for comp in (self.comp_cli, self.comp_api):
            case_components = TestCaseComponent.objects.filter(case=self.case_1, component=comp)
            self.assertFalse(case_components.exists())

    def test_fail_to_remove_if_component_not_exist(self):
        user_should_have_perm(self.tester, "testcases.delete_testcasecomponent")

        result = Component.objects.aggregate(max_pk=Max("pk"))
        nonexistent_id = result["max_pk"] + 1
        resp = self.client.post(
            reverse("cases-remove-component"),
            {
                "o_component": [nonexistent_id],
                "case": [self.case_1.pk],
                "a": "remove",
            },
        )

        data = json.loads(resp.content)
        self.assertIn(f"Nonexistent component id(s) {nonexistent_id}", data["message"][0])

    @patch("tcms.testcases.models.TestCase.remove_component")
    def test_case_remove_component_fails(self, remove_component):
        remove_component.side_effect = Exception

        user_should_have_perm(self.tester, "testcases.delete_testcasecomponent")

        resp = self.client.post(
            reverse("cases-remove-component"),
            {
                "o_component": [self.comp_cli.pk, self.comp_api.pk],
                "case": [self.case_1.pk],
                "a": "remove",
            },
        )

        data = json.loads(resp.content)
        case_id = self.case_1.pk
        msgs = sorted(data["message"])
        self.assertIn(
            f"Failed to remove component {self.comp_api.name} from case {case_id}",
            msgs[0],
        )
        self.assertIn(
            f"Failed to remove component {self.comp_cli.name} from case {case_id}",
            msgs[1],
        )


class TestOperateCategoryView(BasePlanCase):
    """Tests for operating category on cases"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_cat_full_auto = f.TestCaseCategoryFactory(name="Full Auto", product=cls.product)
        cls.case_cat_full_manual = f.TestCaseCategoryFactory(
            name="Full Manual", product=cls.product
        )

        user_should_have_perm(cls.tester, "testcases.add_testcasecomponent")

        cls.case_category_url = reverse("cases-category")

    def test_show_categories_form(self):
        response = self.client.post(self.case_category_url, {"product": self.product.pk})

        self.assertContains(
            response,
            f'<option value="{self.product.pk}" selected="selected">'
            f"{self.product.name}"
            f"</option>",
            html=True,
        )

        categories = "".join(
            f'<option value="{category.pk}">{category.name}</option>'
            for category in self.product.category.all()
        )
        self.assertContains(
            response,
            f'<select multiple="multiple" id="id_o_category" name="o_category">'
            f"{categories}"
            f"</select>",
            html=True,
        )

    def test_update_cases_category(self):
        post_data = {
            "from_plan": self.plan.pk,
            "product": self.product.pk,
            "case": [self.case_1.pk, self.case_3.pk],
            "a": "update",
            "o_category": self.case_cat_full_auto.pk,
        }
        response = self.client.post(self.case_category_url, post_data)

        self.assertJsonResponse(response, {})

        for pk in (self.case_1.pk, self.case_3.pk):
            case = TestCase.objects.get(pk=pk)
            self.assertEqual(self.case_cat_full_auto, case.category)


class TestOperateCasePlans(BasePlanCase):
    """Test operation in case' plans tab"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Besides the plan and its cases created in parent class, this test case
        # also needs other cases in order to list multiple plans of a case and
        # remove a plan from a case.

        cls.plan_test_case_plans = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )
        cls.plan_test_add = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )
        cls.plan_test_remove = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        cls.case_1.add_to_plan(cls.plan_test_case_plans)
        cls.case_1.add_to_plan(cls.plan_test_remove)

        cls.perm_add = "testcases.add_testcaseplan"
        cls.perm_change = "testcases.change_testcaseplan"
        user_should_have_perm(cls.tester, cls.perm_add)
        user_should_have_perm(cls.tester, cls.perm_change)

    def _contains_html(self, content, expected):
        from django.test.testcases import assert_and_parse_html

        parsed_content = assert_and_parse_html(self, content, None, "content is not valid html.")
        parsed_expected = assert_and_parse_html(self, expected, None, "expected is not valid html.")
        self.assertTrue(parsed_content.count(parsed_expected) > 0)

    def assert_list_case_plans(self, response, case):
        self.assert200(response)

        returned_html = json.loads(response.content)["html"]
        for rel in TestCasePlan.objects.filter(case=case):
            plan = rel.plan
            slugified_name = slugify(plan.name)
            self._contains_html(
                returned_html,
                f'<a href="/plan/{plan.pk}/{slugified_name}">{plan.pk}</a>',
            )
            self._contains_html(
                returned_html,
                f'<a href="/plan/{plan.pk}/{slugified_name}">{plan.name}</a>',
            )

    def test_missing_permission_to_add(self):
        remove_perm_from_user(self.tester, self.perm_add)
        response = self.client.post(
            reverse("case-add-to-plans", args=[self.case_1.pk]),
            {"plan": self.plan_test_add.pk},
        )
        self.assert403(response)

    def test_missing_permission_to_remove(self):
        remove_perm_from_user(self.tester, self.perm_change)
        response = self.client.post(
            reverse("case-remove-from-plans", args=[self.case_1.pk]),
            {"plan": self.plan_test_remove.pk},
        )
        self.assert403(response)

    def test_add_a_plan(self):
        response = self.client.post(
            reverse("case-add-to-plans", args=[self.case_1.pk]),
            {"plan": self.plan_test_add.pk},
        )

        self.assert_list_case_plans(response, self.case_1)

        self.assertTrue(
            TestCasePlan.objects.filter(plan=self.plan_test_add, case=self.case_1).exists()
        )

    def test_remove_a_plan(self):
        response = self.client.post(
            reverse("case-remove-from-plans", args=[self.case_1.pk]),
            {"plan": self.plan_test_remove.pk},
        )

        self.assert_list_case_plans(response, self.case_1)

        self.assertFalse(
            TestCasePlan.objects.filter(case=self.case_1, plan=self.plan_test_remove).exists()
        )

    def test_add_a_few_of_plans(self):
        # This time, add a few plans to another case
        response = self.client.post(
            reverse("case-add-to-plans", args=[self.case_2.pk]),
            {"plan": [self.plan_test_add.pk, self.plan_test_remove.pk]},
        )

        self.assertTrue(
            TestCasePlan.objects.filter(case=self.case_2, plan=self.plan_test_add).exists()
        )
        self.assertTrue(
            TestCasePlan.objects.filter(case=self.case_2, plan=self.plan_test_remove).exists()
        )

        self.assert_list_case_plans(response, self.case_2)

    def test_missing_plan_id(self):
        resp = self.client.post(reverse("case-add-to-plans", args=[self.case_1.pk]))

        self.assert400(resp)

        data = json.loads(resp.content)
        self.assertIn("Missing plan ids", data["message"][0])

    def test_all_plan_ids_do_not_exist(self):
        max_pk = TestPlan.objects.aggregate(max_pk=Max("pk"))["max_pk"]
        nonexisting_plan_ids = [max_pk + 1, max_pk + 2]
        resp = self.client.post(
            reverse("case-add-to-plans", args=[self.case_1.pk]),
            {"plan": nonexisting_plan_ids},
        )

        self.assert400(resp)

        data = json.loads(resp.content)
        self.assertIn("Nonexistent plan ids", data["message"][0])


class GetTagCandidatesForRemoval(BasePlanCase):
    """Test remove tags to and from cases in a plan"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tag_fedora = f.TestTagFactory(name="fedora")
        cls.tag_rhel = f.TestTagFactory(name="rhel")
        cls.tag_python = f.TestTagFactory(name="python")

        f.TestCaseTagFactory(case=cls.case_1, tag=cls.tag_fedora)
        f.TestCaseTagFactory(case=cls.case_1, tag=cls.tag_rhel)
        f.TestCaseTagFactory(case=cls.case_1, tag=cls.tag_python)
        f.TestCaseTagFactory(case=cls.case_3, tag=cls.tag_rhel)
        f.TestCaseTagFactory(case=cls.case_3, tag=cls.tag_python)

        cls.url = reverse("cases-tag-candidates-for-removal")

    def test_show_tag_candidates(self):
        response = self.client.get(self.url, {"case": [self.case_1.pk, self.case_3.pk]})

        tags = (
            TestTag.objects.filter(cases__in=[self.case_1, self.case_3]).order_by("name").distinct()
        )
        tag_options = "".join(f'<option value="{tag.pk}">{tag.name}</option>' for tag in tags)

        self.assertContains(
            response,
            f'<p><label for="id_tags">Tags:</label>'
            f'<select multiple="multiple" id="id_tags" name="tags">{tag_options}</select>'
            f"</p>",
            html=True,
        )


class TestEditCase(BasePlanCase):
    """Test edit view method"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.proposed_case = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_proposed,
            plan=[cls.plan],
        )

        user_should_have_perm(cls.tester, "testcases.change_testcase")
        cls.case_edit_url = reverse("case-edit", args=[cls.case_1.pk])

        # Copy, then modify or add new data for specific tests below
        cls.edit_data = {
            "from_plan": cls.plan.pk,
            "summary": cls.case_1.summary,
            "product": cls.case_1.category.product.pk,
            "category": cls.case_1.category.pk,
            "default_tester": "",
            "estimated_time": "0m",
            "case_status": cls.case_status_confirmed.pk,
            "arguments": "",
            "extra_link": "",
            "notes": "",
            "is_automated": "0",
            "requirement": "",
            "script": "",
            "alias": "",
            "priority": cls.case_1.priority.pk,
            "tag": "RHEL",
            "setup": "",
            "action": "",
            "breakdown": "",
            "effect": "",
            "cc_list": "",
        }

    def test_404_if_case_id_not_exist(self):
        url = reverse("case-edit", args=[99999])
        response = self.client.get(url)
        self.assert404(response)

    def test_404_if_from_plan_not_exist(self):
        response = self.client.get(self.case_edit_url, {"from_plan": 9999})
        self.assert404(response)

    def test_show_edit_page(self):
        response = self.client.get(self.case_edit_url)
        self.assert200(response)

    def test_edit_a_case(self):
        edit_data = self.edit_data.copy()
        new_summary = f"Edited: {self.case_1.summary}"
        edit_data["summary"] = new_summary

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = "{}?from_plan={}".format(
            reverse("case-get", args=[self.case_1.pk]),
            self.plan.pk,
        )
        self.assertRedirects(response, redirect_url)

        edited_case = TestCase.objects.get(pk=self.case_1.pk)
        self.assertEqual(new_summary, edited_case.summary)

    def test_continue_edit_this_case_after_save(self):
        edit_data = self.edit_data.copy()
        edit_data["_continue"] = "continue edit"

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = "{}?from_plan={}".format(
            reverse("case-edit", args=[self.case_1.pk]),
            self.plan.pk,
        )
        self.assertRedirects(response, redirect_url)

    def test_continue_edit_next_confirmed_case_after_save(self):
        edit_data = self.edit_data.copy()
        edit_data["_continuenext"] = "continue edit next case"

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = "{}?from_plan={}".format(
            reverse("case-edit", args=[self.case_2.pk]),
            self.plan.pk,
        )
        self.assertRedirects(response, redirect_url)

    def test_continue_edit_next_non_confirmed_case_after_save(self):
        edit_data = self.edit_data.copy()
        edit_data["case_status"] = self.case_status_proposed.pk
        edit_data["_continuenext"] = "continue edit next case"

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = "{}?from_plan={}".format(
            reverse("case-edit", args=[self.proposed_case.pk]),
            self.plan.pk,
        )
        self.assertRedirects(response, redirect_url)

    def test_return_to_plan_confirmed_cases_tab(self):
        edit_data = self.edit_data.copy()
        edit_data["_returntoplan"] = "return to plan"

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = "{}#testcases".format(reverse("plan-get", args=[self.plan.pk]))
        self.assertRedirects(response, redirect_url, target_status_code=301)

    def test_return_to_plan_review_cases_tab(self):
        edit_data = self.edit_data.copy()
        edit_data["case_status"] = self.case_status_proposed.pk
        edit_data["_returntoplan"] = "return to plan"

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = "{}#reviewcases".format(reverse("plan-get", args=[self.plan.pk]))
        self.assertRedirects(response, redirect_url, target_status_code=301)


class TestChangeCasesAutomated(BasePlanCase):
    """Test automated view method"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.change_data = {
            "case": [cls.case_1.pk, cls.case_2.pk],
            "a": "change",
            # Add necessary automated value here:
            # o_is_automated
            # o_is_manual
            # o_is_automated_proposed
        }

        user_should_have_perm(cls.tester, "testcases.change_testcase")
        cls.change_url = reverse("cases-automated")

    def test_update_automated(self):
        change_data = self.change_data.copy()
        change_data["o_is_automated"] = "on"

        response = self.client.post(self.change_url, change_data)

        self.assertJsonResponse(response, {})

        for case in TestCase.objects.filter(pk__in=self.change_data["case"]):
            self.assertEqual(1, case.is_automated)

    def test_update_manual(self):
        change_data = self.change_data.copy()
        change_data["o_is_manual"] = "on"

        response = self.client.post(self.change_url, change_data)

        self.assertJsonResponse(response, {})

        for pk in self.change_data["case"]:
            case = TestCase.objects.get(pk=pk)
            self.assertEqual(0, case.is_automated)

    def test_update_automated_proposed(self):
        change_data = self.change_data.copy()
        change_data["o_is_automated_proposed"] = "on"

        response = self.client.post(self.change_url, change_data)

        self.assertJsonResponse(response, {})

        for case in TestCase.objects.filter(pk__in=self.change_data["case"]):
            self.assertTrue(case.is_automated_proposed)

    def test_fail_due_to_invalid_input(self):
        change_data = self.change_data.copy()
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        change_data["case"] = [result["max_pk"] + 1]

        resp = self.client.post(self.change_url, change_data)

        self.assert400(resp)

        data = json.loads(resp.content)
        self.assertIn(f'{change_data["case"][0]} do not exist', data["messages"][0])


class PlanCaseExportTestHelper:
    """Used to verify exported cases

    This could be reused for two use cases of export from cases or plans.
    """

    def assert_exported_case(
        self,
        case,
        element,
        expected_text,
        expected_components,
        expected_tags,
        expected_products,
    ):
        """Verify exported case info inside XML document

        :param case: a test case object to be exported.
        :type case: :class:`TestCase`
        :param element: an XML element object representing a test case inside
            XML document. It is the return value from ``ElementTree.findall``
            or ``ElementTree.find``.
        :param dict expected_text: a mapping representing expected case text object.
            It must have four key/value pairs ``action``, ``effect``, ``breakdown``
            and ``setup``.
        :param expected_components: a list of expected component names in
            whatever order.
        :type expected_components: list[str]
        :param expected_tags: a list of expected tag names in whatever order.
        :type expected_tags: list[str]
        :param expected_products: a list of expected product names in whatever
            order.
        :type expected_tags: list[str]
        """
        self.assertEqual(case.author.email, element.attrib["author"])
        self.assertEqual(case.priority.value, element.attrib["priority"])
        self.assertEqual(case.is_automated, int(element.attrib["automated"]))
        self.assertEqual(case.case_status.name, element.attrib["status"])
        self.assertEqual(case.summary, element.find("summary").text)
        self.assertEqual(case.category.name, element.find("categoryname").text)
        if not case.default_tester:
            self.assertEqual(None, element.find("defaulttester").text)
        else:
            self.assertEqual(case.default_tester.email, element.find("defaulttester").text)
        self.assertEqual(case.notes or None, element.find("notes").text)
        self.assertEqual(expected_text["action"], element.find("action").text)
        self.assertEqual(expected_text["effect"], element.find("expectedresults").text)
        self.assertEqual(expected_text["setup"], element.find("setup").text)
        self.assertEqual(expected_text["breakdown"], element.find("breakdown").text)

        self.assertEqual(
            sorted(expected_components),
            sorted(elem.text.strip() for elem in element.findall("component")),
        )

        self.assertEqual(
            set(expected_products),
            set(
                map(
                    itemgetter("product"),
                    map(attrgetter("attrib"), element.findall("component")),
                )
            ),
        )

        self.assertEqual(
            sorted(expected_tags),
            sorted(elem.text.strip() for elem in element.findall("tag")),
        )

        self.assertEqual(
            sorted(map(attrgetter("name"), case.plan.all())),
            sorted(
                item.text.strip() for item in element.find("testplan_reference").findall("item")
            ),
        )


class TestExportCases(PlanCaseExportTestHelper, BasePlanCase):
    """Test export view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.export_url = reverse("cases-export")

        # Change case status in order to test cases in expected scope can be exported.
        cls.case_1.case_status = cls.case_status_proposed
        cls.case_1.save()

        # Add components to case 1 and case 2
        for name in ["vi", "emacs"]:
            component = Component.objects.create(
                name=name,
                product=cls.product,
                initial_owner=cls.tester,
                initial_qa_contact=cls.tester,
            )
            cls.case_1.add_component(component)

        for name in ["db", "cli", "webui"]:
            component = Component.objects.create(
                name=name,
                product=cls.product,
                initial_owner=cls.tester,
                initial_qa_contact=cls.tester,
            )
            cls.case_2.add_component(component)

        # Add tags to case 2
        for name in ["python", "nitrate"]:
            tag = TestTag.objects.create(name=name)
            cls.case_2.add_tag(tag)

        # Add text to case 1 with several verions
        cls.case_1.add_text("action", "effect", "setup", "breakdown")
        cls.case_1.add_text("action 1", "effect 1", "setup 1", "breakdown 1")
        cls.case_1.add_text("action 2", "effect 2", "setup 2", "breakdown 2")

    def assert_exported_case_1(self, element):
        self.assert_exported_case(
            self.case_1,
            element,
            {
                "action": "action 2",
                "effect": "effect 2",
                "setup": "setup 2",
                "breakdown": "breakdown 2",
            },
            ["emacs", "vi"],
            [],
            [self.product.name],
        )

    def assert_exported_case_2(self, element):
        self.assert_exported_case(
            self.case_2,
            element,
            {
                "action": None,
                "effect": None,
                "setup": None,
                "breakdown": None,
            },
            ["cli", "db", "webui"],
            ["nitrate", "python"],
            [self.product.name],
        )

    def test_export_cases(self):
        response = self.client.post(self.export_url, {"case": [self.case_1.pk, self.case_2.pk]})

        today = datetime.now()
        # Verify header
        self.assertEqual(
            "attachment; filename=tcms-testcases-%02i-%02i-%02i.xml"
            % (today.year, today.month, today.day),
            response["Content-Disposition"],
        )
        # verify content

        xmldoc = xml.etree.ElementTree.fromstring(response.content)
        exported_cases_elements = xmldoc.findall("testcase")
        self.assertEqual(2, len(exported_cases_elements))

        for element in exported_cases_elements:
            summary = element.find("summary").text
            if summary == self.case_1.summary:
                self.assert_exported_case_1(element)
            elif summary == self.case_2.summary:
                self.assert_exported_case_2(element)

    def test_no_cases_to_be_exported(self):
        response = self.client.post(self.export_url, {})
        self.assertContains(response, "At least one target is required")


class TestPrintablePage(BasePlanCase):
    """Test printable page view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.printable_url = reverse("cases-printable")

        cls.case_1.add_text(action="action", effect="effect", setup="setup", breakdown="breakdown")
        cls.case_2.add_text(action="action", effect="effect", setup="setup", breakdown="breakdown")

    def test_no_cases_to_print(self):
        response = self.client.post(self.printable_url, {})
        self.assertContains(response, "At least one target is required")

    def test_printable_page(self):
        response = self.client.post(self.printable_url, {"case": [self.case_1.pk, self.case_2.pk]})

        for case in [self.case_1, self.case_2]:
            self.assertContains(response, f"<h3>[{case.pk}] {case.summary}</h3>", html=True)


class TestCloneCase(BasePlanCase):
    """Test clone view method"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.orphan_plan = f.TestPlanFactory(
            name="Orphan plan for test below",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        cls.plan_test_clone = f.TestPlanFactory(
            name="Plan for testing clone cases",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        cls.plan_test_clone_more = f.TestPlanFactory(
            name="Plan for testing more clone cases",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        cls.tag_1 = f.TestTagFactory(name="tag1")
        cls.tag_2 = f.TestTagFactory(name="tag2")

        f.TestCaseTagFactory(case=cls.case, tag=cls.tag_1)
        f.TestCaseTagFactory(case=cls.case, tag=cls.tag_2)

        # Add attachments to cls.case

        cls.attachment_1 = f.TestAttachmentFactory(submitter=cls.tester)
        cls.attachment_2 = f.TestAttachmentFactory(submitter=cls.tester)

        f.TestCaseAttachmentFactory(case=cls.case, attachment=cls.attachment_1)
        f.TestCaseAttachmentFactory(case=cls.case, attachment=cls.attachment_2)

        # Add components to cls.case

        cls.component_1 = f.ComponentFactory(name="db", product=cls.product)
        # This component belongs to a different product than cls.product.
        # When copy a case, it should be added to cls.product.
        cls.component_2 = f.ComponentFactory(name="web")

        f.TestCaseComponentFactory(case=cls.case, component=cls.component_1)
        f.TestCaseComponentFactory(case=cls.case, component=cls.component_2)

        cls.case_author = f.UserFactory(username="clone_case_author")
        cls.case_test_clone = f.TestCaseFactory(
            author=cls.case_author,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan],
        )

        user_should_have_perm(cls.tester, "testcases.add_testcase")
        cls.clone_url = reverse("cases-clone")

    def test_refuse_if_missing_argument(self):
        # Refuse to clone cases if missing selectAll and case arguments
        response = self.client.get(self.clone_url, {})

        self.assertContains(response, "At least one case is required")

    def test_show_clone_page_with_from_plan(self):
        response = self.client.get(
            self.clone_url,
            {"from_plan": self.plan.pk, "case": [self.case_1.pk, self.case_2.pk]},
        )

        self.assertContains(
            response,
            f"<div>"
            f'<input type="radio" id="id_use_sameplan" name="selectplan" '
            f'  value="{self.plan.pk}">'
            f'<label for="id_use_sameplan" class="strong">'
            f"Use the same Plan -- {self.plan.pk} : {self.plan.name}"
            f"</label>"
            f"</div>",
            html=True,
        )

        # The order of cases is important for running tests against PostgreSQL.
        # Instead of calling assertContains to assert a piece of HTML inside the
        # response, it is necessary to inspect the response content directly.

        bs = BeautifulSoup(response.content.decode("utf-8"), "html.parser")
        case_ids = sorted(
            map(
                int,
                [elem.attrs["value"] for elem in bs.find(id="id_case").find_all("input")],
            )
        )
        self.assertEqual([self.case_1.pk, self.case_2.pk], case_ids)

    def test_show_clone_page_without_from_plan(self):
        response = self.client.get(self.clone_url, {"case": self.case_1.pk})

        self.assertNotContains(
            response,
            "Use the same Plan -- {} : {}".format(self.plan.pk, self.plan.name),
        )

        self.assertContains(
            response,
            '<label for="id_case_0">'
            '<input checked id="id_case_0" name="case" '
            'type="checkbox" value="{}"> {}</label>'.format(self.case_1.pk, self.case_1.summary),
            html=True,
        )

    def test_clone_one_case_to_a_plan(self):
        self._clone_cases([self.plan_test_clone], [self.case])

    def test_clone_one_case_to_several_plans(self):
        self._clone_cases([self.plan_test_clone, self.plan_test_clone_more], [self.case])

    def test_clone_some_cases_to_a_plan(self):
        self._clone_cases([self.plan_test_clone], [self.case, self.case_1])

    def test_clone_some_cases_to_several_plans(self):
        self._clone_cases(
            [self.plan_test_clone, self.plan_test_clone_more], [self.case, self.case_1]
        )

    def test_link_one_case_to_a_plan(self):
        self._clone_cases([self.plan_test_clone], [self.case], copy_case=False)

    def test_link_one_case_to_several_plans(self):
        self._clone_cases(
            [self.plan_test_clone, self.plan_test_clone_more],
            [self.case],
            copy_case=False,
        )

    def test_link_some_cases_to_a_plan(self):
        self._clone_cases([self.plan_test_clone], [self.case, self.case_1], copy_case=False)

    def test_link_some_cases_to_several_plans(self):
        self._clone_cases(
            [self.plan_test_clone, self.plan_test_clone_more],
            [self.case, self.case_1],
            copy_case=False,
        )

    def assert_cloned_case(
        self,
        orig_case,
        cloned_case,
        copy_case=True,
        keep_original_author=False,
        keep_original_default_tester=False,
        copy_component=False,
        copy_attachment=None,
    ):
        # Ensure this is a copy
        if copy_case:
            self.assertNotEqual(orig_case.pk, cloned_case.pk)

            self.assertEqual(orig_case.summary, cloned_case.summary)
            self.assertEqual(orig_case.is_automated, cloned_case.is_automated)
            self.assertEqual(orig_case.is_automated_proposed, cloned_case.is_automated_proposed)
            self.assertEqual(orig_case.script, cloned_case.script)
            self.assertEqual(orig_case.arguments, cloned_case.arguments)
            self.assertEqual(orig_case.extra_link, cloned_case.extra_link)
            self.assertEqual(orig_case.requirement, cloned_case.requirement)
            self.assertEqual(orig_case.alias, cloned_case.alias)
            self.assertEqual(orig_case.estimated_time, cloned_case.estimated_time)
            self.assertEqual(orig_case.category.name, cloned_case.category.name)
            self.assertEqual(orig_case.priority.value, cloned_case.priority.value)
            self.assertEqual(orig_case.notes, cloned_case.notes)

            # Assert text
            orig_case_text = orig_case.latest_text()
            cloned_case_text = cloned_case.latest_text()

            if keep_original_author:
                self.assertEqual(orig_case.author, cloned_case_text.author)
            else:
                self.assertEqual(self.tester, cloned_case_text.author)

            self.assertEqual(orig_case_text.action, cloned_case_text.action)
            self.assertEqual(orig_case_text.effect, cloned_case_text.effect)
            self.assertEqual(orig_case_text.setup, cloned_case_text.setup)
            self.assertEqual(orig_case_text.breakdown, cloned_case_text.breakdown)

            # Assert tags
            tags = cloned_case.tag.all()
            tags_from_orig_cases = orig_case.tag.all()
            self.assertSetEqual(
                {item.pk for item in tags_from_orig_cases}, {item.pk for item in tags}
            )

            # Assert attachments
            if copy_attachment:
                orig_attachments = orig_case.attachments.order_by("pk")
                cloned_attachments = cloned_case.attachments.order_by("pk")
                self.assertListEqual(list(orig_attachments), list(cloned_attachments))

            if copy_component:
                expected_components = [self.component_1.name, self.component_2.name]

                self.assertListEqual(
                    expected_components,
                    [c.name for c in cloned_case.component.order_by("name")],
                )

                for plan in cloned_case.plan.all():
                    self.assertListEqual(
                        expected_components,
                        [c.name for c in plan.product.component.order_by("name")],
                    )

        else:
            self.assertEqual(orig_case.pk, cloned_case.pk)

        if keep_original_author:
            self.assertEqual(orig_case.author, cloned_case.author)
        else:
            self.assertEqual(self.tester, cloned_case.author)

        if keep_original_default_tester:
            self.assertEqual(orig_case.author, cloned_case.default_tester)
        else:
            self.assertEqual(self.tester, cloned_case.default_tester)

    def _clone_cases(
        self,
        dest_plans,
        orig_cases,
        orig_plan=None,
        copy_case=True,
        keep_original_author=False,
        keep_original_default_tester=False,
        copy_component=False,
        copy_attachment=False,
    ):
        post_data = {
            "plan": [item.pk for item in dest_plans],
            "case": [item.pk for item in orig_cases],
            "copy_case": copy_case,
            "maintain_case_orignal_author": keep_original_author,
            "maintain_case_orignal_default_tester": keep_original_default_tester,
            "copy_component": copy_component,
            "copy_attachment": copy_attachment,
        }

        if orig_plan:
            post_data["from_plan"] = orig_plan.pk

        resp = self.client.post(self.clone_url, post_data)

        dest_plans_count = len(dest_plans)
        orig_cases_count = len(orig_cases)

        # Assert response from view

        if dest_plans_count == 1 and orig_cases_count == 1:
            # Use last() to get the correct case. If a case is cloned into
            # another plan, last() returns that case. If a case is cloned into
            # the same plan, last() just returns the new cloned case properly.
            cloned_case = dest_plans[0].case.order_by("pk").last()
            redirect_url = reverse("case-get", args=[cloned_case.pk])
            self.assertRedirects(resp, f"{redirect_url}?from_plan={dest_plans[0].pk}")
        elif orig_cases_count == 1:
            cloned_case = dest_plans[0].case.first()
            self.assertRedirects(resp, reverse("case-get", args=[cloned_case.pk]))
        elif dest_plans_count == 1:
            self.assertRedirects(
                resp,
                reverse("plan-get", args=[dest_plans[0].pk]),
                fetch_redirect_response=False,
            )
        else:
            self.assertContains(resp, "Test case successful to clone")

        # Assert cases are cloned or linked correctly

        for dest_plan in dest_plans:
            for orig_case in orig_cases:
                # Every original case should have a corresponding cloned case
                # in the destination plan.
                # Same purpose to use last() as above to the correct cloned case.
                cloned_case = (
                    TestCase.objects.filter(summary=orig_case.summary, plan__in=[dest_plan])
                    .order_by("pk")
                    .last()
                )

                # Otherwise, there must be something wrong with the clone code.
                # So, make the test fail.
                if cloned_case is None:
                    self.fail(f"{orig_case} is not cloned into plan {dest_plan}.")

                self.assert_cloned_case(
                    orig_case,
                    cloned_case,
                    copy_case=copy_case,
                    copy_component=copy_component,
                    copy_attachment=copy_attachment,
                    keep_original_author=keep_original_author,
                    keep_original_default_tester=keep_original_default_tester,
                )

                # Assert sort key in test case plan relationship

                if orig_plan is None:
                    # If no original plan is specified, use the destination plan's
                    # sort key.
                    new_rel = TestCasePlan.objects.get(plan=dest_plan, case=cloned_case)
                    self.assertEqual(dest_plan.get_case_sortkey(), new_rel.sortkey)
                else:
                    # If original plan is specified, use the original sort key
                    # related to the original plan.
                    orig_rel = TestCasePlan.objects.filter(plan=orig_plan, case=orig_case).first()
                    new_rel = TestCasePlan.objects.get(plan=dest_plan, case=cloned_case)
                    if orig_rel:
                        self.assertEqual(orig_rel.sortkey, new_rel.sortkey)
                    else:
                        self.assertEqual(dest_plan.get_case_sortkey(), new_rel.sortkey)

    def test_keep_original_author(self):
        self._clone_cases(
            [self.plan_test_clone],
            [self.case],
            copy_case=True,
            keep_original_author=True,
        )

    def test_keep_original_default_tester(self):
        self._clone_cases(
            [self.plan_test_clone],
            [self.case],
            copy_case=True,
            keep_original_default_tester=True,
        )

    def test_copy_components(self):
        # copy_components only works when copying cases.
        self._clone_cases(
            [self.plan_test_clone, self.plan_test_clone_more],
            [self.case],
            copy_case=True,
            copy_component=True,
        )

    def test_copy_attachments(self):
        self._clone_cases(
            [self.plan_test_clone],
            [self.case, self.case_1],
            copy_case=True,
            copy_attachment=True,
        )

    def test_set_sort_key_for_cloned_case_by_using_orig_plan(self):
        self._clone_cases(
            [self.plan_test_clone, self.plan_test_clone_more],
            [self.case],
            orig_plan=self.case.plan.first(),
            copy_case=True,
        )

    def test_set_sort_key_for_linked_case_by_using_orig_plan(self):
        self._clone_cases(
            [self.plan_test_clone, self.plan_test_clone_more],
            [self.case],
            orig_plan=self.case.plan.first(),
            copy_case=False,
        )

    def test_create_new_plan_case_rel_sort_key_for_copy(self):
        """
        Test to generate a new sort key from destination plan even if
        from_plan is given, but the given from_plan has no relationship with
        the case to be cloned
        """
        self._clone_cases(
            [self.plan_test_clone, self.plan_test_clone_more],
            [self.case],
            orig_plan=self.orphan_plan,
            copy_case=True,
        )

    def test_create_new_plan_case_rel_sort_key_for_link(self):
        """
        Same as test test_create_new_plan_case_rel_sort_key_for_copy, but this
        test tests link rather than cloned
        """
        self._clone_cases(
            [self.plan_test_clone, self.plan_test_clone_more],
            [self.case],
            orig_plan=self.orphan_plan,
            copy_case=False,
        )

    @patch("tcms.testplans.models.TestPlan.get_case_sortkey")
    def test_clone_to_same_plan(self, get_case_sortkey):
        # Make it easier to assert the new sort key.
        get_case_sortkey.return_value = 100
        self._clone_cases([self.plan], [self.case, self.case_1, self.case_2], copy_case=True)


class TestSearchCases(BasePlanCase):
    """Test search view method"""

    @classmethod
    def setUpTestData(cls):
        """Setup data for test

        Besides those initial test cases created by base class, this test needs
        more cases in order to test switching other page.
        """
        super().setUpTestData()

        cls.functional_case = f.TestCaseCategoryFactory(name="Functional", product=cls.product)

        cls.case_2.category = cls.functional_case
        cls.case_2.priority = Priority.objects.get(value="P2")
        cls.case_2.save()
        cls.case_3.category = cls.functional_case
        cls.case_3.priority = Priority.objects.get(value="P5")
        cls.case_3.save()

        # Create more cases. The total number must greater than 25 due to 20 is
        # the default count per page.
        for i in range(20):
            f.TestCaseFactory(
                author=cls.tester,
                default_tester=None,
                reviewer=cls.tester,
                case_status=cls.case_status_confirmed,
                plan=[cls.plan],
            )

        cls.component_db = f.ComponentFactory(name="db", product=cls.product)

        f.TestCaseComponentFactory(case=cls.case_1, component=cls.component_db)
        f.TestCaseComponentFactory(case=cls.case_2, component=cls.component_db)
        f.TestCaseComponentFactory(case=cls.case_3, component=cls.component_db)
        f.TestCaseComponentFactory(case=cls.case_4, component=cls.component_db)

        cls.tag_python = f.TestTagFactory(name="python")
        cls.tag_fedora = f.TestTagFactory(name="fedora")

        cls.case_1.add_tag(cls.tag_python)
        cls.case_2.add_tag(cls.tag_python)
        cls.case_2.add_tag(cls.tag_fedora)
        cls.case_3.add_tag(cls.tag_python)
        cls.case_4.add_tag(cls.tag_fedora)

        cls.search_url = reverse("cases-search")

    def test_show_first_page_for_initial_query(self):
        resp = self.client.get(self.search_url, data={})
        self.assert200(resp)

        bs = BeautifulSoup(resp.content.decode("utf-8"), "html.parser")
        case_ids = [int(tr.find_all("td")[2].text) for tr in bs.table.tbody.find_all("tr")]

        expected_ids = list(
            TestCase.objects.values_list("pk", flat=True).order_by("-create_date")[0:20]
        )

        self.assertListEqual(expected_ids, case_ids)

    def test_show_first_page_for_query(self):
        resp = self.client.get(
            self.search_url, data={"priority": Priority.objects.get(value="P2").pk}
        )
        self.assert200(resp)

        bs = BeautifulSoup(resp.content.decode("utf-8"), "html.parser")
        case_ids = [int(tr.find_all("td")[2].text) for tr in bs.table.tbody.find_all("tr")]

        expected_ids = list(
            TestCase.objects.filter(priority__value="P2")
            .values_list("pk", flat=True)
            .order_by("-create_date")
        )
        self.assertListEqual(expected_ids, case_ids)

    def test_switch_to_another_page_order_by_pk(self):
        resp = self.client.get(
            self.search_url,
            data={
                "sEcho": 1,
                "iDisplayStart": 20,
                "iDisplayLength": 2,
                "iSortCol_0": 2,
                "sSortDir_0": "desc",
                "iSortingCols": 1,
                "bSortable_0": "true",
                "bSortable_1": "true",
                "bSortable_2": "true",
                "bSortable_3": "true",
            },
        )

        table_data = json.loads(resp.content)
        case_ids = [
            int(BeautifulSoup(item[2], "html.parser").text) for item in table_data["aaData"]
        ]

        expected_ids = list(TestCase.objects.values_list("pk", flat=True).order_by("-pk")[20:22])
        self.assertListEqual(expected_ids, case_ids)


class TestAddComponent(BasePlanCase):
    """Test AddComponentView"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.component_db = f.ComponentFactory(name="db", product=cls.product)
        cls.component_doc = f.ComponentFactory(name="doc", product=cls.product)
        cls.component_cli = f.ComponentFactory(name="cli", product=cls.product)
        cls.component_web = f.ComponentFactory(name="web", product=cls.product)

        cls.case_2.add_component(cls.component_db)
        cls.case_2.add_component(cls.component_cli)

    def setUp(self):
        super().setUp()
        user_should_have_perm(self.tester, "testcases.add_testcasecomponent")
        self.add_component_url = reverse("cases-add-component")

    def test_add_one_component(self):
        resp = self.client.post(
            self.add_component_url,
            {
                "product": self.product.pk,
                "case": self.case_1.pk,
                "o_component": [self.component_db.pk],
            },
        )

        self.assert200(resp)

        components = self.case_1.component.all()
        self.assertEqual(1, len(components))
        self.assertEqual(self.component_db, components[0])

    def test_add_multiple_components(self):
        resp = self.client.post(
            self.add_component_url,
            {
                "product": self.product.pk,
                "case": self.case_1.pk,
                "o_component": [self.component_db.pk, self.component_cli.pk],
            },
        )

        self.assert200(resp)

        components = self.case_1.component.order_by("name")
        self.assertEqual(2, len(components))
        self.assertEqual(self.component_cli, components[0])
        self.assertEqual(self.component_db, components[1])

    def test_avoid_duplicate_components(self):
        TestCaseComponent.objects.create(case=self.case_1, component=self.component_doc)

        resp = self.client.post(
            self.add_component_url,
            {
                "product": self.product.pk,
                "case": self.case_1.pk,
                "o_component": [self.component_doc.pk, self.component_cli.pk],
            },
        )

        self.assert200(resp)

        components = self.case_1.component.order_by("name")
        self.assertEqual(2, len(components))
        self.assertEqual(self.component_cli, components[0])
        self.assertEqual(self.component_doc, components[1])

    def test_invalid_arguments(self):
        from tcms.management.models import Component, Product

        result = Product.objects.aggregate(max_pk=Max("pk"))
        nonexisting_product_id = result["max_pk"] + 1

        result = Component.objects.aggregate(max_pk=Max("pk"))
        nonexisting_component_id = result["max_pk"] + 1

        resp = self.client.post(
            self.add_component_url,
            {
                "product": nonexisting_product_id,
                "case": self.case_1.pk,
                "o_component": [nonexisting_component_id],
            },
        )

        self.assert400(resp)

        data = json.loads(resp.content)
        msgs = sorted(data["message"])
        self.assertIn(f"Nonexistent component id(s) {nonexisting_component_id}", msgs[0])
        self.assertIn("Nonexistent product id", msgs[1])

    @patch("tcms.testcases.models.TestCase.add_component")
    def test_failed_to_add_component(self, add_component):
        add_component.side_effect = ValueError

        resp = self.client.post(
            self.add_component_url,
            {
                "product": self.product.pk,
                "case": self.case_2.pk,
                "o_component": [
                    self.component_doc.pk,
                    self.component_web.pk,
                ],
            },
        )

        self.assert400(resp)

        data = json.loads(resp.content)
        msgs = sorted(data["message"])
        case_id = self.case_2.pk
        self.assertIn(
            f"Failed to add component {self.component_doc.name} to case {case_id}",
            msgs[0],
        )
        self.assertIn(
            f"Failed to add component {self.component_web.name} to case {case_id}",
            msgs[1],
        )


class TestIssueManagement(BaseCaseRun):
    """Test add and remove issue to and from a test case"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.perm_add_issue = "issuetracker.add_issue"
        cls.perm_change_issue = "issuetracker.change_issue"
        cls.perm_delete_issue = "issuetracker.delete_issue"

        user_should_have_perm(cls.tester, cls.perm_change_issue)

        cls.add_issue_url = reverse("cases-add-issue", args=[cls.case_1.pk])
        cls.remove_issue_url = reverse("cases-delete-issue", args=[cls.case_1.pk])

        cls.fake_issue_key = "123456"

        cls.tracker_product = f.IssueTrackerProductFactory(name="BZ")
        cls.issue_tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            tracker_product=cls.tracker_product,
            validate_regex=r"^\d+$",
        )

        cls.disabled_tracker = f.IssueTrackerFactory(
            service_url="http://bz1.localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            tracker_product=cls.tracker_product,
            validate_regex=r"^\d+$",
            enabled=False,
        )

        # Used for testing removing issue from test case.
        cls.case_2_delete_issue_url = reverse("cases-delete-issue", args=[cls.case_2.pk])
        cls.case_2.add_issue("67890", cls.issue_tracker)
        cls.case_2.add_issue("78901", cls.issue_tracker)

    def tearDown(self):
        self.client.logout()
        remove_perm_from_user(self.tester, self.perm_add_issue)
        remove_perm_from_user(self.tester, self.perm_delete_issue)

    def test_bad_issue_key_to_remove(self):
        user_should_have_perm(self.tester, self.perm_delete_issue)

        resp = self.client.post(
            self.remove_issue_url,
            data={
                "issue_key": "",
                "case_run": self.case_run_1.pk,
            },
        )

        self.assert400(resp)
        self.assertIn("Missing issue key to delete.", resp.json()["message"])

    def test_bad_case_run_to_remove(self):
        user_should_have_perm(self.tester, self.perm_delete_issue)

        resp = self.client.post(
            self.remove_issue_url,
            data={
                # Whatever the issue key is, which does not impact this test.
                "issue_key": self.fake_issue_key,
                "case_run": 1000,
            },
        )

        self.assert400(resp)
        self.assertIn("Test case run does not exists.", resp.json()["message"])

    def test_bad_case_run_case_rel_to_remove(self):
        user_should_have_perm(self.tester, self.perm_delete_issue)

        resp = self.client.post(
            self.remove_issue_url,
            data={
                # Whatever the issue key is, which does not impact this test.
                "issue_key": self.fake_issue_key,
                "case_run": self.case_run_2.pk,
            },
        )

        self.assert400(resp)
        self.assertIn(
            f"Case run {self.case_run_2.pk} is not associated with case {self.case_1.pk}.",
            resp.json()["message"],
        )

    def test_no_permission_to_add(self):
        # Note that, required permission is not granted by default. Hence, the
        # request should be forbidden.
        resp = self.client.post(
            self.add_issue_url,
            data={
                # Whatever the issue key is, which does not impact this test.
                "issue_key": self.fake_issue_key,
                "tracker": self.issue_tracker.pk,
            },
        )
        self.assert403(resp)

    def test_no_permission_to_remove(self):
        # Note that, no permission is set for self.tester.
        resp = self.client.post(
            self.remove_issue_url,
            data={
                # Whatever the issue key is, which does not impact this test.
                "issue_key": self.fake_issue_key,
                "case_run": self.case_run_1.pk,
            },
        )
        self.assert403(resp)

    def test_add_an_issue(self):
        user_should_have_perm(self.tester, self.perm_add_issue)

        resp = self.client.post(
            self.add_issue_url,
            data={
                "issue_key": self.fake_issue_key,
                "case": self.case_1.pk,
                "tracker": self.issue_tracker.pk,
            },
        )

        self.assert200(resp)

        added_issue = Issue.objects.filter(
            issue_key=self.fake_issue_key, case=self.case_1, case_run__isnull=True
        ).first()

        self.assertIsNotNone(added_issue)
        self.assertIn(added_issue.get_absolute_url(), resp.json()["html"])

    def test_invalid_input_for_adding_an_issue(self):
        user_should_have_perm(self.tester, self.perm_add_issue)

        result = IssueTracker.objects.aggregate(max_pk=Max("pk"))
        resp = self.client.post(
            self.add_issue_url,
            data={"issue_key": self.fake_issue_key, "tracker": result["max_pk"] + 1},
        )

        self.assert400(resp)

        error_messages = sorted(resp.json()["message"])
        self.assertListEqual(["Invalid issue tracker that does not exist."], error_messages)

    @patch("tcms.testcases.models.TestCase.add_issue")
    def test_fail_if_case_add_issue_fails(self, add_issue):
        add_issue.side_effect = Exception("Something wrong")

        user_should_have_perm(self.tester, self.perm_add_issue)

        resp = self.client.post(
            self.add_issue_url,
            data={
                "issue_key": self.fake_issue_key,
                "tracker": self.issue_tracker.pk,
            },
        )

        self.assert400(resp)
        self.assertIn("Something wrong", resp.json()["message"])

    def test_fail_if_validation_error_occurs_while_adding_the_issue(self):
        user_should_have_perm(self.tester, self.perm_add_issue)

        resp = self.client.post(
            self.add_issue_url,
            data={
                # invalid issue key that should cause the validation error
                "issue_key": "abcdef1234",
                "tracker": self.issue_tracker.pk,
            },
        )

        self.assert400(resp)
        self.assertIn("Issue key abcdef1234 is in wrong format.", resp.json()["message"][0])

    def test_remove_an_issue(self):
        user_should_have_perm(self.tester, self.perm_delete_issue)

        # Assert later
        removed_issue_url = (
            Issue.objects.filter(issue_key="67890", case=self.case_2, case_run__isnull=True)
            .first()
            .get_absolute_url()
        )

        resp = self.client.post(
            self.case_2_delete_issue_url,
            data={
                "issue_key": "67890",
                "case": self.case_2.pk,
            },
        )

        self.assert200(resp)

        removed_issue = Issue.objects.filter(
            issue_key="67890", case=self.case_2, case_run__isnull=True
        ).first()

        self.assertIsNone(removed_issue)
        self.assertNotIn(removed_issue_url, resp.json()["html"])

        # There were two issues added to self.case_2. This issue should be
        # still there after removing the above one.

        remained_issue = Issue.objects.filter(
            issue_key="78901", case=self.case_2, case_run__isnull=True
        ).first()

        self.assertIsNotNone(remained_issue)
        self.assertIn(remained_issue.get_absolute_url(), resp.json()["html"])

    def test_bad_request_if_case_not_exist(self):
        user_should_have_perm(self.tester, self.perm_add_issue)

        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        case_id = result["max_pk"] + 1
        url = reverse("cases-add-issue", args=[case_id])

        resp = self.client.post(
            url,
            data={
                "issue_key": self.fake_issue_key,
                "tracker": self.issue_tracker.pk,
            },
        )

        self.assert400(resp)
        self.assertIn(f"Test case {case_id} does not exist.", resp.json()["message"])

    def test_bad_request_if_an_issue_tracker_is_not_enabled(self):
        user_should_have_perm(self.tester, self.perm_add_issue)

        url = reverse("cases-add-issue", args=[self.case_1.pk])

        resp = self.client.post(
            url,
            data={
                "issue_key": self.fake_issue_key,
                "tracker": self.disabled_tracker.pk,
            },
        )

        self.assert400(resp)
        self.assertIn(
            f'Issue tracker "{self.disabled_tracker.name}" is not enabled',
            resp.json()["message"],
        )


class TestNewCase(BasePlanCase):
    """Test create a new case"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super(TestNewCase, cls).setUpTestData()
        cls.tag_fedora = f.TestTagFactory(name="fedora")
        cls.tag_python = f.TestTagFactory(name="python")

        cls.component_db = f.ComponentFactory(name="db", product=cls.product)
        cls.component_web = f.ComponentFactory(name="web", product=cls.product)

        user_should_have_perm(cls.tester, "testcases.add_testcase")

    def setUp(self):
        super().setUp()
        self.new_case_url = reverse("cases-new")

    def test_open_page(self):
        """Test open the page to create a new case"""
        resp = self.client.get(self.new_case_url, data={"from_plan": self.plan.pk})
        self.assert200(resp)

        # More assertions on the content to ensure the rendered page is correct.

    def assert_new_case_creation(
        self, estimated_time: str = "0m", from_plan: int = None, next_action: str = None
    ) -> None:
        category = TestCaseCategory.objects.all()[0]
        priority = Priority.objects.all()[0]

        post_data = {
            "product": str(self.product.pk),
            "summary": "Test case: create a new test case",
            "is_automated": "0",
            "script": "",
            "arguments": "",
            "extra_link": "https://localhost/case-2",
            "requirement": "",
            "alias": "alias",
            "estimated_time": estimated_time,
            "category": category.pk,
            "priority": priority.pk,
            "default_tester": "",
            "notes": "",
            "tag": f"{self.tag_fedora.name},{self.tag_python.name}",
            "component": [self.component_db.pk, self.component_web.pk],
            "action": "",
            "effect": "",
            "setup": "",
            "breakdown": "",
        }
        if from_plan is not None:
            post_data["from_plan"] = (str(from_plan),)
        if next_action:
            post_data[next_action] = "Next action after case is created"

        resp = self.client.post(self.new_case_url, data=post_data)

        new_case = TestCase.objects.filter(summary=post_data["summary"]).first()
        self.assertIsNotNone(new_case)

        if next_action == "continue":
            url = reverse("case-edit", args=[new_case.pk])
            if from_plan is None:
                self.assertRedirects(resp, url, fetch_redirect_response=False)
            else:
                self.assertRedirects(
                    resp, f"{url}?from_plan={from_plan}", fetch_redirect_response=False
                )
        elif next_action == "addanother":
            self.assert200(resp)
        elif next_action == "returntocase":
            url = reverse("case-get", args=[new_case.pk])
            if from_plan is None:
                self.assertRedirects(
                    resp, f"{url}?from_plan={from_plan}", fetch_redirect_response=False
                )
            else:
                self.assertRedirects(resp, url, fetch_redirect_response=False)
        elif next_action == "returntoplan":
            if from_plan is None:
                self.assert404(resp)
            else:
                url = reverse("plan-get", args=[from_plan])
                self.assertRedirects(resp, f"{url}#reviewcases", fetch_redirect_response=False)

        # Prepare expected properties for assertion
        expected = post_data.copy()
        expected["is_automated"] = False
        expected["is_automated_proposed"] = False
        expected["product"] = self.product
        expected["category"] = category
        expected["priority"] = priority
        expected["default_tester"] = None
        expected["estimated_time"] = timedelta(timedelta2int(post_data["estimated_time"]))
        expected["case_status"] = TestCaseStatus.objects.get(name="PROPOSED")
        expected["tag"] = [self.tag_fedora, self.tag_python]
        expected["component"] = [self.component_db, self.component_web]

        assert_new_case(new_case, expected)

        new_case.delete()

    def test_create_a_new_case(self):
        """Test new case creation and redirect to the new case page"""
        self.assert_new_case_creation()
        self.assert_new_case_creation(from_plan=self.plan.pk)

    def test_save_and_continue_editing(self):
        self.assert_new_case_creation(next_action="_continue")
        self.assert_new_case_creation(from_plan=self.plan.pk, next_action="_continue")

    def test_save_and_add_another_one(self):
        self.assert_new_case_creation(next_action="_addanother")
        self.assert_new_case_creation(from_plan=self.plan.pk, next_action="_addanother")

    def test_save_and_return_plan(self):
        self.assert_new_case_creation(next_action="_returntoplan")
        self.assert_new_case_creation(from_plan=self.plan.pk, next_action="_returntoplan")

    def test_empty_estimated_time(self):
        self.assert_new_case_creation(estimated_time="")


class TestTextHistory(test.TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.case = f.TestCaseFactory()
        cls.case.add_text(action="abc", effect="def", setup="uvw", breakdown="xyz")
        cls.case.add_text(action="123", effect="456", setup="789", breakdown="010")
        cls.url = reverse("case-text-history", args=[cls.case.pk])

    def test_open_page(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "<h2>Test Case History</h2>", html=True)

    def test_open_page_with_specific_text_version(self):
        resp = self.client.get(f"{self.url}?case_text_version=2")
        self.assertContains(resp, "<h2>Test Case History</h2>", html=True)
        self.assertContains(resp, "<b>SETUP:</b>", html=True)
        self.assertContains(resp, "789")
        self.assertContains(resp, "<b>ACTION:</b>", html=True)
        self.assertContains(resp, "123")
        self.assertContains(resp, "<b>EXPECTED RESULT:</b>", html=True)
        self.assertContains(resp, "456")
        self.assertContains(resp, "<b>BREAKDOWN:</b>", html=True)
        self.assertContains(resp, "010")


class TestCalculationForTestCase(BasePlanCase):
    """Test calculate_for_testcases"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.orphan_case = f.TestCaseFactory(summary="Orphan case")

        cls.cool_plan = f.TestPlanFactory(
            name="Cool test plan",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )
        f.TestCasePlanFactory(plan=cls.cool_plan, case=cls.case_1)

    def test_calculate_for_cases(self):
        result = calculate_for_testcases(self.plan, [self.case_1, self.case_2])

        for case in result:
            rel = TestCasePlan.objects.get(plan=self.plan, case=case)
            self.assertEqual(rel.sortkey, case.cal_sortkey)
            self.assertEqual(rel.pk, case.cal_testcaseplan_pk)

    def test_calculate_for_empty_cases(self):
        result = calculate_for_testcases(self.plan, [])
        self.assertListEqual([], result)

    def test_part_of_cases_are_not_associated_with_the_plan(self):
        result = calculate_for_testcases(self.plan, [self.case_1, self.orphan_case])

        for case in result:
            rel = TestCasePlan.objects.filter(plan=self.plan, case=case).first()
            if rel is None:
                self.assertIsNone(case.cal_sortkey)
                self.assertIsNone(case.cal_testcaseplan_pk)
            else:
                self.assertEqual(rel.sortkey, case.cal_sortkey)
                self.assertEqual(rel.pk, case.cal_testcaseplan_pk)


class BaseTestCaseView(test.TestCase):
    """Base class of test case view in a plan page"""

    @classmethod
    def setUpTestData(cls):
        cls.case = f.TestCaseFactory(
            summary="Show the simple test case",
            notes="Some notes",
        )
        cls.case.add_text(action="action", effect="effect", setup="setup", breakdown="breakdown")
        cls.case.add_component(f.ComponentFactory(name="db"))
        cls.case.add_component(f.ComponentFactory(name="web"))
        cls.case.add_tag(f.TestTagFactory(name="python"))
        cls.case.add_tag(f.TestTagFactory(name="tcms"))
        cls.case.add_tag(f.TestTagFactory(name="django"))

        cls.attachment_logo = f.TestAttachmentFactory(file_name="logo.png")
        f.TestCaseAttachmentFactory(case=cls.case, attachment=cls.attachment_logo)

        add_comment(cls.case.author, "testcases.testcase", [cls.case.pk], "first comment")
        add_comment(cls.case.author, "testcases.testcase", [cls.case.pk], "second comment")
        add_comment(cls.case.author, "testcases.testcase", [cls.case.pk], "third comment")

        cls.first_comment = Comment.objects.get(comment="first comment")
        cls.second_comment = Comment.objects.get(comment="second comment")
        cls.third_comment = Comment.objects.get(comment="third comment")

    def assert_case_content(self, response):
        expected_content = [
            '<div class="content">action</div>',
            '<div class="content">effect</div>',
            '<div class="content">setup</div>',
            '<div class="content">breakdown</div>',
            '<li class="grey">No issue found</li>',
            '<ul class="ul-no-format"><li>python</li><li>tcms</li><li>django</li></ul>',
            '<ul class="ul-no-format">'
            '<li id="display_component" >db</li>'
            '<li id="display_component" >web</li>'
            "</ul>",
            f'<ul class="ul-no-format"><li>'
            f'<a href="{reverse("check-file", args=[self.attachment_logo.pk])}">'
            f"{self.attachment_logo.file_name}"
            f"</a></li></ul>",
        ]

        for item in expected_content:
            self.assertContains(response, item, html=True)

    def assert_nonexisting_case_content(self, response):
        expected_content = [
            '<h4>Actions:</h4><div class="content"></div>',
            '<h4>Setup:</h4><div class="content"></div>',
            '<h4>Breakdown:</h4><div class="content"></div>',
            '<h4>Expected Results:</h4><div class="content"></div>',
            '<ul class="ul-no-format"><li class="grey">No tag found</li></ul>',
            '<ul class="ul-no-format">' '<li class="grey">No issue found</li>' "</ul>",
            '<ul class="ul-no-format">' '<li class="grey">No component found</li>' "</ul>",
            '<ul class="ul-no-format">' '<li class="grey">No attachment found</li>' "</ul>",
        ]

        for item in expected_content:
            self.assertContains(response, item, html=True)


class TestSimpleTestCaseView(BaseTestCaseView):
    """Test the SimpleTestCaseView"""

    def assert_comments(self, response, comments):
        expected_content = render_to_string(
            "case/comments_in_simple_case_pane.html", context={"comments": comments}
        )
        self.assertContains(response, expected_content, html=True)

    def test_show_the_case(self):
        url = reverse("case-readonly-pane", args=[self.case.pk])
        resp = self.client.get(url)

        self.assert_case_content(resp)
        self.assertContains(
            resp,
            f"<h4>Notes:</h4>" f'<div class="content">{self.case.notes}</div>',
            html=True,
        )
        self.assert_comments(resp, [self.first_comment, self.second_comment, self.third_comment])

    def test_nonexisting_case(self):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        url = reverse("case-readonly-pane", args=[result["max_pk"] + 1])
        resp = self.client.get(url)

        self.assert_nonexisting_case_content(resp)
        self.assertContains(resp, '<h4>Notes:</h4><div class="content"></div>', html=True)
        self.assert_comments(resp, [])


class TestCaseReviewPaneView(BaseTestCaseView):
    """Test view TestCaseReviewPaneView"""

    def assert_comments(self, response, comments):
        expected_content = render_to_string(
            "case/comments_of_reviewing_cases.html", context={"comments": comments}
        )
        self.assertContains(response, expected_content, html=True)

    def assert_change_log(self, response):
        logs = TCMSLogModel.objects.for_model(self.case).order_by("date")
        expected_content = render_to_string(
            "case/get_details_case_log.html", context={"logs": logs}
        )
        self.assertContains(response, expected_content, html=True)

    def test_show_the_case(self):
        url = reverse("case-review-pane", args=[self.case.pk])
        resp = self.client.get(url)

        self.assert_case_content(resp)
        self.assert_comments(resp, [self.first_comment, self.second_comment, self.third_comment])
        self.assert_change_log(resp)

    def test_nonexisting_case(self):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        url = reverse("case-review-pane", args=[result["max_pk"] + 1])
        resp = self.client.get(url)

        self.assert_nonexisting_case_content(resp)
        self.assert_comments(resp, [])
        self.assert_change_log(resp)


class TestCaseCaseRunListPaneView(BaseCaseRun):
    """Test view class TestCaseCaseRunListPaneView"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        add_comment(cls.tester, "testruns.testcaserun", [cls.case_run_1.pk], "first comment")
        add_comment(cls.tester, "testruns.testcaserun", [cls.case_run_1.pk], "second comment")

    def test_get_the_list(self):
        url = reverse("caserun-list-pane", args=[self.case_1.pk])
        resp = self.client.get(url, data={"plan_id": self.plan.pk})

        case_runs = TestCaseRun.objects.filter(
            case=self.case_1, run__plan=self.plan
        ).select_related("run")

        for case_run in case_runs:
            run = case_run.run
            run_url = reverse("run-get", args=[run.pk])
            expected_content = [
                f'<td><a href="{run_url}">{run.pk}</a></td>',
                f'<td class="expandable"><p>{run.summary}</p></td>',
                # the number of comments
                '<td class="expandable"><img src="/static/images/comment.png"'
                ' style="vertical-align: middle;">2</td>',
            ]
            for item in expected_content:
                self.assertContains(resp, item, html=True)

    def test_irrelative_plan_id(self):
        url = reverse("caserun-list-pane", args=[self.case_1.pk])
        result = TestPlan.objects.aggregate(max_pk=Max("pk"))
        resp = self.client.get(url, data={"plan_id": result["max_pk"] + 1})

        self.assertContains(resp, "<tbody></tbody>", html=True)


def format_date(dt: datetime) -> str:
    """Format datetime to string using in the Django way"""
    return Template("{{ submit_date }}").render(Context({"submit_date": dt}))


class TestCaseSimpleCaseRunView(BaseCaseRun):
    """Test view TestCaseSimpleCaseRunView"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_run_1.notes = "Some notes"
        cls.case_run_1.save()

        with patch("django.utils.timezone.now") as mock_now:
            cls.submit_date = datetime(2020, 1, 22, 19, 47, 30)
            mock_now.return_value = cls.submit_date
            add_comment(cls.tester, "testruns.testcaserun", [cls.case_run_1.pk], "first comment")

        with patch("django.utils.timezone.now") as mock_now:
            cls.submit_date_later = cls.submit_date + timedelta(minutes=10)
            mock_now.return_value = cls.submit_date_later
            add_comment(
                cls.tester,
                "testruns.testcaserun",
                [cls.case_run_1.pk],
                "second comment",
            )

    def test_get_the_view(self):
        url = reverse("caserun-simple-pane", args=[self.case_1.pk])
        resp = self.client.get(url, data={"case_run_id": self.case_run_1.pk})

        expected_content = [
            f"<p>{self.case_run_1.notes}</p>",
            f"<li>"
            f'<span class="strong">#1</span>'
            f'<span class="strong">{self.tester.email}</span>'
            f'<span class="grey">{format_date(self.submit_date)}</span><br/>'
            f"first comment"
            f"</li>",
            f"<li>"
            f'<span class="strong">#2</span>'
            f'<span class="strong">{self.tester.email}</span>'
            f'<span class="grey">{format_date(self.submit_date_later)}</span><br/>'
            f"second comment"
            f"</li>",
            # FIXME: assert change logs after the template is fixed to show
            #        change log content
        ]
        for item in expected_content:
            self.assertContains(resp, item, html=True)

    def test_show_empty_content(self):
        url = reverse("caserun-simple-pane", args=[self.case_2.pk])
        resp = self.client.get(url, data={"case_run_id": self.case_run_2.pk})

        expected_content = [
            f"<p>{self.case_run_2.notes}</p>",
            '<li class="grey" style="border:none;margin:0px;padding:0px">'
            "No comments found.</li>",
            '<td colspan="5" class="empty-message-row">No logs.</td>',
        ]
        for item in expected_content:
            self.assertContains(resp, item, html=True)

    def test_404_if_case_run_id_is_invalid(self):
        url = reverse("caserun-simple-pane", args=[self.case.pk])
        resp = self.client.get(url, data={"case_run_id": "abc"})
        self.assert400(resp)

    def test_404_if_case_and_case_run_are_not_associated(self):
        url = reverse("caserun-simple-pane", args=[self.case.pk])
        resp = self.client.get(url, data={"case_run_id": self.case_run_2.pk})
        self.assert404(resp)

    def test_404_if_case_run_id_does_not_exist(self):
        url = reverse("caserun-simple-pane", args=[self.case.pk])
        result = TestCaseRun.objects.aggregate(max_pk=Max("pk"))
        resp = self.client.get(url, data={"case_run_id": result["max_pk"] + 1})
        self.assert404(resp)

    def test_404_if_missing_case_run_id(self):
        url = reverse("caserun-simple-pane", args=[self.case.pk])
        resp = self.client.get(url)
        self.assert400(resp)


class TestCaseCaseRunDetailPanelView(BaseCaseRun):
    """Test TestCaseCaseRunDetailPanelView"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_1.add_text(action="123", effect="456", setup="789", breakdown="010")
        cls.case_1.add_text(action="abc", effect="def", setup="ghi", breakdown="jkl")

        cls.case_1.add_component(f.ComponentFactory(name="db"))
        cls.case_1.add_component(f.ComponentFactory(name="web"))
        cls.case_1.add_component(f.ComponentFactory(name="dist"))

        cls.case_1.add_tag(f.TestTagFactory(name="python"))
        cls.case_1.add_tag(f.TestTagFactory(name="webapp"))

        cls.attachment_logo = f.TestAttachmentFactory(file_name="logo.png")
        f.TestCaseAttachmentFactory(case=cls.case_1, attachment=cls.attachment_logo)
        cls.attachment_screenshort = f.TestAttachmentFactory(file_name="screenshot.png")
        f.TestCaseAttachmentFactory(case=cls.case_1, attachment=cls.attachment_screenshort)

        add_comment(cls.tester, "testruns.testcaserun", [cls.case_run_1.pk], "start the test")
        add_comment(cls.tester, "testruns.testcaserun", [cls.case_run_1.pk], "mark failed")

        cls.first_comment = Comment.objects.get(comment="start the test")
        cls.second_comment = Comment.objects.get(comment="mark failed")

        cls.case_run_1.log_action(
            who=cls.tester,
            field="case_run_status",
            new_value="idle",
            original_value="running",
        )
        cls.case_run_1.log_action(
            who=cls.tester,
            field="case_run_status",
            new_value="running",
            original_value="failed",
        )

        cls.first_log = TCMSLogModel.objects.get(new_value="idle", original_value="running")
        cls.second_log = TCMSLogModel.objects.get(new_value="running", original_value="failed")

    def test_404_if_case_and_case_run_are_not_associated(self):
        case_run = self.case_run_1
        # Note that, self.case_run_1 is not created from self.case_2
        url = reverse("caserun-detail-pane", args=[self.case_2.pk])
        resp = self.client.get(url, data={"case_run_id": case_run.pk, "case_text_version": 1})
        self.assert404(resp)

    def test_invalid_argument_case_run_id(self):
        invalid_args = [
            {"case_text_version": 1},
            {"case_run_id": "", "case_text_version": 1},
            {"case_run_id": "pk", "case_text_version": 1},
        ]
        url = reverse("caserun-detail-pane", args=[self.case_1.pk])
        for args in invalid_args:
            resp = self.client.get(url, data=args)
            self.assert400(resp)

    def test_invalid_argument_case_text_version(self):
        invalid_args = [
            {"case_run_id": 1},
            {"case_run_id": 1, "case_text_version": ""},
            {"case_run_id": 1, "case_text_version": "i"},
        ]
        url = reverse("caserun-detail-pane", args=[self.case_1.pk])
        for args in invalid_args:
            resp = self.client.get(url, data=args)
            self.assert400(resp)

    def test_show_with_some_empty_content(self):
        case_run = self.case_run_2
        url = reverse("caserun-detail-pane", args=[case_run.case.pk])
        resp = self.client.get(url, data={"case_run_id": case_run.pk, "case_text_version": 1})

        expected_content = [
            f'<ul class="comment" id="comment{case_run.pk}" style="display:none;"></ul>',
            '<ul class="ul-no-format"><li class="grey">No bug found</li></ul>',
            '<ul><li class="grey">No log recorded.</li></ul>',
            '<ul class="ul-no-format"><li class="grey">No attachment found</li></ul>',
            '<ul class="ul-no-format"><li class="grey">No component found</li></ul>',
            '<ul class="ul-no-format"><li class="grey">No tag found</li></ul>',
            '<h4 class="borderB">Test Log <span>'
            '[<a href="javascript:void(0);" class="js-add-testlog">Add</a>]'
            "</span></h4>"
            '<div class="content"><ul class="ul-format"></ul></div>',
            '<h4>Actions</h4><div class="content"></div>',
            '<h4>Breakdown</h4><div class="content"></div>',
            '<h4>Actions</h4><div class="content"></div>',
            '<h4>Expected Results</h4><div class="content"></div>',
        ]

        for item in expected_content:
            self.assertContains(resp, item, html=True)

    def test_show_case_run_detailed_info(self):
        case_run = self.case_run_1
        url = reverse("caserun-detail-pane", args=[case_run.case.pk])
        resp = self.client.get(url, data={"case_run_id": case_run.pk, "case_text_version": 2})

        expected_content = [
            '<h4>Actions</h4><div class="content">abc</div>',
            '<h4>Expected Results</h4><div class="content">def</div>',
            '<h4>Setup</h4><div class="content">ghi</div>',
            '<h4>Breakdown</h4><div class="content">jkl</div>',
            # Assert change logs
            f'<ul id="changeLog{case_run.pk}" style="display:none;">'
            f"<li>"
            f"<span>{format_date(self.first_log.date)}</span>"
            f"<span>{self.first_log.who.username}</span><br />"
            f"Field {self.first_log.field} changed "
            f"from {self.first_log.original_value} to {self.first_log.new_value}"
            f"</li>"
            f"<li>"
            f"<span>{format_date(self.second_log.date)}</span>"
            f"<span>{self.second_log.who.username}</span><br />"
            f"Field {self.second_log.field} changed "
            f"from {self.second_log.original_value} to {self.second_log.new_value}"
            f"</li>"
            f"</ul>",
            # Assert comments history list
            f'<ul class="comment" id="comment{case_run.pk}" style="display:none;">'
            f"<li>"
            f"<span>#1</span>"
            f"<span>{self.first_comment.user.email}</span>"
            f"<span>{format_date(self.first_comment.submit_date)}</span>"
            f"<div>"
            f"{self.first_comment.comment}"
            f"<br></div></li>"
            f"<li>"
            f"<span>#2</span>"
            f"<span>{self.second_comment.user.email}</span>"
            f"<span>{format_date(self.second_comment.submit_date)}</span>"
            f"<div>"
            f"{self.second_comment.comment}"
            f"<br></div></li>"
            f"</ul>",
            f'<ul class="ul-no-format">'
            f"<li>"
            f'<a href="{reverse("check-file", args=[self.attachment_logo.pk])}">'
            f"{self.attachment_logo.file_name}"
            f"</a></li>"
            f"<li>"
            f'<a href="{reverse("check-file", args=[self.attachment_screenshort.pk])}">'
            f"{self.attachment_screenshort.file_name}"
            f"</a></li>"
            f"</ul>",
            '<ul class="ul-no-format"><li>db</li><li>dist</li><li>web</li></ul>',
            '<ul class="ul-no-format"><li>python</li><li>webapp</li></ul>',
        ]

        for item in expected_content:
            self.assertContains(resp, item, html=True)


class TestSubTotalByStatusView(BasePlanCase):
    """Test view cases-subtotal-by-status"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        status_proposed = TestCaseStatus.objects.get(name="PROPOSED")
        status_need_update = TestCaseStatus.objects.get(name="NEED_UPDATE")

        cls.case_1.case_status = status_proposed
        cls.case_1.save()
        cls.case_2.case_status = status_proposed
        cls.case_2.save()
        cls.case_3.case_status = status_need_update
        cls.case_3.save()

        # Note that, no DISABLED cases

        cls.another_plan = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        f.TestCaseFactory(
            case_status=status_need_update,
            author=cls.tester,
            default_tester=cls.tester,
            reviewer=cls.tester,
            plan=[cls.another_plan],
        )
        f.TestCaseFactory(
            case_status=status_proposed,
            author=cls.tester,
            default_tester=cls.tester,
            reviewer=cls.tester,
            plan=[cls.another_plan],
        )

        cls.third_plan = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )
        f.TestCaseFactory(
            case_status=status_proposed,
            author=cls.tester,
            default_tester=cls.tester,
            reviewer=cls.tester,
            plan=[cls.third_plan],
        )

        cls.plan_without_cases = f.TestPlanFactory()

        cls.url = reverse("cases-subtotal-by-status")

    def _construct_expected_result(
        self, proposed=0, confirmed=0, need_update=0, disabled=0, total=0
    ):
        return {
            "raw": {
                "PROPOSED": proposed,
                "CONFIRMED": confirmed,
                "DISABLED": disabled,
                "NEED_UPDATE": need_update,
            },
            "confirmed_cases": confirmed,
            "reviewing_cases": proposed + disabled + need_update,
            "total": total,
        }

    def test_plan_has_no_case(self):
        resp = self.client.get(self.url, data={"plan": self.plan_without_cases.pk})
        self.assertJsonResponse(resp, self._construct_expected_result())

    def test_subtotal_by_plan_ids(self):
        resp = self.client.get(self.url, data={"plan": [self.plan.pk, self.another_plan.pk]})
        self.assertJsonResponse(
            resp,
            self._construct_expected_result(
                proposed=3, confirmed=4, need_update=2, disabled=0, total=9
            ),
        )

    def test_no_plan_is_given(self):
        resp = self.client.get(self.url)
        # All test cases should be included. One more proposed case.
        self.assertJsonResponse(
            resp,
            self._construct_expected_result(
                proposed=4, confirmed=4, need_update=2, disabled=0, total=10
            ),
        )

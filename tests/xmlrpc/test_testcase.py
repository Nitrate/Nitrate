# -*- coding: utf-8 -*-

import itertools
import operator
from datetime import timedelta
from unittest.mock import PropertyMock, patch

from django import test
from django.db.models import Max, Min
from django_comments.models import Comment

from tcms.core.utils import checksum
from tcms.issuetracker.models import Issue
from tcms.management.models import Component, Priority, TestTag
from tcms.testcases.models import (
    TestCase,
    TestCaseComponent,
    TestCasePlan,
    TestCaseStatus,
    TestCaseTag,
)
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestCaseRun, TestRun
from tcms.xmlrpc.api import testcase as XmlrpcTestCase
from tcms.xmlrpc.serializer import datetime_to_str
from tcms.xmlrpc.utils import pre_process_ids
from tests import factories as f
from tests.xmlrpc.utils import XmlrpcAPIBaseTest, make_http_request


class TestNotificationRemoveCC(test.TestCase):
    """Tests the XML-RPC testcase.notication_remove_cc method"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory()
        cls.http_req = make_http_request(user=cls.user, user_perm="testcases.change_testcase")

        cls.default_cc = "example@MrSenko.com"
        cls.testcase = f.TestCaseFactory()
        cls.testcase.emailing.add_cc(cls.default_cc)

    def test_remove_existing_cc(self):
        # initially testcase has the default CC listed
        # and we issue XMLRPC request to remove the cc
        XmlrpcTestCase.notification_remove_cc(self.http_req, self.testcase.pk, [self.default_cc])

        # now verify that the CC email has been removed
        self.assertEqual(0, self.testcase.emailing.cc_list.count())


class TestUnlinkPlan(test.TestCase):
    """Test the XML-RPC method testcase.unlink_plan()"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory()
        cls.http_req = make_http_request(user=cls.user, user_perm="testcases.delete_testcaseplan")

        cls.testcase_1 = f.TestCaseFactory()
        cls.testcase_2 = f.TestCaseFactory()
        cls.plan_1 = f.TestPlanFactory()
        cls.plan_2 = f.TestPlanFactory()

        cls.testcase_1.add_to_plan(cls.plan_1)

        cls.testcase_2.add_to_plan(cls.plan_1)
        cls.testcase_2.add_to_plan(cls.plan_2)

    def test_unlink_plan_from_case_with_single_plan(self):
        result = XmlrpcTestCase.unlink_plan(self.http_req, self.testcase_1.pk, self.plan_1.pk)
        self.assertEqual(0, self.testcase_1.plan.count())
        self.assertEqual([], result)

    def test_unlink_plan_from_case_with_two_plans(self):
        result = XmlrpcTestCase.unlink_plan(self.http_req, self.testcase_2.pk, self.plan_1.pk)
        self.assertEqual(1, self.testcase_2.plan.count())
        self.assertEqual(1, len(result))
        self.assertEqual(self.plan_2.pk, result[0]["plan_id"])


class TestLinkPlan(XmlrpcAPIBaseTest):
    """Test the XML-RPC method testcase.link_plan()"""

    permission = "testcases.add_testcaseplan"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.testcase_1 = f.TestCaseFactory()
        cls.testcase_2 = f.TestCaseFactory()
        cls.testcase_3 = f.TestCaseFactory()

        cls.plan_1 = f.TestPlanFactory()
        cls.plan_2 = f.TestPlanFactory()
        cls.plan_3 = f.TestPlanFactory()

        # case 1 is already linked to plan 1
        cls.testcase_1.add_to_plan(cls.plan_1)

    def test_insert_ignores_existing_mappings(self):
        plans = [self.plan_1.pk, self.plan_2.pk, self.plan_3.pk]
        cases = [self.testcase_1.pk, self.testcase_2.pk, self.testcase_3.pk]
        XmlrpcTestCase.link_plan(self.request, cases, plans)

        # no duplicates for plan1/case1 were created
        self.assertTrue(
            TestCasePlan.objects.filter(plan=self.plan_1.pk, case=self.testcase_1.pk).exists()
        )

        # verify all case/plan combinations exist
        for plan_id, case_id in itertools.product(plans, cases):
            self.assertTrue(TestCasePlan.objects.filter(plan=plan_id, case=case_id).exists())

    def test_case_ids_do_not_exist(self):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        max_case_id = result["max_pk"]

        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.link_plan,
            self.request,
            [max_case_id + 1, max_case_id + 2],
            [self.plan_1.pk],
        )

        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.link_plan, self.request, max_case_id + 1, [self.plan_1.pk]
        )

    def test_plan_ids_do_not_exist(self):
        result = TestPlan.objects.aggregate(max_pk=Max("pk"))
        max_plan_id = result["max_pk"]

        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.link_plan,
            self.request,
            [self.testcase_1.pk, self.testcase_2.pk],
            [max_plan_id + 1, max_plan_id + 2],
        )

        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.link_plan,
            self.request,
            [self.testcase_1.pk, self.testcase_2.pk],
            max_plan_id + 1,
        )


class TestGet(test.TestCase):
    """Test XML-RPC testcase.get"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory()
        cls.http_req = make_http_request(user=cls.user)
        cls.reviewer = f.UserFactory(username="reviewer")

        cls.plan_1 = f.TestPlanFactory()
        cls.plan_2 = f.TestPlanFactory()

        cls.status = TestCaseStatus.objects.get(name="CONFIRMED")
        cls.priority = Priority.objects.get(value="P2")
        cls.category = f.TestCaseCategoryFactory(name="fast")
        cls.case = f.TestCaseFactory(
            priority=cls.priority,
            case_status=cls.status,
            category=cls.category,
            author=cls.user,
            default_tester=cls.user,
            reviewer=cls.reviewer,
        )
        cls.tag_fedora = f.TestTagFactory(name="fedora")
        cls.tag_python = f.TestTagFactory(name="python")
        cls.case.add_tag(cls.tag_fedora)
        cls.case.add_tag(cls.tag_python)

        f.TestCasePlanFactory(plan=cls.plan_1, case=cls.case)
        f.TestCasePlanFactory(plan=cls.plan_2, case=cls.case)

    def test_get_a_case(self):
        resp = XmlrpcTestCase.get(self.http_req, self.case.pk)
        resp["tag"].sort()
        resp["plan"].sort()

        expected_resp = {
            "case_id": self.case.pk,
            "summary": self.case.summary,
            "create_date": datetime_to_str(self.case.create_date),
            "is_automated": self.case.is_automated,
            "is_automated_proposed": self.case.is_automated_proposed,
            "script": "",
            "arguments": "",
            "extra_link": None,
            "requirement": "",
            "alias": "",
            "estimated_time": "00:00:00",
            "notes": "",
            "case_status_id": self.status.pk,
            "case_status": self.status.name,
            "category_id": self.category.pk,
            "category": self.category.name,
            "author_id": self.user.pk,
            "author": self.user.username,
            "default_tester_id": self.user.pk,
            "default_tester": self.user.username,
            "priority": self.priority.value,
            "priority_id": self.priority.pk,
            "reviewer_id": self.reviewer.pk,
            "reviewer": self.reviewer.username,
            "text": {},
            "tag": ["fedora", "python"],
            "attachments": [],
            "plan": [self.plan_1.pk, self.plan_2.pk],
            "component": [],
        }
        self.assertEqual(expected_resp, resp)


class TestAttachIssue(XmlrpcAPIBaseTest):
    """Test attach_issue"""

    permission = "issuetracker.add_issue"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case = f.TestCaseFactory()
        cls.tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            validate_regex=r"^\d+$",
        )

    def test_attach_an_issue(self):
        XmlrpcTestCase.attach_issue(
            self.request,
            {
                "case": self.case.pk,
                "issue_key": "123456",
                "tracker": self.tracker.pk,
                "summary": "XMLRPC fails",
            },
        )

        issue = Issue.objects.filter(
            issue_key="123456",
            tracker=self.tracker.pk,
            case=self.case.pk,
            case_run__isnull=True,
        ).first()

        self.assertIsNotNone(issue)
        self.assertEqual("XMLRPC fails", issue.summary)

    def test_attach_some_issues(self):
        XmlrpcTestCase.attach_issue(
            self.request,
            [
                {
                    "case": self.case.pk,
                    "issue_key": "123456",
                    "tracker": self.tracker.pk,
                    "summary": "XMLRPC fails",
                },
                {
                    "case": self.case.pk,
                    "issue_key": "789012",
                    "tracker": self.tracker.pk,
                    "summary": "abc",
                },
            ],
        )

        issue = Issue.objects.filter(
            issue_key="123456",
            tracker=self.tracker.pk,
            case=self.case.pk,
            case_run__isnull=True,
        ).first()

        self.assertIsNotNone(issue)
        self.assertEqual("XMLRPC fails", issue.summary)

        issue = Issue.objects.filter(
            issue_key="789012",
            tracker=self.tracker.pk,
            case=self.case.pk,
            case_run__isnull=True,
        ).first()

        self.assertIsNotNone(issue)
        self.assertEqual("abc", issue.summary)

    def test_nonexisting_case_id(self):
        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.attach_issue,
            self.request,
            {
                "case": self.case.pk + 1,
                "issue_key": "123456",
                "tracker": self.tracker.pk,
                "summary": "XMLRPC fails",
            },
        )


class TestGetIssues(test.TestCase):
    """Test get_issues"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = f.UserFactory(username="tester", email="tester@example.com")
        cls.request = make_http_request(user=cls.tester)

        cls.tracker = f.IssueTrackerFactory(
            name="coolbz",
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            validate_regex=r"^\d+$",
        )

        cls.plan = f.TestPlanFactory()
        cls.case_1 = f.TestCaseFactory(plan=[cls.plan])
        cls.issue_1 = cls.case_1.add_issue("12345", cls.tracker)
        cls.issue_2 = cls.case_1.add_issue("89072", cls.tracker)
        cls.case_2 = f.TestCaseFactory(plan=[cls.plan])
        cls.issue_3 = cls.case_2.add_issue("23456", cls.tracker)

    def assert_issues(self, case_ids, expected_issues):
        issues = XmlrpcTestCase.get_issues(self.request, case_ids)
        issues = sorted(issues, key=operator.itemgetter("id"))
        self.assertEqual(expected_issues, issues)

    def test_get_issues_from_one_case(self):
        expected_issues = [
            {
                "id": self.issue_1.pk,
                "issue_key": "12345",
                "tracker": "coolbz",
                "tracker_id": self.tracker.pk,
                "summary": None,
                "description": None,
                "case_run": None,
                "case_run_id": None,
                "case": self.case_1.summary,
                "case_id": self.case_1.pk,
            },
            {
                "id": self.issue_2.pk,
                "issue_key": "89072",
                "tracker": "coolbz",
                "tracker_id": self.tracker.pk,
                "summary": None,
                "description": None,
                "case_run": None,
                "case_run_id": None,
                "case": self.case_1.summary,
                "case_id": self.case_1.pk,
            },
        ]

        self.assert_issues(self.case_1.pk, expected_issues)

    def test_get_issues_from_two_cases(self):
        expected_issues = [
            {
                "id": self.issue_1.pk,
                "issue_key": "12345",
                "tracker": "coolbz",
                "tracker_id": self.tracker.pk,
                "summary": None,
                "description": None,
                "case_run": None,
                "case_run_id": None,
                "case": self.case_1.summary,
                "case_id": self.case_1.pk,
            },
            {
                "id": self.issue_2.pk,
                "issue_key": "89072",
                "tracker": "coolbz",
                "tracker_id": self.tracker.pk,
                "summary": None,
                "description": None,
                "case_run": None,
                "case_run_id": None,
                "case": self.case_1.summary,
                "case_id": self.case_1.pk,
            },
            {
                "id": self.issue_3.pk,
                "issue_key": "23456",
                "tracker": "coolbz",
                "tracker_id": self.tracker.pk,
                "summary": None,
                "description": None,
                "case_run": None,
                "case_run_id": None,
                "case": self.case_2.summary,
                "case_id": self.case_2.pk,
            },
        ]

        for case_ids in (
            [self.case_1.pk, self.case_2.pk],
            f"{self.case_1.pk}, {self.case_2.pk}",
        ):
            self.assert_issues(case_ids, expected_issues)


class TestDetachIssue(test.TestCase):
    """Test detach_issue"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = f.UserFactory(username="tester", email="tester@example.com")
        cls.request = make_http_request(user=cls.tester, user_perm="issuetracker.delete_issue")

        cls.tracker = f.IssueTrackerFactory(
            name="coolbz",
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            validate_regex=r"^\d+$",
        )

        cls.plan = f.TestPlanFactory()
        cls.case_1 = f.TestCaseFactory(plan=[cls.plan])
        cls.issue_1 = cls.case_1.add_issue("12345", cls.tracker)
        cls.issue_2 = cls.case_1.add_issue("23456", cls.tracker)
        cls.issue_3 = cls.case_1.add_issue("34567", cls.tracker)
        cls.case_2 = f.TestCaseFactory(plan=[cls.plan])
        cls.issue_4 = cls.case_2.add_issue("12345", cls.tracker)
        cls.issue_5 = cls.case_2.add_issue("23456", cls.tracker)
        cls.issue_6 = cls.case_2.add_issue("56789", cls.tracker)

    def assert_rest_issues_after_detach(
        self, case_ids, issue_keys_to_detach, expected_rest_issue_keys
    ):
        """
        Detach issues from specified cases and assert whether expected rest
        issue keys still exists and detached issues are really detached
        """
        XmlrpcTestCase.detach_issue(self.request, case_ids, issue_keys_to_detach)

        # Check if detached issues are really detached.
        for case_id, issue_key in itertools.product(case_ids, issue_keys_to_detach):
            self.assertFalse(Issue.objects.filter(case=case_id, issue_key=issue_key).exists())

        # Ensure the expected rest issue keys are still there.
        for case_id, rest_issue_keys in expected_rest_issue_keys.items():
            for issue_key in rest_issue_keys:
                self.assertTrue(Issue.objects.filter(case=case_id, issue_key=issue_key).exists())

    def test_detach_issues_from_cases(self):
        self.assert_rest_issues_after_detach(
            [self.case_1.pk, self.case_2.pk],
            ["12345", "23456"],
            {self.case_1.pk: ["34567"], self.case_2.pk: ["56789"]},
        )


class TestCreateCase(XmlrpcAPIBaseTest):
    """Test create"""

    permission = "testcases.add_testcase"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory(name="Nitrate")
        cls.case_category = f.TestCaseCategoryFactory(name="functional", product=cls.product)
        cls.priority_p1, _ = Priority.objects.get_or_create(value="P1")

        cls.plan_1 = f.TestPlanFactory(
            name="Test add case to plans",
            product=cls.product,
        )
        cls.plan_2 = f.TestPlanFactory(
            name="Another plan 2",
            product=cls.product,
            author=cls.plan_1.author,
            owner=cls.plan_1.owner,
            product_version=cls.plan_1.product_version,
            type=cls.plan_1.type,
        )

        cls.component_db = f.ComponentFactory(name="db", product=cls.product)
        cls.component_web = f.ComponentFactory(name="web", product=cls.product)
        cls.tag_python = f.TestTagFactory(name="python")
        cls.tag_fedora = f.TestTagFactory(name="fedora")

    def test_missing_properties_summary_and_category(self):
        self.assertXmlrpcFaultBadRequest(XmlrpcTestCase.create, self.request, {"is_automated": 1})

    def test_fail_if_input_is_invalid(self):
        result = TestPlan.objects.aggregate(max_pk=Max("pk"))
        nonexisting_plan_id = result["max_pk"] + 1
        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.create,
            self.request,
            {
                "summary": "Test fail to create case if plan does not exist",
                "category": self.case_category.pk,
                "priority": self.priority_p1.pk,
                "product": self.product.pk,
                "plan": nonexisting_plan_id,
            },
        )

    def test_create_a_case_with_some_optional_properties(self):
        case = XmlrpcTestCase.create(
            self.request,
            {
                "summary": "Test create a case",
                "category": self.case_category.pk,
                "priority": self.priority_p1.pk,
                "product": self.product.pk,
                "estimated_time": "20s",
                "component": [self.component_db.pk, self.component_web.pk],
                "tag": [self.tag_python.name, self.tag_fedora.name],
            },
        )

        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        new_case_id = result["max_pk"]

        self.assertIsNotNone(new_case_id)
        self.assertEqual(new_case_id, case["case_id"])

        new_case = TestCase.objects.get(pk=new_case_id)

        self.assertEqual(self.case_category.pk, new_case.category.pk)
        self.assertEqual(self.priority_p1.pk, new_case.priority.pk)
        self.assertEqual(timedelta(seconds=20), new_case.estimated_time)

        for c in [self.component_db, self.component_web]:
            self.assertTrue(TestCaseComponent.objects.filter(case=new_case, component=c).exists())

        for tag in [self.tag_python, self.tag_fedora]:
            self.assertTrue(TestCaseTag.objects.filter(case=new_case, tag=tag).exists())

        text = new_case.latest_text()
        self.assertEqual("", text.action)
        self.assertEqual("", text.effect)
        self.assertEqual("", text.setup)
        self.assertEqual("", text.breakdown)

    def test_create_a_case_and_add_to_plans(self):
        case = XmlrpcTestCase.create(
            self.request,
            {
                "summary": "Test create a case",
                "category": self.case_category.pk,
                "priority": self.priority_p1.pk,
                "product": self.product.pk,
                "plan": [self.plan_1.pk, self.plan_2.pk],
            },
        )

        self.assertTrue(
            TestCasePlan.objects.filter(plan=self.plan_1, case=case["case_id"]).exists()
        )
        self.assertTrue(
            TestCasePlan.objects.filter(plan=self.plan_2, case=case["case_id"]).exists()
        )

    def test_create_tag_if_not_exist(self):
        case = XmlrpcTestCase.create(
            self.request,
            {
                "summary": "Test create a case",
                "category": self.case_category.pk,
                "priority": self.priority_p1.pk,
                "product": self.product.pk,
                "tag": [self.tag_python.name, "new_tag"],
            },
        )

        new_tag = TestTag.objects.filter(name="new_tag").first()
        self.assertIsNotNone(new_tag)

        new_case = TestCase.objects.get(pk=case["case_id"])
        self.assertTrue(TestCaseTag.objects.filter(case=new_case, tag=new_tag).exists())


class TestAddComment(XmlrpcAPIBaseTest):
    """Test add_comment"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_1 = f.TestCaseFactory()
        cls.case_2 = f.TestCaseFactory()
        cls.case_3 = f.TestCaseFactory()
        cls.case_4 = f.TestCaseFactory()

    def test_add_comment(self):
        content = "add a comment"

        test_data = (
            ([self.case_1.pk, self.case_2.pk], [self.case_1, self.case_2]),
            (f"{self.case_3.pk},{self.case_4.pk}", [self.case_3, self.case_4]),
        )

        for case_ids, cases in test_data:
            XmlrpcTestCase.add_comment(self.request, case_ids, content)

            for case in cases:
                comment = Comment.objects.for_model(case).first()
                self.assertEqual(content, comment.comment)

    def test_add_comment_to_nonexisting_cases(self):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        max_case_id = result["max_pk"]

        XmlrpcTestCase.add_comment(self.request, [max_case_id + 1, max_case_id + 2], "some comment")

        self.assertEqual(0, Comment.objects.count())

    def test_empty_case_ids(self):
        for case_ids in ("", []):
            XmlrpcTestCase.add_comment(self.request, [], "some comment")
            self.assertEqual(0, Comment.objects.count())


class TestAddcomponent(XmlrpcAPIBaseTest):
    """Test add_component"""

    permission = "testcases.add_testcasecomponent"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory(name="Nitrate")
        cls.plan = f.TestPlanFactory(name="A big plan", product=cls.product)
        cls.case_1 = f.TestCaseFactory(author=cls.plan.author, default_tester=cls.plan.author)
        cls.case_2 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )
        cls.case_3 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )
        cls.case_4 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )
        cls.case_5 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )
        cls.case_6 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )
        cls.case_7 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )
        cls.case_8 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )
        cls.case_9 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )

        cls.component_db = f.ComponentFactory(name="db", product=cls.product)
        cls.component_web = f.ComponentFactory(name="web", product=cls.product)

    def assert_case_has_components(self, cases, components):
        for case in cases:
            self.assertEqual(sorted(item.pk for item in case.component.all()), sorted(components))

    def test_add_components(self):
        component_ids = [self.component_db.pk, self.component_web.pk]

        XmlrpcTestCase.add_component(self.request, self.case_1.pk, component_ids)
        self.assert_case_has_components([self.case_1], component_ids)

        XmlrpcTestCase.add_component(self.request, [self.case_2.pk, self.case_3.pk], component_ids)
        self.assert_case_has_components([self.case_2, self.case_3], component_ids)

        XmlrpcTestCase.add_component(self.request, str(self.case_4.pk), component_ids)
        self.assert_case_has_components([self.case_4], component_ids)

        XmlrpcTestCase.add_component(
            self.request, f"{self.case_5.pk},{self.case_6.pk}", component_ids
        )
        self.assert_case_has_components([self.case_5], component_ids)

        XmlrpcTestCase.add_component(self.request, [self.case_7.pk], self.component_web.pk)
        self.assert_case_has_components([self.case_7], [self.component_web.pk])

        XmlrpcTestCase.add_component(self.request, [self.case_8.pk], str(self.component_web.pk))
        self.assert_case_has_components([self.case_8], [self.component_web.pk])

        XmlrpcTestCase.add_component(
            self.request,
            [self.case_9.pk],
            f"{self.component_db.pk},{self.component_web.pk}",
        )
        self.assert_case_has_components(
            [self.case_9], [self.component_db.pk, self.component_web.pk]
        )

    @patch("tcms.testcases.models.TestCase.add_component")
    def test_empty_case_ids(self, add_component):
        component_ids = [self.component_db.pk, self.component_web.pk]

        XmlrpcTestCase.add_component(self.request, "", component_ids)
        add_component.assert_not_called()

        XmlrpcTestCase.add_component(self.request, [], component_ids)
        add_component.assert_not_called()

    @patch("tcms.testcases.models.TestCase.add_component")
    def test_empty_component_ids(self, add_component):
        XmlrpcTestCase.add_component(self.request, self.case_1.pk, "")
        add_component.assert_not_called()

        XmlrpcTestCase.add_component(self.request, self.case_1.pk, [])
        add_component.assert_not_called()

    @patch("tcms.testcases.models.TestCase.add_component")
    def test_nonexisting_case_ids(self, add_component):
        XmlrpcTestCase.add_component(
            self.request, [self.case_9.pk + 1, self.case_9.pk + 2], self.component_db.pk
        )
        add_component.assert_not_called()

    @patch("tcms.testcases.models.TestCase.add_component")
    def test_nonexisting_component_ids(self, add_component):
        XmlrpcTestCase.add_component(self.request, self.case_1.pk, self.component_web.pk + 1)
        add_component.assert_not_called()


class TestAddTag(XmlrpcAPIBaseTest):
    """Test add_tag"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_add_tag(self):
        pass


class TestNotificationGetCCList(XmlrpcAPIBaseTest):
    """Test notification_get_cc_list"""

    permission = "testcases.change_testcase"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_1_cc_list = [
            "lisi@example.com",
            "wangwu@example.com",
            "zhangsan@example.com",
        ]

        cls.case_1 = f.TestCaseFactory()

        for item in cls.case_1_cc_list:
            cls.case_1.emailing.add_cc(item)

        cls.case_2_cc_list = [
            "somebody@example.com",
            "zhaoliu@example.com",
        ]

        cls.case_2 = f.TestCaseFactory()

        for item in cls.case_2_cc_list:
            cls.case_2.emailing.add_cc(item)

        cls.case_3 = f.TestCaseFactory()

    def test_get_cc_list(self):
        result = XmlrpcTestCase.notification_get_cc_list(self.request, self.case_1.pk)
        self.assertEqual({str(self.case_1.pk): self.case_1_cc_list}, result)

        result = XmlrpcTestCase.notification_get_cc_list(self.request, str(self.case_1.pk))
        self.assertEqual({str(self.case_1.pk): self.case_1_cc_list}, result)

        result = XmlrpcTestCase.notification_get_cc_list(
            self.request, f"{self.case_1.pk},{self.case_2.pk}"
        )
        self.assertEqual(
            {
                str(self.case_1.pk): self.case_1_cc_list,
                str(self.case_2.pk): self.case_2_cc_list,
            },
            result,
        )

        result = XmlrpcTestCase.notification_get_cc_list(
            self.request, [self.case_1.pk, self.case_2.pk]
        )
        self.assertEqual(
            {
                str(self.case_1.pk): self.case_1_cc_list,
                str(self.case_2.pk): self.case_2_cc_list,
            },
            result,
        )

    def test_empty_case_ids(self):
        for value in ("", []):
            result = XmlrpcTestCase.notification_get_cc_list(self.request, value)
            self.assertEqual({}, result)

    def test_nonexisting_case_ids(self):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        result = XmlrpcTestCase.notification_get_cc_list(self.request, result["max_pk"] + 1)
        self.assertEqual({}, result)

    def test_case_has_no_cc(self):
        result = XmlrpcTestCase.notification_get_cc_list(
            self.request, [self.case_1.pk, self.case_3.pk]
        )
        self.assertEqual(
            {str(self.case_1.pk): self.case_1_cc_list, str(self.case_3.pk): []}, result
        )


class TestNotificationAddCC(XmlrpcAPIBaseTest):
    """Test notification_add_cc"""

    permission = "testcases.change_testcase"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory(name="Nitrate")
        cls.plan = f.TestPlanFactory(name="A big plan", product=cls.product)
        cls.case_1 = f.TestCaseFactory(author=cls.plan.author, default_tester=cls.plan.author)
        cls.case_2 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )
        cls.case_3 = f.TestCaseFactory(
            author=cls.plan.author,
            default_tester=cls.plan.author,
            category=cls.case_1.category,
        )

        cls.case_3.emailing.add_cc("lisi@example.com")
        cls.case_3.emailing.add_cc("zhangsan@example.com")

    def test_add_cc(self):
        cc = ["lisi@example.com", "zhangsan@example.com"]
        another_cc = [
            "lisi@example.com",
            "wangwu@example.com",
            "zhangsan@example.com",
        ]

        test_data = (
            ([self.case_1.pk], cc),
            ([self.case_1.pk, self.case_2.pk], cc),
            ([self.case_3.pk], another_cc),
        )

        for case_ids, cc_emails in test_data:
            XmlrpcTestCase.notification_add_cc(self.request, case_ids, cc_emails)

            for case in TestCase.objects.filter(pk__in=case_ids):
                self.assertListEqual(cc_emails, case.emailing.get_cc_list())

    @patch("tcms.testcases.models.TestCase.emailing", new_callable=PropertyMock)
    def test_empty_case_ids(self, emailing):
        for case_ids in ("", []):
            XmlrpcTestCase.notification_add_cc(self.request, case_ids, ["zhangsan@example.com"])
            emailing.assert_not_called()

    @patch("tcms.testcases.models.TestCase.emailing", new_callable=PropertyMock)
    def test_nonexisting_case_ids(self, emailing):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        XmlrpcTestCase.notification_add_cc(
            self.request, result["max_pk"] + 1, ["zhangsan@example.com"]
        )
        emailing.assert_not_called()

    def test_empty_cc_list(self):
        XmlrpcTestCase.notification_add_cc(self.request, self.case_1.pk, [])
        self.assertEqual([], self.case_1.emailing.get_cc_list())

        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.notification_add_cc, self.request, self.case_1.pk, ""
        )

    def test_cc_is_not_a_list(self):
        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.notification_add_cc,
            self.request,
            self.case_1.pk,
            "zhangsan@example.com",
        )

    def test_cc_has_invalid_email_address(self):
        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.notification_add_cc,
            self.request,
            self.case_1.pk,
            ["email1", "email2"],
        )

        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.notification_add_cc,
            self.request,
            self.case_1.pk,
            ["", "zhangsan@example.com"],
        )


class TestStoreText(XmlrpcAPIBaseTest):
    """Test store_text"""

    permission = "testcases.add_testcasetext"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case = f.TestCaseFactory()
        cls.text_author = f.UserFactory(username="text-author")

    def test_case_does_not_exist(self):
        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.store_text, self.request, self.case.pk + 1, "action"
        )

    def test_store_text(self):
        test_data = (
            ("action", "", "", ""),
            ("action", "effect", "", ""),
            ("action", "effect", "setup", ""),
            ("action", "effect", "setup", "breakdown"),
            (" action    ", "effect\r\n\r\n", "setup  \t", "\tbreakdown\r\n"),
            ("action", "    \r\n\t   ", "setup", "      "),
        )

        for action, effect, setup, breakdown in test_data:
            stored_text = XmlrpcTestCase.store_text(
                self.request, self.case.pk, action, effect, setup, breakdown
            )

            action = action.strip()
            effect = effect.strip()
            setup = setup.strip()
            breakdown = breakdown.strip()

            # Yeah, do not assert the creation date
            del stored_text["create_date"]

            latest_text = self.case.latest_text()
            expected_result = {
                "id": latest_text.pk,
                "case": self.case.summary,
                "case_id": self.case.pk,
                "author": self.request.user.username,
                "author_id": self.request.user.pk,
                "case_text_version": latest_text.case_text_version,
                "action": action,
                "action_checksum": checksum(action),
                "effect": effect,
                "effect_checksum": checksum(effect),
                "setup": setup,
                "setup_checksum": checksum(setup),
                "breakdown": breakdown,
                "breakdown_checksum": checksum(breakdown),
            }
            self.assertDictEqual(expected_result, stored_text)

    def test_set_request_user_as_author(self):
        XmlrpcTestCase.store_text(self.request, self.case.pk, "action")

        text = self.case.latest_text()
        self.assertEqual(self.tester, text.author)

    def test_specify_author_explicitly(self):
        XmlrpcTestCase.store_text(
            self.request, self.case.pk, "action", author_id=self.text_author.pk
        )

        text = self.case.latest_text()
        self.assertEqual(self.text_author, text.author)

    def test_set_nonexisting_author(self):
        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.store_text,
            self.request,
            self.case.pk,
            "action",
            author_id=self.text_author.pk + 1,
        )


class TestCheckCaseStatus(XmlrpcAPIBaseTest):
    """Test check_case_status"""

    def test_get_by_name(self):
        case_status = TestCaseStatus.objects.get(name="CONFIRMED")
        self.assertEqual(
            {
                "id": case_status.pk,
                "name": case_status.name,
                "description": case_status.description,
            },
            XmlrpcTestCase.check_case_status(self.request, "CONFIRMED"),
        )

    def test_name_does_not_exist(self):
        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.check_case_status, self.request, "STATUS")

    def test_name_is_an_empty_string(self):
        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.check_case_status, self.request, "")


class TestCheckPriority(XmlrpcAPIBaseTest):
    """Test check_priority"""

    def test_get_by_value(self):
        priority = Priority.objects.get(value="P2")
        self.assertEqual(
            {
                "id": priority.pk,
                "value": priority.value,
                "sortkey": priority.sortkey,
                "is_active": priority.is_active,
            },
            XmlrpcTestCase.check_priority(self.request, "P2"),
        )

    def test_value_does_not_exist(self):
        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.check_priority, self.request, "VERY_HIGH")

    def test_value_is_an_empty_string(self):
        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.check_priority, self.request, "")


class TestGetCaseStatus(XmlrpcAPIBaseTest):
    """Test get_case_status"""

    def test_all_status(self):
        result = sorted(
            XmlrpcTestCase.get_case_status(self.request),
            key=lambda status: status["id"],
        )
        expected_status = [
            {
                "id": item.pk,
                "name": item.name,
                "description": item.description,
            }
            for item in TestCaseStatus.objects.order_by("pk")
        ]
        self.assertEqual(expected_status, result)

    def test_by_id(self):
        result = TestCaseStatus.objects.aggregate(max_pk=Max("pk"))
        max_id = result["max_pk"]
        case_status = TestCaseStatus.objects.get(pk=max_id)
        self.assertEqual(
            {
                "id": case_status.pk,
                "name": case_status.name,
                "description": case_status.description,
            },
            XmlrpcTestCase.get_case_status(self.request, max_id),
        )

    def test_by_nonexisting_id(self):
        result = TestCaseStatus.objects.aggregate(max_pk=Max("pk"))
        max_id = result["max_pk"]

        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.get_case_status, self.request, max_id + 1)

        result = TestCaseStatus.objects.aggregate(min_pk=Min("pk"))
        min_id = result["min_pk"]

        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.get_case_status, self.request, min_id - 1)


class TestGetPriority(XmlrpcAPIBaseTest):
    """Test get_priority"""

    def test_get_by_id(self):
        priority = Priority.objects.get(value="P2")
        self.assertEqual(
            {
                "id": priority.pk,
                "value": priority.value,
                "sortkey": priority.sortkey,
                "is_active": priority.is_active,
            },
            XmlrpcTestCase.get_priority(self.request, priority.pk),
        )

    def test_get_by_nonexisting_id(self):
        result = Priority.objects.aggregate(max_pk=Max("pk"))
        max_id = result["max_pk"]

        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.get_priority, self.request, max_id + 1)


class TestGetText(XmlrpcAPIBaseTest):
    """Test get_text"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case = f.TestCaseFactory(summary="Test get text via XMLRPC API")
        cls.text_1 = cls.case.add_text(
            action="action 1",
            effect="effect 1",
            setup="setup 1",
            breakdown="breakdown 1",
        )
        cls.text_2 = cls.case.add_text(
            action="action 2",
            effect="effect 2",
            setup="setup 2",
            breakdown="breakdown 2",
        )
        cls.text_3 = cls.case.add_text(
            action="action 3",
            effect="effect 3",
            setup="setup 3",
            breakdown="breakdown 3",
        )

    def assert_text(self, expected_text, call_result):
        self.assertDictEqual(
            {
                "id": expected_text.pk,
                "author_id": self.case.author.pk,
                "author": self.case.author.username,
                "case_id": self.case.pk,
                "case": self.case.summary,
                "case_text_version": expected_text.case_text_version,
                "action": expected_text.action,
                "action_checksum": expected_text.action_checksum,
                "effect": expected_text.effect,
                "effect_checksum": expected_text.effect_checksum,
                "setup": expected_text.setup,
                "setup_checksum": expected_text.setup_checksum,
                "breakdown": expected_text.breakdown,
                "breakdown_checksum": expected_text.breakdown_checksum,
            },
            call_result,
        )

    def test_get_text_with_latest_text_version(self):
        text = XmlrpcTestCase.get_text(self.request, self.case.pk)
        del text["create_date"]

        self.assert_text(self.text_3, text)

    def test_specify_a_text_version(self):
        text = XmlrpcTestCase.get_text(self.request, self.case.pk, self.text_2.case_text_version)
        del text["create_date"]

        self.assert_text(self.text_2, text)

    def test_specify_a_nonexiting_text_version(self):
        result = XmlrpcTestCase.get_text(
            self.request, self.case.pk, self.text_3.case_text_version + 1
        )
        self.assertDictEqual({}, result)

    def test_case_id_does_not_exist(self):
        nonexisting_case_id = self.case.pk + 1

        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.get_text,
            self.request,
            nonexisting_case_id,
            self.text_3.case_text_version,
        )


class TestGetComponents(XmlrpcAPIBaseTest):
    """Test get_components"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory()
        cls.plan = f.TestPlanFactory(product=cls.product)

        cls.case_1 = f.TestCaseFactory(plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(plan=[cls.plan])

        cls.component_db = Component.objects.create(
            name="db",
            product=cls.product,
            initial_owner=cls.plan.author,
            initial_qa_contact=cls.plan.author,
        )
        cls.component_web = Component.objects.create(
            name="web",
            product=cls.product,
            initial_owner=cls.plan.author,
            initial_qa_contact=cls.plan.author,
        )

        f.TestCaseComponentFactory(case=cls.case_1, component=cls.component_db)
        f.TestCaseComponentFactory(case=cls.case_1, component=cls.component_web)

    def _serialize_component(self, component):
        return {
            "id": component.pk,
            "name": component.name,
            "product_id": self.product.pk,
            "product": self.product.name,
            "initial_owner_id": component.initial_owner.pk,
            "initial_owner": component.initial_owner.username,
            "initial_qa_contact_id": component.initial_qa_contact.pk,
            "initial_qa_contact": component.initial_qa_contact.username,
            "description": component.description,
        }

    def test_get_by_case_id(self):
        self.maxDiff = None

        result = sorted(
            XmlrpcTestCase.get_components(self.request, self.case_1.pk),
            key=lambda item: item["id"],
        )
        self.assertListEqual(
            [
                self._serialize_component(self.component_db),
                self._serialize_component(self.component_web),
            ],
            result,
        )

    def test_case_id_does_not_exist(self):
        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.get_components, self.request, self.case_2.pk + 1
        )

    def test_case_does_not_have_components(self):
        self.assertListEqual([], XmlrpcTestCase.get_components(self.request, self.case_2.pk))


class TestGetPlans(XmlrpcAPIBaseTest):
    """Test get_plans"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory(name="xmlrpc")
        cls.plan_1 = f.TestPlanFactory(product=cls.product)
        cls.plan_2 = f.TestPlanFactory(product=cls.product)
        cls.plan_3 = f.TestPlanFactory(product=cls.product)

        cls.case = f.TestCaseFactory(author=cls.plan_2.author, plan=[cls.plan_2, cls.plan_3])

        cls.case_1 = f.TestCaseFactory(author=cls.plan_2.author)

    def test_get_by_case_id(self):
        plans = sorted(
            XmlrpcTestCase.get_plans(self.request, self.case.pk),
            key=lambda item: item["plan_id"],
        )

        self.assertEqual(self.plan_2.pk, plans[0]["plan_id"])
        self.assertEqual(self.plan_2.name, plans[0]["name"])
        self.assertEqual(self.plan_3.pk, plans[1]["plan_id"])
        self.assertEqual(self.plan_3.name, plans[1]["name"])

    def test_case_is_not_associated_with_any_plan(self):
        self.assertListEqual([], XmlrpcTestCase.get_plans(self.request, self.case_1.pk))

    def test_case_id_does_not_exist(self):
        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.get_plans, self.request, self.case_1.pk + 1)


class TestGetTags(XmlrpcAPIBaseTest):
    """Test get_tags"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tag_python = f.TestTagFactory(name="python")
        cls.tag_fedora = f.TestTagFactory(name="fedora")

        cls.case_1 = f.TestCaseFactory(tag=[cls.tag_python, cls.tag_fedora])
        cls.case_2 = f.TestCaseFactory()

    def test_get_by_case_id(self):
        tags = sorted(
            XmlrpcTestCase.get_tags(self.request, self.case_1.pk),
            key=lambda item: item["id"],
        )

        self.assertListEqual(
            [
                {"id": self.tag_python.pk, "name": self.tag_python.name},
                {"id": self.tag_fedora.pk, "name": self.tag_fedora.name},
            ],
            tags,
        )

    def test_case_has_no_tags(self):
        self.assertListEqual([], XmlrpcTestCase.get_tags(self.request, self.case_2.pk))

    def test_case_does_not_exist(self):
        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.get_tags, self.request, self.case_2.pk + 1)


class TestRemoveComponent(XmlrpcAPIBaseTest):
    """Test remove_component"""

    permission = "testcases.delete_testcasecomponent"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory()
        cls.plan = f.TestPlanFactory(name="Test remove component from case", product=cls.product)
        cls.case_1 = f.TestCaseFactory(author=cls.plan.author, plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(author=cls.plan.author, plan=[cls.plan])

        cls.component_db = f.ComponentFactory(name="db", product=cls.product)
        cls.component_web = f.ComponentFactory(name="web", product=cls.product)
        cls.component_doc = f.ComponentFactory(name="doc", product=cls.product)

    def _add_components(self):
        # Add those three components to every case created
        combinations = itertools.product(
            [self.case_1, self.case_2], [[self.component_db, self.component_web]]
        )
        for case, components in combinations:
            for c in components:
                case.add_component(c)

    def test_remove_component(self):
        test_data = (
            (self.case_1.pk, self.component_db.pk),
            (str(self.case_1.pk), self.component_db.pk),
            (f"{self.case_1.pk},{self.case_2.pk}", self.component_db.pk),
            ([self.case_1.pk, self.case_2.pk], self.component_db.pk),
            (self.case_1.pk, str(self.component_db.pk)),
            (self.case_1.pk, f"{self.component_db.pk},{self.component_web.pk}"),
            (self.case_1.pk, [self.component_db.pk, self.component_web.pk]),
        )

        for case_ids, component_ids in test_data:
            self._add_components()

            XmlrpcTestCase.remove_component(self.request, case_ids, component_ids)

            verify_combinations = itertools.product(
                pre_process_ids(case_ids), pre_process_ids(component_ids)
            )

            for case_id, component_id in verify_combinations:
                self.assertFalse(
                    TestCaseComponent.objects.filter(case=case_id, component=component_id).exists()
                )

    @patch("tcms.testcases.models.TestCase.remove_component")
    def test_nonexisting_case_ids(self, remove_component):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        XmlrpcTestCase.remove_component(self.request, result["max_pk"] + 1, [1, 2])
        remove_component.assert_not_called()

    @patch("tcms.testcases.models.TestCase.remove_component")
    def test_nonexisting_component_ids(self, remove_component):
        result = Component.objects.aggregate(max_pk=Max("pk"))
        XmlrpcTestCase.remove_component(self.request, [1, 2], result["max_pk"] + 1)

    @patch("tcms.testcases.models.TestCase.remove_component")
    def test_empty_case_ids(self, remove_component):
        XmlrpcTestCase.remove_component(self.request, "", self.component_db.pk)
        remove_component.assert_not_called()

        XmlrpcTestCase.remove_component(self.request, [], self.component_db.pk)
        remove_component.assert_not_called()

    @patch("tcms.testcases.models.TestCase.remove_component")
    def test_empty_component_ids(self, remove_component):
        XmlrpcTestCase.remove_component(self.request, self.case_1.pk, "")
        remove_component.assert_not_called()

        XmlrpcTestCase.remove_component(self.request, self.case_1.pk, [])
        remove_component.assert_not_called()

    def test_component_is_not_added_to_case(self):
        XmlrpcTestCase.remove_component(self.request, self.case_1.pk, self.component_doc.pk)

        # Component doc is not associated with any case. The API call should
        # return successfully without changing anything.

        self.assertTrue(TestCase.objects.filter(pk=self.case_1.pk).exists())
        self.assertTrue(Component.objects.filter(pk=self.component_doc.pk).exists())
        self.assertFalse(
            TestCaseComponent.objects.filter(
                case=self.case_1, component=self.component_doc
            ).exists()
        )


class TestRemoveTag(XmlrpcAPIBaseTest):
    """Test remove_tag"""

    permission = "testcases.delete_testcasetag"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory()
        cls.plan = f.TestPlanFactory(name="Test remove component from case", product=cls.product)
        cls.case_1 = f.TestCaseFactory(author=cls.plan.author, plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(author=cls.plan.author, plan=[cls.plan])

        cls.tag_python = f.TestTagFactory(name="python")
        cls.tag_fedora = f.TestTagFactory(name="fedora")
        cls.tag_os = f.TestTagFactory(name="os")

    def _add_tags(self):
        combinations = itertools.product(
            [self.case_1, self.case_2], [[self.tag_python, self.tag_fedora]]
        )
        for case, tags in combinations:
            for tag in tags:
                case.add_tag(tag)

    def test_remove_tag(self):
        test_data = (
            (self.case_1.pk, self.tag_python.name),
            (str(self.case_1.pk), self.tag_python.name),
            (f"{self.case_1.pk},{self.case_2.pk}", self.tag_python.name),
            ([self.case_1.pk, self.case_2.pk], self.tag_python.name),
            (self.case_1.pk, f"{self.tag_python.name},{self.tag_fedora.name}"),
            (self.case_1.pk, [self.tag_python.name, self.tag_fedora.name]),
        )

        for case_ids, tag_names in test_data:
            self._add_tags()

            XmlrpcTestCase.remove_tag(self.request, case_ids, tag_names)

            verify_combinations = itertools.product(
                pre_process_ids(case_ids), TestTag.string_to_list(tag_names)
            )

            for case_id, tag_name in verify_combinations:
                self.assertFalse(
                    TestCaseTag.objects.filter(
                        case=case_id, tag=TestTag.objects.get(name=tag_name)
                    ).exists()
                )

    @patch("tcms.testcases.models.TestCase.remove_tag")
    def test_nonexisting_case_ids(self, remove_tag):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        XmlrpcTestCase.remove_tag(self.request, result["max_pk"] + 1, self.tag_python.name)
        remove_tag.assert_not_called()

    @patch("tcms.testcases.models.TestCase.remove_tag")
    def test_nonexisting_tag_names(self, remove_tag):
        XmlrpcTestCase.remove_tag(self.request, self.case_1.pk, f"__{self.tag_fedora.name}__")
        remove_tag.assert_not_called()

    @patch("tcms.testcases.models.TestCase.remove_tag")
    def test_empty_case_ids(self, remove_tag):
        XmlrpcTestCase.remove_tag(self.request, "", self.tag_python.name)
        remove_tag.assert_not_called()

        XmlrpcTestCase.remove_tag(self.request, [], self.tag_python.name)
        remove_tag.assert_not_called()

    @patch("tcms.testcases.models.TestCase.remove_tag")
    def test_empty_tag_names(self, remove_tag):
        XmlrpcTestCase.remove_tag(self.request, self.case_1.pk, "")
        remove_tag.assert_not_called()

    def test_tag_is_not_added_to_case(self):
        XmlrpcTestCase.remove_tag(self.request, self.case_1.pk, self.tag_os.name)

        # Tag os is not associated with any case. The API call should return
        # successfully without changing anything.

        self.assertTrue(TestCase.objects.filter(pk=self.case_1.pk).exists())
        self.assertTrue(TestTag.objects.filter(name=self.tag_os.name).exists())
        self.assertFalse(TestCaseTag.objects.filter(case=self.case_1, tag=self.tag_os).exists())


class TestAddTags(XmlrpcAPIBaseTest):
    """Test add_tags"""

    permission = "testcases.add_testcasetag"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_1 = f.TestCaseFactory()
        cls.case_2 = f.TestCaseFactory()

        cls.tag_python = f.TestTagFactory(name="python")

    def _remove_tags(self):
        self.case_1.tag.delete()
        self.case_2.tag.delete()

    def test_add_tags(self):
        test_data = (
            (self.case_1.pk, "tag1"),
            (str(self.case_1.pk), "tag1"),
            (f"{self.case_1.pk},{self.case_2.pk}", "tag1"),
            ([self.case_1.pk, self.case_2.pk], "tag1"),
            (self.case_1.pk, "tag1,tag2"),
            (self.case_1.pk, "tag1,tag2, python"),
            (self.case_1.pk, ["tag1", "tag2"]),
            (self.case_1.pk, ["tag1", "tag2"]),
            (self.case_1.pk, ["tag1", "tag2", "python"]),
        )

        for case_ids, tag_names in test_data:
            XmlrpcTestCase.add_tag(self.request, case_ids, tag_names)

            verify_combinations = itertools.product(
                pre_process_ids(case_ids), TestTag.string_to_list(tag_names)
            )

            for case_id, tag_name in verify_combinations:
                self.assertTrue(
                    TestCaseTag.objects.filter(
                        case=case_id, tag=TestTag.objects.get(name=tag_name)
                    ).exists()
                )

    @patch("tcms.testcases.models.TestCase.add_tag")
    def test_empty_case_ids(self, add_tag):
        XmlrpcTestCase.add_tag(self.request, "", "tag1")
        add_tag.assert_not_called()
        self.assertFalse(TestTag.objects.filter(name="tag1").exists())

        XmlrpcTestCase.add_tag(self.request, [], "tag1")
        add_tag.assert_not_called()
        self.assertFalse(TestTag.objects.filter(name="tag1").exists())

    @patch("tcms.testcases.models.TestCase.add_tag")
    def test_empty_tag_names(self, add_tag):
        XmlrpcTestCase.add_tag(self.request, self.case_1.pk, "")
        add_tag.assert_not_called()

    @patch("tcms.testcases.models.TestCase.add_tag")
    def test_case_id_does_not_exist(self, add_tag):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        XmlrpcTestCase.add_tag(self.request, result["max_pk"] + 1, "tag1")
        add_tag.assert_not_called()


class TestAddCaseToRun(XmlrpcAPIBaseTest):
    """Test add_to_run"""

    permission = "testruns.add_testcaserun"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory()
        cls.plan = f.TestPlanFactory(product=cls.product)
        cls.case_1 = f.TestCaseFactory(summary="Case 1", author=cls.plan.author, plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(summary="Case 2", author=cls.plan.author, plan=[cls.plan])
        cls.run_1 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )
        cls.run_2 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )
        cls.run_3 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )
        cls.run_4 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )
        cls.run_5 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )
        cls.run_6 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )
        cls.run_7 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )
        cls.run_8 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )
        cls.run_9 = f.TestRunFactory(
            plan=cls.plan, manager=cls.plan.author, default_tester=cls.tester
        )

    def test_add_to_run(self):
        test_data = (
            (self.case_1.pk, self.run_1.pk),
            (str(self.case_1.pk), self.run_2.pk),
            (f"{self.case_1.pk},{self.case_2.pk}", self.run_3.pk),
            ([self.case_1.pk, self.case_2.pk], self.run_4.pk),
            (self.case_1.pk, str(self.run_5.pk)),
            (self.case_1.pk, f"{self.run_6.pk},{self.run_7.pk}"),
            (self.case_1.pk, [self.run_8.pk, self.run_9.pk]),
        )

        for case_ids, run_ids in test_data:
            XmlrpcTestCase.add_to_run(self.request, case_ids, run_ids)

            verify_combinations = itertools.product(
                pre_process_ids(case_ids), pre_process_ids(run_ids)
            )

            for case_id, run_id in verify_combinations:
                self.assertTrue(TestCaseRun.objects.filter(case=case_id, run=run_id).exists())

    def test_empty_case_ids(self):
        self.assertXmlrpcFaultBadRequest(XmlrpcTestCase.add_to_run, self.request, "", self.run_1.pk)

        self.assertXmlrpcFaultBadRequest(XmlrpcTestCase.add_to_run, self.request, [], self.run_1.pk)

    def test_empty_run_ids(self):
        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.add_to_run, self.request, self.case_1.pk, ""
        )

        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.add_to_run, self.request, self.case_1.pk, []
        )

    def test_case_ids_do_not_exist(self):
        result = TestCase.objects.aggregate(max_pk=Max("pk"))
        max_case_id = result["max_pk"]

        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.add_to_run, self.request, max_case_id + 1, self.run_1
        )

    def test_run_ids_do_not_exist(self):
        result = TestRun.objects.aggregate(max_pk=Max("pk"))
        max_run_id = result["max_pk"]

        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.add_to_run, self.request, self.case_1.pk, max_run_id + 1
        )


class TestEstimatedTime(XmlrpcAPIBaseTest):
    """Test calculation on case estimation time"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory()
        cls.plan = f.TestPlanFactory(author=cls.tester, product=cls.product)
        cls.case_1 = f.TestCaseFactory(estimated_time=timedelta(minutes=5), plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(estimated_time=timedelta(seconds=30), plan=[cls.plan])
        cls.case_3 = f.TestCaseFactory(plan=[cls.plan])
        cls.case_4 = f.TestCaseFactory(plan=[cls.plan])

    def test_total_estimated_time(self):
        total = XmlrpcTestCase.calculate_total_estimated_time(
            self.request, [self.case_1.pk, self.case_2.pk]
        )
        self.assertEqual("00:05:30", total)

        total = XmlrpcTestCase.calculate_total_estimated_time(
            self.request, [self.case_3.pk, self.case_4.pk]
        )
        self.assertEqual("00:00:00", total)

    def test_average_estimated_time(self):
        avg = XmlrpcTestCase.calculate_average_estimated_time(
            self.request, [self.case_1.pk, self.case_2.pk]
        )
        self.assertEqual("00:02:45", avg)

        avg = XmlrpcTestCase.calculate_average_estimated_time(
            self.request, [self.case_3.pk, self.case_4.pk]
        )
        self.assertEqual("00:00:00", avg)

    def test_case_ids_do_not_exist(self):
        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.calculate_total_estimated_time,
            self.request,
            self.case_4.pk + 1,
        )

        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.calculate_average_estimated_time,
            self.request,
            self.case_4.pk + 1,
        )


class TestUpdateCases(XmlrpcAPIBaseTest):
    """Test update"""

    permission = "testcases.change_testcase"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory()
        cls.product_1 = f.ProductFactory(name="CoolProduct")
        cls.plan = f.TestPlanFactory(product=cls.product)
        cls.case_1 = f.TestCaseFactory(plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(plan=[cls.plan])

    def test_update_value_is_invalid(self):
        result = Priority.objects.aggregate(max_pk=Max("pk"))
        max_priority_id = result["max_pk"]

        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.update,
            self.request,
            self.case_1.pk,
            {"priority": max_priority_id + 1},
        )

    def test_missing_product_if_category_is_given(self):
        self.assertXmlrpcFaultBadRequest(
            XmlrpcTestCase.update, self.request, self.case_1.pk, {"category": 1}
        )

    def test_update(self):
        update_data = {
            "product": self.product_1.pk,
            "estimated_time": "00:05:00",
            "summary": "Test update case via XMLRPC API",
            "notes": "Some new notes",
            "script": "run shell script",
            "is_automated": 2,
        }
        result = XmlrpcTestCase.update(self.request, self.case_1.pk, update_data)

        self.assertEqual(self.case_1.pk, result[0]["case_id"])

        case = TestCase.objects.get(pk=self.case_1.pk)
        self.assertEqual(update_data["summary"], case.summary)
        self.assertEqual(timedelta(seconds=300), case.estimated_time)
        self.assertEqual(update_data["notes"], case.notes)
        self.assertEqual(update_data["script"], case.script)
        self.assertEqual(update_data["is_automated"], case.is_automated)


class TestFilterCount(XmlrpcAPIBaseTest):
    """Test filter_count"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory()
        cls.category = f.TestCaseCategoryFactory(name="functional", product=cls.product)

        cls.plan = f.TestPlanFactory(product=cls.product)

        cls.case_1 = f.TestCaseFactory(plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(estimated_time=timedelta(seconds=200), plan=[cls.plan])
        cls.case_3 = f.TestCaseFactory(category=cls.category, plan=[cls.plan])

    def test_empty_filter_criteria(self):
        self.assertEqual(TestCase.objects.count(), XmlrpcTestCase.filter_count(self.request, {}))

    def test_filter_by_estimated_time(self):
        result = XmlrpcTestCase.filter_count(self.request, values={"estimated_time": "00:03:20"})
        self.assertEqual(1, result)

    def test_filter_count_in_general(self):
        result = XmlrpcTestCase.filter_count(self.request, values={"category": self.category.pk})
        self.assertEqual(1, result)


class TestFilterCases(XmlrpcAPIBaseTest):
    """Test filter"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product = f.ProductFactory()
        cls.category = f.TestCaseCategoryFactory(name="functional", product=cls.product)

        cls.plan = f.TestPlanFactory(product=cls.product)

        cls.case_1 = f.TestCaseFactory(plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(estimated_time=timedelta(seconds=200), plan=[cls.plan])
        cls.case_3 = f.TestCaseFactory(category=cls.category, plan=[cls.plan])

    def test_empty_filter_criteria(self):
        result = XmlrpcTestCase.filter(self.request, {})
        self.assertListEqual(
            [self.case_1.pk, self.case_2.pk, self.case_3.pk],
            sorted(item["case_id"] for item in result),
        )

    def test_filter_by_estimated_time(self):
        result = XmlrpcTestCase.filter(self.request, {"estimated_time": "00:03:20"})
        self.assertEqual(1, len(result))
        self.assertEqual(self.case_2.pk, result[0]["case_id"])

    def test_filter_count_in_general(self):
        result = XmlrpcTestCase.filter(self.request, {"category": self.category.pk})
        self.assertEqual(1, len(result))
        self.assertEqual(self.case_3.pk, result[0]["case_id"])

    def test_deprecate_attachment(self):
        """!!! remove this test when the deprecation warning is removed

        When criterion with the old relationship name is passed, the query
        should be performed successfully and warning the deprecation message.
        """
        query = {"attachment__stored_name__startswith": "filename"}
        self.assertListEqual([], XmlrpcTestCase.filter(self.request, query))


class TestGetIssueTracker(XmlrpcAPIBaseTest):
    """Test get_issue_tracker"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tracker_1 = f.IssueTrackerFactory(name="Tracker1")

    def test_get_by_id(self):
        for tid in (str(self.tracker_1.pk), self.tracker_1.pk):
            tracker = XmlrpcTestCase.get_issue_tracker(self.request, tid)
            self.assertEqual(self.tracker_1.pk, tracker["id"])

    def test_id_does_not_exist(self):
        self.assertXmlrpcFaultNotFound(
            XmlrpcTestCase.get_issue_tracker, self.request, self.tracker_1.pk + 1
        )

        self.assertXmlrpcFaultNotFound(XmlrpcTestCase.get_issue_tracker, self.request, 0)


class TestDeprecatedAPIs(XmlrpcAPIBaseTest):
    """Simple tests for deprecated APIs"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.category = f.TestCaseCategoryFactory(name="functional")

    def test_lookup_status_name_by_id(self):
        case_status = TestCaseStatus.objects.get(name="PROPOSED")
        self.assertDictEqual(
            {
                "id": case_status.pk,
                "name": case_status.name,
                "description": case_status.description,
            },
            XmlrpcTestCase.lookup_status_name_by_id(self.request, case_status.pk),
        )

    def test_lookup_status_id_by_name(self):
        case_status = TestCaseStatus.objects.get(name="PROPOSED")
        self.assertDictEqual(
            {
                "id": case_status.pk,
                "name": case_status.name,
                "description": case_status.description,
            },
            XmlrpcTestCase.lookup_status_id_by_name(self.request, "PROPOSED"),
        )

    def test_lookup_priority_id_by_name(self):
        priority = Priority.objects.get(value="P2")
        self.assertDictEqual(
            {
                "id": priority.pk,
                "value": priority.value,
                "sortkey": priority.sortkey,
                "is_active": priority.is_active,
            },
            XmlrpcTestCase.lookup_priority_id_by_name(self.request, "P2"),
        )

    def test_lookup_priority_name_by_id(self):
        priority = Priority.objects.get(value="P1")
        self.assertDictEqual(
            {
                "id": priority.pk,
                "value": priority.value,
                "sortkey": priority.sortkey,
                "is_active": priority.is_active,
            },
            XmlrpcTestCase.lookup_priority_name_by_id(self.request, priority.pk),
        )

    def test_lookup_category_name_by_id(self):
        self.assertDictEqual(
            {
                "id": self.category.pk,
                "name": self.category.name,
                "description": self.category.description,
                "product_id": self.category.product.pk,
                "product": self.category.product.name,
            },
            XmlrpcTestCase.lookup_category_name_by_id(self.request, self.category.pk),
        )

    def test_lookup_category_id_by_name(self):
        self.assertDictEqual(
            {
                "id": self.category.pk,
                "name": self.category.name,
                "description": self.category.description,
                "product_id": self.category.product.pk,
                "product": self.category.product.name,
            },
            XmlrpcTestCase.lookup_category_id_by_name(
                self.request, "functional", self.category.product.pk
            ),
        )


class TestGetCaseRunHistory(XmlrpcAPIBaseTest):
    """Test testcase.get_case_run_history"""

    def test_get_case_run_history(self):
        self.assertXmlrpcFaultNotImplemented(XmlrpcTestCase.get_case_run_history, None, None)


class TestChangeHistory(XmlrpcAPIBaseTest):
    """Test testcase.get_case_run_history"""

    def test_get_case_run_history(self):
        self.assertXmlrpcFaultNotImplemented(XmlrpcTestCase.get_change_history, None, None)

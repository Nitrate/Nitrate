# -*- coding: utf-8 -*-

import itertools
import operator

from django import test

from tcms.integration.issuetracker.factories import IssueTrackerFactory
from tcms.integration.issuetracker.models import Issue
from tcms.management.models import Priority
from tcms.testcases.models import TestCasePlan
from tcms.testcases.models import TestCaseStatus
from tcms.tests.factories import TestCaseCategoryFactory
from tcms.tests.factories import TestCaseFactory
from tcms.tests.factories import TestCasePlanFactory
from tcms.tests.factories import TestPlanFactory
from tcms.tests.factories import TestTagFactory
from tcms.tests.factories import UserFactory
from tcms.xmlrpc.api import testcase as XmlrpcTestCase
from tcms.xmlrpc.serializer import datetime_to_str
from tcms.xmlrpc.tests.utils import make_http_request


class TestNotificationRemoveCC(test.TestCase):
    """ Tests the XML-RPC testcase.notication_remove_cc method """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.http_req = make_http_request(user=cls.user,
                                         user_perm='testcases.change_testcase')

        cls.default_cc = 'example@MrSenko.com'
        cls.testcase = TestCaseFactory()
        cls.testcase.emailing.add_cc(cls.default_cc)

    def test_remove_existing_cc(self):
        # initially testcase has the default CC listed
        # and we issue XMLRPC request to remove the cc
        XmlrpcTestCase.notification_remove_cc(self.http_req, self.testcase.pk, [self.default_cc])

        # now verify that the CC email has been removed
        self.assertEqual(0, self.testcase.emailing.cc_list.count())


class TestUnlinkPlan(test.TestCase):
    """ Test the XML-RPC method testcase.unlink_plan() """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.http_req = make_http_request(user=cls.user,
                                         user_perm='testcases.delete_testcaseplan')

        cls.testcase_1 = TestCaseFactory()
        cls.testcase_2 = TestCaseFactory()
        cls.plan_1 = TestPlanFactory()
        cls.plan_2 = TestPlanFactory()

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
        self.assertEqual(self.plan_2.pk, result[0]['plan_id'])


class TestLinkPlan(test.TestCase):
    """ Test the XML-RPC method testcase.link_plan() """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.http_req = make_http_request(user=cls.user,
                                         user_perm='testcases.add_testcaseplan')

        cls.testcase_1 = TestCaseFactory()
        cls.testcase_2 = TestCaseFactory()
        cls.testcase_3 = TestCaseFactory()

        cls.plan_1 = TestPlanFactory()
        cls.plan_2 = TestPlanFactory()
        cls.plan_3 = TestPlanFactory()

        # case 1 is already linked to plan 1
        cls.testcase_1.add_to_plan(cls.plan_1)

    def test_insert_ignores_existing_mappings(self):
        plans = [self.plan_1.pk, self.plan_2.pk, self.plan_3.pk]
        cases = [self.testcase_1.pk, self.testcase_2.pk, self.testcase_3.pk]
        XmlrpcTestCase.link_plan(self.http_req, cases, plans)

        # no duplicates for plan1/case1 were created
        self.assertEqual(
            1,
            TestCasePlan.objects.filter(
                plan=self.plan_1.pk,
                case=self.testcase_1.pk
            ).count()
        )

        # verify all case/plan combinations exist
        for plan_id in plans:
            for case_id in cases:
                self.assertEqual(
                    1,
                    TestCasePlan.objects.filter(
                        plan=plan_id,
                        case=case_id
                    ).count()
                )


class TestGet(test.TestCase):
    """Test XML-RPC testcase.get"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.http_req = make_http_request(user=cls.user)
        cls.reviewer = UserFactory(username='reviewer')

        cls.plan_1 = TestPlanFactory()
        cls.plan_2 = TestPlanFactory()

        cls.status = TestCaseStatus.objects.get(name='CONFIRMED')
        cls.priority = Priority.objects.get(value='P2')
        cls.category = TestCaseCategoryFactory(name='fast')
        cls.case = TestCaseFactory(
            priority=cls.priority,
            case_status=cls.status,
            category=cls.category,
            author=cls.user,
            default_tester=cls.user,
            reviewer=cls.reviewer)
        cls.tag_fedora = TestTagFactory(name='fedora')
        cls.tag_python = TestTagFactory(name='python')
        cls.case.add_tag(cls.tag_fedora)
        cls.case.add_tag(cls.tag_python)

        TestCasePlanFactory(plan=cls.plan_1, case=cls.case)
        TestCasePlanFactory(plan=cls.plan_2, case=cls.case)

    def test_get_a_case(self):
        resp = XmlrpcTestCase.get(self.http_req, self.case.pk)
        resp['tag'].sort()
        resp['plan'].sort()

        expected_resp = dict(
            case_id=self.case.pk,
            summary=self.case.summary,
            create_date=datetime_to_str(self.case.create_date),
            is_automated=self.case.is_automated,
            is_automated_proposed=self.case.is_automated_proposed,
            script='',
            arguments='',
            extra_link=None,
            requirement='',
            alias='',
            estimated_time='00:00:00',
            notes='',
            case_status_id=self.status.pk,
            case_status=self.status.name,
            category_id=self.category.pk,
            category=self.category.name,
            author_id=self.user.pk,
            author=self.user.username,
            default_tester_id=self.user.pk,
            default_tester=self.user.username,
            priority=self.priority.value,
            priority_id=self.priority.pk,
            reviewer_id=self.reviewer.pk,
            reviewer=self.reviewer.username,
            text={},
            tag=['fedora', 'python'],
            attachment=[],
            plan=[self.plan_1.pk, self.plan_2.pk],
            component=[],
        )
        self.assertEqual(expected_resp, resp)


class TestAttachIssue(test.TestCase):
    """Test attach_issue"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = UserFactory(username='tester', email='tester@example.com')
        cls.request = make_http_request(user=cls.tester,
                                        user_perm='issuetracker.add_issue')
        cls.case = TestCaseFactory()
        cls.tracker = IssueTrackerFactory(
            service_url='http://localhost/',
            issue_report_endpoint='/enter_bug.cgi',
            validate_regex=r'^\d+$')

    def test_attach_an_issue(self):
        XmlrpcTestCase.attach_issue(
            self.request,
            {
                'case': self.case.pk,
                'issue_key': '123456',
                'tracker': self.tracker.pk,
                'summary': 'XMLRPC fails'
            })

        issue = Issue.objects.filter(
            issue_key='123456',
            tracker=self.tracker.pk,
            case=self.case.pk,
            case_run__isnull=True,
        ).first()

        self.assertIsNotNone(issue)
        self.assertEqual('XMLRPC fails', issue.summary)

    def test_attach_some_issues(self):
        XmlrpcTestCase.attach_issue(
            self.request,
            [
                {
                    'case': self.case.pk,
                    'issue_key': '123456',
                    'tracker': self.tracker.pk,
                    'summary': 'XMLRPC fails'
                },
                {
                    'case': self.case.pk,
                    'issue_key': '789012',
                    'tracker': self.tracker.pk,
                    'summary': 'abc'
                },
            ])

        issue = Issue.objects.filter(
            issue_key='123456',
            tracker=self.tracker.pk,
            case=self.case.pk,
            case_run__isnull=True,
        ).first()

        self.assertIsNotNone(issue)
        self.assertEqual('XMLRPC fails', issue.summary)

        issue = Issue.objects.filter(
            issue_key='789012',
            tracker=self.tracker.pk,
            case=self.case.pk,
            case_run__isnull=True,
        ).first()

        self.assertIsNotNone(issue)
        self.assertEqual('abc', issue.summary)


class TestGetIssues(test.TestCase):
    """Test get_issues"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = UserFactory(username='tester', email='tester@example.com')
        cls.request = make_http_request(user=cls.tester)

        cls.tracker = IssueTrackerFactory(
            name='coolbz',
            service_url='http://localhost/',
            issue_report_endpoint='/enter_bug.cgi',
            validate_regex=r'^\d+$')

        cls.plan = TestPlanFactory()
        cls.case_1 = TestCaseFactory(plan=[cls.plan])
        cls.issue_1 = cls.case_1.add_issue('12345', cls.tracker)
        cls.issue_2 = cls.case_1.add_issue('89072', cls.tracker)
        cls.case_2 = TestCaseFactory(plan=[cls.plan])
        cls.issue_3 = cls.case_2.add_issue('23456', cls.tracker)

    def assert_issues(self, case_ids, expected_issues):
        issues = XmlrpcTestCase.get_issues(self.request, case_ids)
        issues = sorted(issues, key=operator.itemgetter('id'))
        self.assertEqual(expected_issues, issues)

    def test_get_issues_from_one_case(self):
        expected_issues = [
            {
                'id': self.issue_1.pk,
                'issue_key': '12345',
                'tracker': 'coolbz',
                'tracker_id': self.tracker.pk,
                'summary': None,
                'description': None,
                'case_run': None,
                'case_run_id': None,
                'case': self.case_1.summary,
                'case_id': self.case_1.pk,
            },
            {
                'id': self.issue_2.pk,
                'issue_key': '89072',
                'tracker': 'coolbz',
                'tracker_id': self.tracker.pk,
                'summary': None,
                'description': None,
                'case_run': None,
                'case_run_id': None,
                'case': self.case_1.summary,
                'case_id': self.case_1.pk,
            },
        ]

        self.assert_issues(self.case_1.pk, expected_issues)

    def test_get_issues_from_two_cases(self):
        expected_issues = [
            {
                'id': self.issue_1.pk,
                'issue_key': '12345',
                'tracker': 'coolbz',
                'tracker_id': self.tracker.pk,
                'summary': None,
                'description': None,
                'case_run': None,
                'case_run_id': None,
                'case': self.case_1.summary,
                'case_id': self.case_1.pk,
            },
            {
                'id': self.issue_2.pk,
                'issue_key': '89072',
                'tracker': 'coolbz',
                'tracker_id': self.tracker.pk,
                'summary': None,
                'description': None,
                'case_run': None,
                'case_run_id': None,
                'case': self.case_1.summary,
                'case_id': self.case_1.pk,
            },
            {
                'id': self.issue_3.pk,
                'issue_key': '23456',
                'tracker': 'coolbz',
                'tracker_id': self.tracker.pk,
                'summary': None,
                'description': None,
                'case_run': None,
                'case_run_id': None,
                'case': self.case_2.summary,
                'case_id': self.case_2.pk,
            },
        ]

        for case_ids in ([self.case_1.pk, self.case_2.pk],
                         '{}, {}'.format(self.case_1.pk, self.case_2.pk)):
            self.assert_issues(case_ids, expected_issues)


class TestDetachIssue(test.TestCase):
    """Test detach_issue"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = UserFactory(username='tester', email='tester@example.com')
        cls.request = make_http_request(
            user=cls.tester, user_perm='issuetracker.delete_issue')

        cls.tracker = IssueTrackerFactory(
            name='coolbz',
            service_url='http://localhost/',
            issue_report_endpoint='/enter_bug.cgi',
            validate_regex=r'^\d+$')

        cls.plan = TestPlanFactory()
        cls.case_1 = TestCaseFactory(plan=[cls.plan])
        cls.issue_1 = cls.case_1.add_issue('12345', cls.tracker)
        cls.issue_2 = cls.case_1.add_issue('23456', cls.tracker)
        cls.issue_3 = cls.case_1.add_issue('34567', cls.tracker)
        cls.case_2 = TestCaseFactory(plan=[cls.plan])
        cls.issue_4 = cls.case_2.add_issue('12345', cls.tracker)
        cls.issue_5 = cls.case_2.add_issue('23456', cls.tracker)
        cls.issue_6 = cls.case_2.add_issue('56789', cls.tracker)

    def assert_rest_issues_after_detach(
            self, case_ids, issue_keys_to_detach, expected_rest_issue_keys):
        """
        Detach issues from specified cases and assert whether expected rest
        issue keys still exists and detached issues are really detached
        """
        XmlrpcTestCase.detach_issue(self.request,
                                    case_ids, issue_keys_to_detach)

        # Check if detached issues are really detached.
        for case_id, issue_key in itertools.product(case_ids, issue_keys_to_detach):
            self.assertFalse(Issue.objects.filter(
                case=case_id, issue_key=issue_key).exists())

        # Ensure the expected rest issue keys are still there.
        for case_id, rest_issue_keys in expected_rest_issue_keys.items():
            for issue_key in rest_issue_keys:
                self.assertTrue(Issue.objects.filter(
                    case=case_id, issue_key=issue_key).exists())

    def test_detach_issues_from_cases(self):
        self.assert_rest_issues_after_detach(
            [self.case_1.pk, self.case_2.pk],
            ['12345', '23456'],
            {self.case_1.pk: ['34567'], self.case_2.pk: ['56789']}
        )

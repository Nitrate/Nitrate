# -*- coding: utf-8 -*-

from django import test

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

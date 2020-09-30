# -*- coding: utf-8 -*-

from django.conf import settings
from django import test
from unittest.mock import patch

from tcms.testplans.helpers import email
from tcms.testplans.models import _disconnect_signals, TestPlan
from tcms.testplans.models import _listen
from tests import factories as f, BasePlanCase


class TestSendEmailOnPlanUpdated(test.TestCase):
    """Test send email on a plan is updated"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = f.UserFactory(username='owner', email='owner@example.com')
        cls.plan = f.TestPlanFactory(owner=cls.owner, author=cls.owner)

        cls.plan.email_settings.auto_to_plan_owner = True
        cls.plan.email_settings.auto_to_plan_author = True
        cls.plan.email_settings.notify_on_plan_update = True
        cls.plan.email_settings.save()

    def setUp(self):
        _listen()

    def tearDown(self):
        _disconnect_signals()

    @patch('tcms.testplans.helpers.email.mailto')
    def test_send_email(self, mailto):
        self.plan.name = 'Update to send email ...'
        self.plan.save()

        mailto.assert_called_once_with(
            settings.PLAN_EMAIL_TEMPLATE,
            f'TestPlan {self.plan.pk} has been updated.',
            ['owner@example.com'],
            context={'plan': self.plan})


class TestSendEmailOnPlanDeleted(test.TestCase):
    """Test send email on a plan is deleted"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = f.UserFactory(username='owner', email='owner@example.com')
        cls.plan = f.TestPlanFactory(owner=cls.owner, author=cls.owner)

        cls.plan.email_settings.auto_to_plan_owner = True
        cls.plan.email_settings.auto_to_plan_author = True
        cls.plan.email_settings.notify_on_plan_delete = True
        cls.plan.email_settings.save()

    def setUp(self):
        _listen()

    def tearDown(self):
        _disconnect_signals()

    @patch('tcms.testplans.helpers.email.mailto')
    def test_send_email(self, mailto):
        plan_id = self.plan.pk
        self.plan.delete()

        mailto.assert_called_once_with(
            settings.PLAN_DELELE_EMAIL_TEMPLATE,
            f'TestPlan {plan_id} has been deleted.',
            ['owner@example.com'],
            context={'plan': self.plan})


class TestGetPlanNotificationRecipients(test.TestCase):
    """Test testplans.helpers.email.get_plan_notification_recipients"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = f.UserFactory(username='user1')
        cls.plan_owner = f.UserFactory(username='plan_owner')
        cls.plan = f.TestPlanFactory(owner=cls.plan_owner, author=cls.owner)

        cls.case_1 = f.TestCaseFactory(
            author=f.UserFactory(username='user2'),
            default_tester=f.UserFactory(username='user3'),
            plan=[cls.plan])

        cls.case_2 = f.TestCaseFactory(
            author=f.UserFactory(username='user4'),
            default_tester=f.UserFactory(username='user5'),
            plan=[cls.plan])

        cls.case_3 = f.TestCaseFactory(
            author=f.UserFactory(username='user6'),
            default_tester=f.UserFactory(username='user7', email=''),
            plan=[cls.plan])

    def test_collect_recipients(self):
        # Test data is a tuple of 5-elements tuples, each of one contains:
        # auto_to_plan_owner, auto_to_plan_author,
        # auto_to_case_owner, auto_to_case_default_tester, expected
        test_data = (
            (0, 0, 0, 0, []),
            (1, 0, 0, 0, ['plan_owner@example.com']),
            (1, 1, 0, 0, ['plan_owner@example.com', 'user1@example.com']),
            (1, 1, 1, 0, ['plan_owner@example.com',
                          'user1@example.com', 'user2@example.com',
                          'user4@example.com', 'user6@example.com']),
            (1, 1, 1, 1, ['plan_owner@example.com',
                          'user1@example.com', 'user2@example.com',
                          'user3@example.com', 'user4@example.com',
                          'user5@example.com', 'user6@example.com']),
        )

        for item in test_data:
            (auto_to_plan_owner,
             auto_to_plan_author,
             auto_to_case_owner,
             auto_to_case_default_tester,
             expected) = item

            es = self.plan.email_settings
            es.auto_to_plan_owner = bool(auto_to_plan_owner)
            es.auto_to_plan_author = bool(auto_to_plan_author)
            es.auto_to_case_owner = bool(auto_to_case_owner)
            es.auto_to_case_default_tester = bool(auto_to_case_default_tester)
            es.save()

            plan = TestPlan.objects.get(pk=self.plan.pk)

            # Since this test contains the case of plan.owner is None,
            # recover the plan's owner here.
            plan.owner = self.plan_owner
            plan.save(update_fields=['owner'])

            recipients = email.get_plan_notification_recipients(plan)
            self.assertListEqual(expected, sorted(recipients))

            # plan's owner could be put into the test data, but that would make
            # the test data larger.
            plan.owner = None
            plan.save(update_fields=['owner'])

            recipients = sorted(email.get_plan_notification_recipients(plan))
            if self.plan_owner.email in expected:
                expected.remove(self.plan_owner.email)
            self.assertListEqual(expected, recipients)

    @patch('tcms.testplans.helpers.email.mailto')
    def test_no_recipients_for_email_plan_update(self, mailto):
        es = self.plan.email_settings
        es.auto_to_plan_owner = False
        es.auto_to_plan_author = False
        es.auto_to_case_owner = False
        es.auto_to_case_default_tester = False
        es.save()

        plan = TestPlan.objects.get(pk=self.plan.pk)
        email.email_plan_update(plan)

        mailto.assert_not_called()

    @patch('tcms.testplans.helpers.email.mailto')
    def test_no_recipients_for_email_plan_deletion(self, mailto):
        es = self.plan.email_settings
        es.auto_to_plan_owner = False
        es.auto_to_plan_author = False
        es.auto_to_case_owner = False
        es.auto_to_case_default_tester = False
        es.save()

        plan = TestPlan.objects.get(pk=self.plan.pk)
        email.email_plan_deletion(plan)

        mailto.assert_not_called()


class TestPlanTreeView(BasePlanCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_treeview_data()

    def test_get_ancestor_ids(self):
        expected = [self.plan.pk, self.plan_2.pk, self.plan_3.pk]
        plan: TestPlan = TestPlan.objects.get(pk=self.plan_4.pk)
        self.assertListEqual(expected, sorted(plan.get_ancestor_ids()))

    def test_get_ancestors(self):
        ancestor_ids = [self.plan.pk, self.plan_2.pk, self.plan_3.pk]
        expected = [
            repr(item) for item in
            TestPlan.objects.filter(pk__in=ancestor_ids).order_by('pk')
        ]
        plan: TestPlan = TestPlan.objects.get(pk=self.plan_4.pk)
        self.assertQuerysetEqual(plan.get_ancestors().order_by('pk'), expected)

    def test_get_descendant_ids(self):
        expected = [self.plan_4.pk, self.plan_5.pk, self.plan_6.pk, self.plan_7.pk]
        plan: TestPlan = TestPlan.objects.get(pk=self.plan_3.pk)
        self.assertListEqual(expected, sorted(plan.get_descendant_ids()))

    def test_get_descendants(self):
        descendant_ids = [
            self.plan_4.pk, self.plan_5.pk, self.plan_6.pk, self.plan_7.pk
        ]
        expected = [
            repr(item) for item in
            TestPlan.objects.filter(pk__in=descendant_ids).order_by('pk')
        ]
        plan: TestPlan = TestPlan.objects.get(pk=self.plan_3.pk)
        self.assertQuerysetEqual(
            plan.get_descendants().order_by('pk'), expected)

    def test_get_direct_descendants(self):
        test_data = [
            [self.plan.pk, [self.plan_2.pk]],
            [self.plan_5.pk, []],
            [self.plan_3.pk, [self.plan_4.pk, self.plan_7.pk]],
        ]

        for parent_plan, expected in test_data:
            plan: TestPlan = TestPlan.objects.get(pk=parent_plan)
            self.assertListEqual(expected, sorted(plan.get_descendant_ids(True)))

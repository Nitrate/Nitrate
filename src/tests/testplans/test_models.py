# -*- coding: utf-8 -*-

from django.conf import settings
from django import test
from mock import patch

from tcms.testplans.models import _disconnect_signals
from tcms.testplans.models import _listen
from tests.factories import TestCaseFactory
from tests.factories import TestPlanEmailSettingsFactory
from tests.factories import TestPlanFactory
from tests.factories import UserFactory

from tcms.testplans.helpers.email import get_plan_notification_recipients


class TestSendEmailOnPlanUpdated(test.TestCase):
    """Test send email on a plan is updated"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = UserFactory(username='owner', email='owner@example.com')
        cls.plan = TestPlanFactory(owner=cls.owner, author=cls.owner)
        TestPlanEmailSettingsFactory(
            auto_to_plan_owner=True,
            auto_to_plan_author=True,
            notify_on_plan_update=True,
            plan=cls.plan)

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
        cls.owner = UserFactory(username='owner', email='owner@example.com')
        cls.plan = TestPlanFactory(owner=cls.owner, author=cls.owner)
        TestPlanEmailSettingsFactory(
            auto_to_plan_owner=True,
            auto_to_plan_author=True,
            notify_on_plan_delete=True,
            plan=cls.plan)

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
        cls.owner = UserFactory(username='user1', email='user1@example.com')
        cls.plan = TestPlanFactory(owner=cls.owner, author=cls.owner)
        cls.case_1 = TestCaseFactory(
            author=UserFactory(username='user2', email='user2@example.com'),
            default_tester=UserFactory(username='user3',
                                       email='user3@example.com'),
            plan=[cls.plan])
        cls.case_2 = TestCaseFactory(
            author=UserFactory(username='user4', email='user4@example.com'),
            default_tester=UserFactory(username='user5',
                                       email='user5@example.com'),
            plan=[cls.plan])
        cls.case_3 = TestCaseFactory(
            author=UserFactory(username='user6', email='user6@example.com'),
            default_tester=UserFactory(username='user7', email=''),
            plan=[cls.plan])

        TestPlanEmailSettingsFactory(
            auto_to_plan_owner=True,
            auto_to_plan_author=True,
            auto_to_case_owner=True,
            auto_to_case_default_tester=True,
            plan=cls.plan)

    def test_collect_recipients(self):
        recipients = get_plan_notification_recipients(self.plan)
        self.assertEqual([
            'user1@example.com',
            'user2@example.com',
            'user3@example.com',
            'user4@example.com',
            'user5@example.com',
            'user6@example.com',
        ], sorted(recipients))

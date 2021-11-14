# -*- coding: utf-8 -*-

from django import test
from django.core import mail
from django.db.models.signals import post_save

from tcms.testruns.models import TestRun
from tcms.testruns.signals import mail_notify_on_test_run_creation_or_update
from tests import BaseCaseRun
from tests import factories as f


class TestRunGetIssuesCount(BaseCaseRun):
    """Test TestRun.get_issues_count"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.empty_test_run = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            manager=cls.tester,
            default_tester=cls.tester,
        )
        cls.test_run_no_issues = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            manager=cls.tester,
            default_tester=cls.tester,
        )

        cls.bz_tracker = cls.create_bz_tracker()

        cls.case_run_1.add_issue("12345", cls.bz_tracker)
        cls.case_run_1.add_issue("909090", cls.bz_tracker)
        cls.case_run_3.add_issue("4567890", cls.bz_tracker)

    def test_get_issues_count_if_no_issue_added(self):
        self.assertEqual(0, self.empty_test_run.get_issues_count())
        self.assertEqual(0, self.test_run_no_issues.get_issues_count())

    def test_get_issues_count(self):
        self.assertEqual(3, self.test_run.get_issues_count())


class TestSendMailNotifyOnTestRunCreation(test.TestCase):
    """Test mail notification on new test run creation"""

    def setUp(self):
        mail.outbox = []
        post_save.connect(mail_notify_on_test_run_creation_or_update, sender=TestRun)

    def tearDown(self):
        post_save.disconnect(mail_notify_on_test_run_creation_or_update, sender=TestRun)

    def test_notify(self):
        run = f.TestRunFactory()

        out_mail = mail.outbox[0]

        self.assertEqual(run.get_notification_recipients(), out_mail.recipients())
        self.assertEqual(
            f"A new test run is created from plan {run.plan.pk}: {run.summary}",
            out_mail.subject,
        )
        self.assertIn(f"A new test run {run.pk} has been created for you.", out_mail.body)


class TestSendMailNotifyOnTestRunUpdate(test.TestCase):
    """Test mail notification on a test run is updated"""

    @classmethod
    def setUpTestData(cls):
        cls.test_run = f.TestRunFactory()

    def setUp(self):
        mail.outbox = []
        post_save.connect(mail_notify_on_test_run_creation_or_update, sender=TestRun)

    def tearDown(self):
        post_save.disconnect(mail_notify_on_test_run_creation_or_update, sender=TestRun)

    def test_notify(self):
        self.test_run.summary = "A new test run for mail notify"
        self.test_run.save()

        out_mail = mail.outbox[0]

        self.assertEqual(self.test_run.get_notification_recipients(), out_mail.recipients())
        self.assertEqual(
            f"Test Run {self.test_run.pk} - " f"{self.test_run.summary} has been updated",
            out_mail.subject,
        )
        self.assertIn(f"Test run {self.test_run.pk} has been updated for you.", out_mail.body)

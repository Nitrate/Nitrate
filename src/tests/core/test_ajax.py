# -*- coding: utf-8 -*-

import unittest
from http import HTTPStatus
from textwrap import dedent

from django import test
from django.core import mail
from django.core.mail import EmailMessage
from django.urls import reverse
from tcms.core.ajax import strip_parameters
from tcms.testcases.models import TestCase
from tcms.testruns.models import TestCaseRun
from tests import factories as f, BasePlanCase, BaseCaseRun
from tests import AuthMixin, HelperAssertions, user_should_have_perm


class TestStripParameters(unittest.TestCase):

    def setUp(self):
        self.request_dict = {
            'name__startswith': 'something',
            'info_type': 'tags',
            'format': 'ulli',
            'case__plan': 1,
            'field': 'tag__name',
        }
        self.internal_parameters = ('info_type', 'field', 'format')

    def test_remove_parameters_in_dict(self):
        simplified_dict = strip_parameters(self.request_dict, self.internal_parameters)
        for p in self.internal_parameters:
            self.assertFalse(p in simplified_dict)

        self.assertEqual('something', simplified_dict['name__startswith'])
        self.assertEqual(1, simplified_dict['case__plan'])

    def test_remove_parameters_not_in_dict(self):
        simplified_dict = strip_parameters(self.request_dict, ['non-existing-parameter'])
        self.assertEqual(self.request_dict, simplified_dict)


class TestUpdateCasesDefaultTester(AuthMixin, HelperAssertions, test.TestCase):
    """Test set default tester to selected cases"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.plan = f.TestPlanFactory(owner=cls.tester, author=cls.tester)
        cls.case_1 = f.TestCaseFactory(
            author=cls.tester, reviewer=cls.tester, default_tester=None,
            plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(
            author=cls.tester, reviewer=cls.tester, default_tester=None,
            plan=[cls.plan])

        user_should_have_perm(cls.tester, 'testcases.change_testcase')

        cls.user_1 = f.UserFactory(username='user1')
        cls.url = reverse('ajax-update-cases-default-tester')

    def test_set_default_tester(self):
        resp = self.client.post(self.url, data={
            'from_plan': self.plan.pk,
            'case': [self.case_1.pk, self.case_2.pk],
            'target_field': 'default_tester',
            'new_value': self.user_1.username,
        })

        self.assertJsonResponse(resp, {})

        for case in [self.case_1, self.case_2]:
            case.refresh_from_db()
            self.assertEqual(self.user_1, case.default_tester)

    def test_given_username_does_not_exist(self):
        resp = self.client.post(self.url, data={
            'from_plan': self.plan.pk,
            'case': [self.case_1.pk, self.case_2.pk],
            'target_field': 'default_tester',
            'new_value': 'unknown',
        })

        self.assertJsonResponse(
            resp,
            {
                'message': 'unknown cannot be set as a default tester, '
                           'since this user does not exist.'
            },
            status_code=HTTPStatus.NOT_FOUND
        )

        for case in [self.case_1, self.case_2]:
            case.refresh_from_db()
            self.assertIsNone(case.default_tester)


class TestSendMailNotifyOnCaseRunAssigneeIsChanged(BaseCaseRun):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, 'testruns.change_testcaserun')
        cls.assignee = f.UserFactory(username='expert-tester')

    def test_ensure_mail_notify_is_sent(self):
        mail.outbox = []

        self.login_tester()
        resp = self.client.post(reverse('ajax-update'), data={
            'content_type': 'testruns.testcaserun',
            'value_type': 'int',
            'object_pk': f'{self.case_run_1.pk},{self.case_run_3.pk}',
            'field': 'assignee',
            'value': self.assignee.pk,
        })
        self.assertEqual(200, resp.status_code)

        case_run_1: TestCaseRun = TestCaseRun.objects.get(pk=self.case_run_1.pk)
        self.assertEqual(self.assignee, case_run_1.assignee)
        case_run_2: TestCaseRun = TestCaseRun.objects.get(pk=self.case_run_3.pk)
        self.assertEqual(self.assignee, case_run_2.assignee)

        out_mail = mail.outbox[0]
        self.assertEqual(
            f'Assignee of run {self.test_run.pk} has been changed',
            out_mail.subject
        )
        self.assertSetEqual(set(self.test_run.get_notification_recipients()),
                            set(out_mail.recipients()))

        expected_body = dedent(f'''\
            ### Links ###
            Test run: {self.test_run.get_full_url()}

            ### Info ###
            The assignee of case run in test run {self.test_run.pk}: {self.test_run.summary}
            has been changed: Following is the new status:

            ### Test case runs information ###

            * {case_run_1.pk}: {case_run_1.case.summary} - {case_run_1.assignee}
            * {case_run_2.pk}: {case_run_2.case.summary} - {case_run_2.assignee}''')

        self.assertEqual(expected_body, out_mail.body)


class TestSendMailNotifyOnTestCaseReviewerIsChanged(BasePlanCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, 'testcases.change_testcase')
        cls.reviewer = f.UserFactory(username='case-reviewer')

    def test_ensure_mail_notify_is_sent(self):
        mail.outbox = []

        self.login_tester()
        resp = self.client.post(reverse('ajax-update-cases-reviewer'), data={
            'from_plan': self.plan.pk,
            'case': [self.case.pk, self.case_2.pk],
            'target_field': 'reviewer',
            'new_value': self.reviewer.username,
        })
        self.assertEqual(200, resp.status_code)

        case = TestCase.objects.get(pk=self.case.pk)
        self.assertEqual(self.reviewer.username, case.reviewer.username)
        case = TestCase.objects.get(pk=self.case_2.pk)
        self.assertEqual(self.reviewer.username, case.reviewer.username)

        out_mail: EmailMessage = mail.outbox[0]

        self.assertEqual('You have been the reviewer of cases', out_mail.subject)
        self.assertListEqual([self.reviewer.email], out_mail.recipients())

        assigned_by = self.tester.username
        expected_body = dedent(f'''\
            You have been assigned as the reviewer of the following Test Cases by {assigned_by}.


            ### Test cases information ###
            [{self.case.pk}] {self.case.summary} - {self.case.get_full_url()}
            [{self.case_2.pk}] {self.case_2.summary} - {self.case_2.get_full_url()}
        ''')

        self.assertEqual(expected_body, out_mail.body)

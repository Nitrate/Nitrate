# -*- coding: utf-8 -*-

import operator

from datetime import datetime
from unittest.mock import patch

from tcms.comments.models import add_comment
from tcms.testruns.data import TestCaseRunDataMixin
from tcms.testruns.data import stats_caseruns_status
from tests import factories as f
from tests import BaseCaseRun
from tests import BasePlanCase


class TestGetCaseRunsStatsByStatusFromEmptyTestRun(BasePlanCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.empty_test_run = f.TestRunFactory(
            manager=cls.tester,
            default_tester=cls.tester,
            plan=cls.plan)

        cls.case_run_statuss = f.TestCaseRunStatus.objects.all().order_by('pk')

    def test_get_from_empty_case_runs(self):
        data = stats_caseruns_status(self.empty_test_run.pk,
                                     self.case_run_statuss)

        subtotal = {status.pk: [0, status] for status in self.case_run_statuss}

        self.assertEqual(subtotal, data.StatusSubtotal)
        self.assertEqual(0, data.CaseRunsTotalCount)
        self.assertEqual(.0, data.CompletedPercentage)
        self.assertEqual(.0, data.FailurePercentage)


class TestGetCaseRunsStatsByStatus(BasePlanCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_run_statuss = f.TestCaseRunStatus.objects.all().order_by('pk')

        get_status = f.TestCaseRunStatus.objects.get
        cls.case_run_status_idle = get_status(name='IDLE')
        cls.case_run_status_failed = get_status(name='FAILED')
        cls.case_run_status_waived = get_status(name='WAIVED')

        cls.test_run = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            manager=cls.tester,
            default_tester=cls.tester)

        for case, status in ((cls.case_1, cls.case_run_status_idle),
                             (cls.case_2, cls.case_run_status_failed),
                             (cls.case_3, cls.case_run_status_failed),
                             (cls.case_4, cls.case_run_status_waived),
                             (cls.case_5, cls.case_run_status_waived),
                             (cls.case_6, cls.case_run_status_waived)):
            f.TestCaseRunFactory(
                assignee=cls.tester,
                tested_by=cls.tester,
                run=cls.test_run,
                case=case,
                case_run_status=status)

    def test_get_stats(self):
        data = stats_caseruns_status(self.test_run.pk, self.case_run_statuss)

        subtotal = {status.pk: [0, status] for status in self.case_run_statuss}
        subtotal[self.case_run_status_idle.pk][0] = 1
        subtotal[self.case_run_status_failed.pk][0] = 2
        subtotal[self.case_run_status_waived.pk][0] = 3

        expected_completed_percentage = 5.0 * 100 / 6
        expected_failure_percentage = 2.0 * 100 / 5

        self.assertEqual(subtotal, data.StatusSubtotal)
        self.assertEqual(6, data.CaseRunsTotalCount)
        self.assertEqual(expected_completed_percentage, data.CompletedPercentage)
        self.assertEqual(expected_failure_percentage, data.FailurePercentage)


class TestGetCaseRunsComments(BaseCaseRun):
    """Test TestCaseRunDataMixin.get_caseruns_comments

    There are two test runs created already, cls.test_run and cls.test_run_1.

    For this case, comments will be added to cls.test_run_1 in order to ensure
    comments could be retrieved correctly. And another one is for ensuring
    empty result even if no comment is added.
    """

    def test_get_empty_comments_if_no_comment_there(self):
        data = TestCaseRunDataMixin()
        comments = data.get_caseruns_comments(self.test_run.pk)
        self.assertEqual({}, comments)

    @patch('django.utils.timezone.now')
    def test_get_comments(self, now):
        now.return_value = datetime(2017, 7, 7, 7, 7, 7)

        add_comment(
            self.tester,
            'testruns.testcaserun', [self.case_run_4.pk, self.case_run_5.pk],
            'new comment')
        add_comment(
            self.tester, 'testruns.testcaserun', [self.case_run_4.pk],
            'make better')

        data = TestCaseRunDataMixin()
        comments = data.get_caseruns_comments(self.test_run_1.pk)

        comments[self.case_run_4.pk] = sorted(
            comments[self.case_run_4.pk], key=operator.itemgetter('comment'))

        expected_comments = {
            self.case_run_4.pk: [
                {
                    'case_run_id': self.case_run_4.pk,
                    'user_name': self.tester.username,
                    'submit_date': now.return_value,
                    'comment': 'make better'
                },
                {
                    'case_run_id': self.case_run_4.pk,
                    'user_name': self.tester.username,
                    'submit_date': now.return_value,
                    'comment': 'new comment'
                },
            ],
            self.case_run_5.pk: [
                {
                    'case_run_id': self.case_run_5.pk,
                    'user_name': self.tester.username,
                    'submit_date': now.return_value,
                    'comment': 'new comment'
                }
            ]
        }

        self.assertEqual(expected_comments, comments)

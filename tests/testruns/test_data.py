# -*- coding: utf-8 -*-

import operator
from datetime import datetime
from unittest.mock import patch

from tcms.comments.models import add_comment
from tcms.testruns.data import TestCaseRunDataMixin, stats_case_runs_status
from tests import BaseCaseRun, BasePlanCase
from tests import factories as f


class TestGetCaseRunsStatsByStatusFromEmptyTestRun(BasePlanCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.empty_test_run = f.TestRunFactory(
            manager=cls.tester, default_tester=cls.tester, plan=cls.plan
        )

    def test_get_from_empty_case_runs(self):
        pk = self.empty_test_run.pk
        data = stats_case_runs_status([pk])[pk]

        self.assertEqual(0, data.total)
        self.assertEqual(0.0, data.complete_percent)
        self.assertEqual(0.0, data.failure_percent_in_complete)


class TestGetCaseRunsStatsByStatus(BasePlanCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        get_status = f.TestCaseRunStatus.objects.get
        cls.case_run_status_idle = get_status(name="IDLE")
        cls.case_run_status_failed = get_status(name="FAILED")
        cls.case_run_status_waived = get_status(name="WAIVED")

        cls.test_run = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            manager=cls.tester,
            default_tester=cls.tester,
        )

        for case, status in (
            (cls.case_1, cls.case_run_status_idle),
            (cls.case_2, cls.case_run_status_failed),
            (cls.case_3, cls.case_run_status_failed),
            (cls.case_4, cls.case_run_status_waived),
            (cls.case_5, cls.case_run_status_waived),
            (cls.case_6, cls.case_run_status_waived),
        ):
            f.TestCaseRunFactory(
                assignee=cls.tester,
                tested_by=cls.tester,
                run=cls.test_run,
                case=case,
                case_run_status=status,
            )

    def test_get_stats(self):
        pk = self.test_run.pk
        data = stats_case_runs_status([pk])[pk]

        expected_completed_percentage = 5.0 * 100 / 6
        expected_failure_percentage = 2.0 * 100 / 5

        self.assertEqual(6, data.total)
        self.assertEqual(expected_completed_percentage, data.complete_percent)
        self.assertEqual(expected_failure_percentage, data.failure_percent_in_complete)


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

    @patch("django.utils.timezone.now")
    def test_get_comments(self, now):
        now.return_value = datetime(2017, 7, 7, 7, 7, 7)

        add_comment(
            self.tester,
            "testruns.testcaserun",
            [self.case_run_4.pk, self.case_run_5.pk],
            "new comment",
        )
        add_comment(self.tester, "testruns.testcaserun", [self.case_run_4.pk], "make better")

        data = TestCaseRunDataMixin()
        comments = data.get_caseruns_comments(self.test_run_1.pk)

        comments[self.case_run_4.pk] = sorted(
            comments[self.case_run_4.pk], key=operator.itemgetter("comment")
        )

        expected_comments = {
            self.case_run_4.pk: [
                {
                    "case_run_id": self.case_run_4.pk,
                    "user_name": self.tester.username,
                    "submit_date": now.return_value,
                    "comment": "make better",
                },
                {
                    "case_run_id": self.case_run_4.pk,
                    "user_name": self.tester.username,
                    "submit_date": now.return_value,
                    "comment": "new comment",
                },
            ],
            self.case_run_5.pk: [
                {
                    "case_run_id": self.case_run_5.pk,
                    "user_name": self.tester.username,
                    "submit_date": now.return_value,
                    "comment": "new comment",
                }
            ],
        }

        self.assertEqual(expected_comments, comments)

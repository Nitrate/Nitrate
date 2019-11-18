# -*- coding: utf-8 -*-

from tests import factories as f, BaseCaseRun


class TestRunGetIssuesCount(BaseCaseRun):
    """Test TestRun.get_issues_count"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.empty_test_run = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            manager=cls.tester,
            default_tester=cls.tester)
        cls.test_run_no_issues = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            manager=cls.tester,
            default_tester=cls.tester)

        cls.bz_tracker = cls.create_bz_tracker()

        cls.case_run_1.add_issue('12345', cls.bz_tracker)
        cls.case_run_1.add_issue('909090', cls.bz_tracker)
        cls.case_run_3.add_issue('4567890', cls.bz_tracker)

    def test_get_issues_count_if_no_issue_added(self):
        self.assertEqual(0, self.empty_test_run.get_issues_count())
        self.assertEqual(0, self.test_run_no_issues.get_issues_count())

    def test_get_issues_count(self):
        self.assertEqual(3, self.test_run.get_issues_count())

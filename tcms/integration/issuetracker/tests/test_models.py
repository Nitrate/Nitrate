# -*- coding: utf-8 -*-

import tcms.integration.issuetracker.factories as f

from django import test
from tcms.tests import HelperAssertions


class TestIssueTrackerValidation(HelperAssertions, test.TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tracker_product = f.IssueTrackerProductFactory(name='CoolIssueTracker')

    def test_validate_issue_report_params(self):
        st = f.IssueTrackerFactory(tracker_product=self.tracker_product)
        st.issue_report_params = 'product=name'
        self.assertValidationError(
            'issue_report_params', r"Line .+ is not a pair of key/value separated by ':'",
            st.full_clean)

        st = f.IssueTrackerFactory(tracker_product=self.tracker_product)
        st.issue_report_params = 'product: name\ncustom_field: a:b:c'
        self.assertValidationError(
            'issue_report_params', r"Line .+ contains multiple ':'", st.full_clean)

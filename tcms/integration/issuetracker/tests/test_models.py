# -*- coding: utf-8 -*-

import re
import tcms.integration.issuetracker.factories as f
from django import test
from django.core.exceptions import ValidationError


class Assertions(object):

    def assertValidationError(self, field, message_regex, func, *args, **kwargs):
        """Assert django.core.exceptions.ValidationError is raised with expected message"""
        try:
            func(*args, **kwargs)
        except Exception as e:
            self.assertIsInstance(
                e, ValidationError, 'Exception {} is not a ValidationError.'.format(e))
            self.assertIn(field, e.message_dict,
                          'Field {} is not included in errors.'.format(field))
            matches = [re.search(message_regex, item) is not None
                       for item in e.message_dict[field]]
            self.assertTrue(any(matches), 'Expected match message is not included.')
        else:
            self.fail('ValidationError is not raised.')


class TestIssueTrackerValidation(Assertions, test.TestCase):

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

# -*- coding: utf-8 -*-

import io
import os
import re
import tempfile

from django import test
from tcms.issuetracker.models import CredentialTypes
from tests import HelperAssertions
import tests.factories as f


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


class TestGetIssueTrackerCredential(test.TestCase):
    """Test IssueTracker property credential"""

    def setUp(self):
        fd, self.user_pwd_secret_file = tempfile.mkstemp()
        with io.open(fd, 'w', encoding='utf-8') as f:
            f.write('[issuetracker]\nusername = admin\npassword = admin\n')

        fd, self.token_secret_file = tempfile.mkstemp()
        with io.open(fd, 'w', encoding='utf-8') as f:
            f.write('[issuetracker]\ntoken = abcde\n')

    def tearDown(self):
        os.unlink(self.user_pwd_secret_file)
        os.unlink(self.token_secret_file)

    def test_get_noneed_credential(self):
        issue_tracker = f.IssueTrackerFactory(
            credential_type=CredentialTypes.NoNeed.name)
        self.assertEqual({}, issue_tracker.credential)

    def test_get_user_pwd_credential_from_secret_file(self):
        issue_tracker = f.IssueTrackerFactory(
            credential_type=CredentialTypes.UserPwd.name)
        f.UserPwdCredentialFactory(
            secret_file=self.user_pwd_secret_file,
            issue_tracker=issue_tracker)
        self.assertEqual({'username': 'admin', 'password': 'admin'},
                         issue_tracker.credential)

    def test_get_user_pwd_credential_from_database(self):
        issue_tracker = f.IssueTrackerFactory(
            credential_type=CredentialTypes.UserPwd.name)
        f.UserPwdCredentialFactory(
            username='abc',
            password='abc',
            issue_tracker=issue_tracker)
        self.assertEqual({'username': 'abc', 'password': 'abc'},
                         issue_tracker.credential)

    def test_get_token_credential_from_secret_file(self):
        issue_tracker = f.IssueTrackerFactory(
            credential_type=CredentialTypes.Token.name)
        f.TokenCredentialFactory(
            secret_file=self.token_secret_file,
            issue_tracker=issue_tracker)
        self.assertEqual({'token': 'abcde'}, issue_tracker.credential)

    def test_get_token_credential_from_database(self):
        issue_tracker = f.IssueTrackerFactory(
            credential_type=CredentialTypes.Token.name)
        f.TokenCredentialFactory(
            token='234wer',
            issue_tracker=issue_tracker)
        self.assertEqual({'token': '234wer'}, issue_tracker.credential)

    def assert_property_credential(self, issue_tracker):
        try:
            issue_tracker.credential
        except ValueError as e:
            if not re.search(r'credential is not set', str(e)):
                self.fail('Expected ValueError is not raised. Instead, another'
                          ' ValueError is raised with message: {}'
                          .format(str(e)))
        else:
            self.fail('Expected ValueError is not raised.')

    def test_user_pwd_credential_not_set(self):
        issue_tracker = f.IssueTrackerFactory(
            credential_type=CredentialTypes.UserPwd.name)
        self.assert_property_credential(issue_tracker)

    def test_token_credential_not_set(self):
        issue_tracker = f.IssueTrackerFactory(
            credential_type=CredentialTypes.Token.name)
        self.assert_property_credential(issue_tracker)

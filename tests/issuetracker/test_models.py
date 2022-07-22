# -*- coding: utf-8 -*-

import io
import os
import re
import tempfile
from unittest.mock import MagicMock, patch

from django import test

import tests.factories as f
from tcms.issuetracker.models import CredentialTypes
from tests import HelperAssertions


class TestIssueTrackerValidation(HelperAssertions, test.TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tracker_product = f.IssueTrackerProductFactory(name="CoolIssueTracker")

    def test_invalid_issue_report_params(self):
        st = f.IssueTrackerFactory(tracker_product=self.tracker_product)
        st.issue_report_params = "product=name"
        self.assertValidationError(
            "issue_report_params",
            r"Line .+ is not a pair of key/value separated by ':'",
            st.full_clean,
        )

        st = f.IssueTrackerFactory(tracker_product=self.tracker_product)
        st.issue_report_params = "product: name\ncustom_field: a:b:c"
        self.assertValidationError(
            "issue_report_params", r"Line .+ contains multiple ':'", st.full_clean
        )

    def test_invalid_class_path(self):
        tracker = f.IssueTrackerFactory(
            tracker_product=self.tracker_product,
            class_path="a.b.c",
            issues_display_url_fmt="http://localhost/{issue_keys}",
        )
        self.assertValidationError("class_path", r"Cannot import a\.b", tracker.full_clean)

    def test_member_name_does_not_exist_in_imported_module(self):
        tracker = f.IssueTrackerFactory(
            tracker_product=self.tracker_product,
            class_path="tracker.klass",
            issues_display_url_fmt="http://localhost/{issue_keys}",
        )

        with patch("importlib.import_module") as import_module:
            # A magic mock to fail function hasattr to find out attribute name klass
            import_module.return_value = MagicMock(spec=object())
            self.assertValidationError(
                "class_path",
                "Module tracker does not have class klass",
                tracker.full_clean,
            )

    def test_invalid_regex_for_validating_issue_id(self):
        tracker = f.IssueTrackerFactory(
            tracker_product=self.tracker_product,
            issues_display_url_fmt="http://localhost/{issue_keys}",
            validate_regex="[0-9}+",
        )

        self.assertValidationError("validate_regex", "cannot be compiled", tracker.full_clean)


class TestGetIssueTrackerCredential(test.TestCase):
    """Test IssueTracker property credential"""

    def setUp(self):
        fd, self.user_pwd_secret_file = tempfile.mkstemp()
        with io.open(fd, "w", encoding="utf-8") as f:
            f.write("[issuetracker]\nusername = admin\npassword = admin\n")

        fd, self.token_secret_file = tempfile.mkstemp()
        with io.open(fd, "w", encoding="utf-8") as f:
            f.write("[issuetracker]\ntoken = abcde\n")

    def tearDown(self):
        os.unlink(self.user_pwd_secret_file)
        os.unlink(self.token_secret_file)

    def test_get_noneed_credential(self):
        issue_tracker = f.IssueTrackerFactory(credential_type=CredentialTypes.NoNeed.name)
        self.assertEqual({}, issue_tracker.credential)

    def test_get_user_pwd_credential_from_secret_file(self):
        issue_tracker = f.IssueTrackerFactory(credential_type=CredentialTypes.UserPwd.name)
        f.UserPwdCredentialFactory(
            secret_file=self.user_pwd_secret_file, issue_tracker=issue_tracker
        )
        self.assertEqual({"username": "admin", "password": "admin"}, issue_tracker.credential)

    def test_get_user_pwd_credential_from_database(self):
        issue_tracker = f.IssueTrackerFactory(credential_type=CredentialTypes.UserPwd.name)
        f.UserPwdCredentialFactory(username="abc", password="abc", issue_tracker=issue_tracker)
        self.assertEqual({"username": "abc", "password": "abc"}, issue_tracker.credential)

    def test_get_token_credential_from_secret_file(self):
        issue_tracker = f.IssueTrackerFactory(credential_type=CredentialTypes.Token.name)
        f.TokenCredentialFactory(secret_file=self.token_secret_file, issue_tracker=issue_tracker)
        self.assertEqual({"token": "abcde"}, issue_tracker.credential)

    def test_get_token_credential_from_database(self):
        issue_tracker = f.IssueTrackerFactory(credential_type=CredentialTypes.Token.name)
        f.TokenCredentialFactory(token="234wer", issue_tracker=issue_tracker)
        self.assertEqual({"token": "234wer"}, issue_tracker.credential)

    def assert_property_credential(self, issue_tracker):
        try:
            issue_tracker.credential
        except ValueError as e:
            if not re.search(r"credential is not set", str(e)):
                self.fail(
                    "Expected ValueError is not raised. Instead, another"
                    " ValueError is raised with message: {}".format(str(e))
                )
        else:
            self.fail("Expected ValueError is not raised.")

    def test_user_pwd_credential_not_set(self):
        issue_tracker = f.IssueTrackerFactory(credential_type=CredentialTypes.UserPwd.name)
        self.assert_property_credential(issue_tracker)

    def test_token_credential_not_set(self):
        issue_tracker = f.IssueTrackerFactory(credential_type=CredentialTypes.Token.name)
        self.assert_property_credential(issue_tracker)

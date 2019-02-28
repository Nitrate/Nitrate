# -*- coding: utf-8 -*-

import json
import re
import six

from six.moves import http_client
from six.moves.urllib_parse import urlparse, parse_qs

from django import test
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from tcms.testcases.models import TestCaseStatus
from tcms.testruns.models import TestCaseRunStatus
from tests.factories import ProductFactory
from tests.factories import TestBuildFactory
from tests.factories import TestCaseFactory
from tests.factories import TestCaseRunFactory
from tests.factories import TestPlanFactory
from tests.factories import TestRunFactory
from tests.factories import UserFactory
from tests.factories import VersionFactory

__all__ = (
    'user_should_have_perm',
    'remove_perm_from_user',
    'BasePlanCase',
    'BaseCaseRun',
    'encode_if_py3',
)


def encode_if_py3(s):
    """For running tests in Python 3

    This is added for running tests successfully with Python 3 while porting to
    Python 3 compatibility. But, it is really necessary to think about the
    XMLPRC API that strings returned should be in bytestring or not.
    """
    if six.PY3 and isinstance(s, six.text_type):
        return s.encode()
    else:
        return s


def user_should_have_perm(user, perm):
    if isinstance(perm, six.string_types):
        try:
            app_label, codename = perm.split('.')
        except ValueError:
            raise ValueError('%s is not valid. Should be in format app_label.perm_codename')
        else:
            if not app_label or not codename:
                raise ValueError('Invalid app_label or codename')
            get_permission = Permission.objects.get
            user.user_permissions.add(
                get_permission(content_type__app_label=app_label, codename=codename))
    elif isinstance(perm, Permission):
        user.user_permissions.add(perm)
    else:
        raise TypeError('perm should be an instance of either basestring or Permission')


def remove_perm_from_user(user, perm):
    """Remove a permission from an user"""

    if isinstance(perm, six.string_types):
        try:
            app_label, codename = perm.split('.')
        except ValueError:
            raise ValueError('%s is not valid. Should be in format app_label.perm_codename')
        else:
            if not app_label or not codename:
                raise ValueError('Invalid app_label or codename')
            get_permission = Permission.objects.get
            user.user_permissions.remove(
                get_permission(content_type__app_label=app_label, codename=codename))
    elif isinstance(perm, Permission):
        user.user_permissions.remove(perm)
    else:
        raise TypeError('perm should be an instance of either basestring or Permission')


def create_request_user(username=None, password=None):
    if username:
        user = UserFactory(username=username)
    else:
        user = UserFactory()
    if password:
        user.set_password(password)
    else:
        user.set_password('password')
    user.save()
    return user


class HelperAssertions(object):
    """Helper assertion methods"""

    def assert404(self, response):
        self.assertEqual(http_client.NOT_FOUND, response.status_code)

    def assertJsonResponse(self, response, expected, status_code=200):
        self.assertEqual(status_code, response.status_code)
        self.assertEqual(expected, json.loads(response.content))

    def assert_url(self, expected_url, url):
        """Check if two URL are same

        Assertions are called inside this this method. If anything is
        different, it will fail immediately.

        :param str expected_url: expected URL compare.
        :param str url: the URL to check if it is same as the expected URL.
        """
        url = urlparse(url)
        expected_url = urlparse(expected_url)

        self.assertEqual(expected_url.scheme, url.scheme)
        self.assertEqual(expected_url.netloc, url.netloc)
        self.assertEqual(expected_url.path, url.path)
        self.assertEqual(parse_qs(expected_url.query), parse_qs(url.query))

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


class NitrateTestCase(test.TestCase):
    """Base test case for writing tests for Nitrate"""

    @classmethod
    def create_bz_tracker(cls):
        """Helper function to create a Bugzilla issue tracker"""
        from tests.factories import IssueTrackerFactory
        return IssueTrackerFactory(
            name='bz',
            service_url='http://bugs.example.com/',
            issue_report_endpoint='/enter_bug.cgi',
            issue_url_fmt='http://bugs.example.com/?id={issue_key}',
            issues_display_url_fmt='http://bugs.example.com/?bug_id={issue_keys}',
            validate_regex=r'^\d+$')

    @classmethod
    def create_jira_tracker(cls):
        """Helper function to create a Bugzilla issue tracker"""
        from tests.factories import IssueTrackerFactory
        return IssueTrackerFactory(
            name='jira',
            service_url='http://jira.example.com/',
            issue_report_endpoint='/enter_bug.cgi',
            issue_url_fmt='http://jira.example.com/browse/{issue_key}',
            issues_display_url_fmt='http://jira.example.com/?jql=issuekey in ({issue_keys})',
            validate_regex=r'^[A-Z]+-\d+$')


class BasePlanCase(HelperAssertions, NitrateTestCase):
    """Base test case by providing essential Plan and Case objects used in tests"""

    @classmethod
    def setUpTestData(cls):
        cls.case_status_confirmed = TestCaseStatus.objects.get(name='CONFIRMED')
        cls.case_status_proposed = TestCaseStatus.objects.get(name='PROPOSED')

        cls.product = ProductFactory(name='Nitrate')
        cls.version = VersionFactory(value='0.1', product=cls.product)

        cls.tester = User.objects.create_user(
            username='nitrate-tester',
            email='nitrate-tester@example.com')
        cls.tester.set_password('password')
        cls.tester.save()

        cls.plan = TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version)

        cls.case = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan])
        cls.case_1 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan])
        cls.case_2 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan])
        cls.case_3 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan])

        cls.case_4 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan])
        cls.case_5 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan])
        cls.case_6 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan])

    def login_tester(self, user=None, password=None):
        """Login tester user for test

        Login pre-created tester user by default. If both user and password
        are given, login that user instead.
        """
        if user and password:
            login_user = user
            login_password = password
        else:
            login_user = self.tester
            login_password = 'password'

        self.client.login(username=login_user.username,
                          password=login_password)


class BaseCaseRun(BasePlanCase):
    """Base test case containing test run and case runs"""

    @classmethod
    def setUpTestData(cls):
        super(BaseCaseRun, cls).setUpTestData()

        cls.case_run_status_idle = TestCaseRunStatus.objects.get(name='IDLE')

        cls.build = TestBuildFactory(product=cls.product)

        cls.test_run = TestRunFactory(product_version=cls.version,
                                      plan=cls.plan,
                                      build=cls.build,
                                      manager=cls.tester,
                                      default_tester=cls.tester)

        cls.case_run_1, cls.case_run_2, cls.case_run_3 = [
            TestCaseRunFactory(assignee=cls.tester, tested_by=cls.tester,
                               run=cls.test_run, build=cls.build,
                               case_run_status=cls.case_run_status_idle,
                               case=case, sortkey=i * 10)
            for i, case in enumerate((cls.case_1, cls.case_2, cls.case_3), 1)]

        cls.test_run_1 = TestRunFactory(product_version=cls.version,
                                        plan=cls.plan,
                                        build=cls.build,
                                        manager=cls.tester,
                                        default_tester=cls.tester)

        cls.case_run_4, cls.case_run_5, cls.case_run_6 = [
            TestCaseRunFactory(assignee=cls.tester, tested_by=cls.tester,
                               run=cls.test_run_1, build=cls.build,
                               case_run_status=cls.case_run_status_idle,
                               case=case, sortkey=i * 10)
            for i, case in enumerate((cls.case_4, cls.case_5, cls.case_6), 1)]

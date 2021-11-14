# -*- coding: utf-8 -*-

import contextlib
import json
import re
from functools import partial
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from django import test
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.test import SimpleTestCase

from tcms.management.models import Classification, Product, Version
from tcms.testcases.models import TestCaseStatus
from tcms.testplans.models import TestPlan, TestPlanType
from tcms.testruns.models import TestCaseRunStatus
from tests import factories as f

__all__ = (
    "AuthMixin",
    "user_should_have_perm",
    "remove_perm_from_user",
    "BasePlanCase",
    "BaseCaseRun",
    "encode",
    "HelperAssertions",
    "BaseDataContext",
)


@contextlib.contextmanager
def no_raised_error():
    """Make it easy to write the parametrized test case"""
    yield


def encode(s):
    """For running tests in Python 3

    This is added for running tests successfully with Python 3 while porting to
    Python 3 compatibility. But, it is really necessary to think about the
    XMLPRC API that strings returned should be in bytestring or not.
    """
    if isinstance(s, str):
        return s.encode()
    else:
        return s


def user_should_have_perm(user, perm):
    if isinstance(perm, str):
        try:
            app_label, codename = perm.split(".")
        except ValueError:
            raise ValueError("%s is not valid. Should be in format app_label.perm_codename")
        else:
            if not app_label or not codename:
                raise ValueError("Invalid app_label or codename")
            get_permission = Permission.objects.get
            user.user_permissions.add(
                get_permission(content_type__app_label=app_label, codename=codename)
            )
    elif isinstance(perm, Permission):
        user.user_permissions.add(perm)
    else:
        raise TypeError("perm should be an instance of either basestring or Permission")


def remove_perm_from_user(user, perm):
    """Remove a permission from an user"""

    if isinstance(perm, str):
        try:
            app_label, codename = perm.split(".")
        except ValueError:
            raise ValueError("%s is not valid. Should be in format app_label.perm_codename")
        else:
            if not app_label or not codename:
                raise ValueError("Invalid app_label or codename")
            get_permission = Permission.objects.get
            user.user_permissions.remove(
                get_permission(content_type__app_label=app_label, codename=codename)
            )
    elif isinstance(perm, Permission):
        user.user_permissions.remove(perm)
    else:
        raise TypeError("perm should be an instance of either basestring or Permission")


def create_request_user(username=None, password=None):
    if username:
        user = f.UserFactory(username=username)
    else:
        user = f.UserFactory()
    if password:
        user.set_password(password)
    else:
        user.set_password("password")
    user.save()
    return user


class HelperAssertions(SimpleTestCase):
    """Helper assertion methods"""

    def assert200(self, response):
        self.assertEqual(HTTPStatus.OK, response.status_code)

    def assert301(self, response):
        self.assertEqual(HTTPStatus.MOVED_PERMANENTLY, response.status_code)

    def assert302(self, response):
        self.assertEqual(HTTPStatus.FOUND, response.status_code)

    def assert400(self, response):
        self.assertEqual(HTTPStatus.BAD_REQUEST, response.status_code)

    def assert403(self, response):
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_code)

    def assert404(self, response):
        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_code)

    def assert500(self, response):
        self.assertEqual(HTTPStatus.INTERNAL_SERVER_ERROR, response.status_code)

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
            self.assertIsInstance(e, ValidationError, f"Exception {e} is not a ValidationError.")
            self.assertIn(field, e.message_dict, f"Field {field} is not included in errors.")
            matches = [re.search(message_regex, item) is not None for item in e.message_dict[field]]
            self.assertTrue(any(matches), "Expected match message is not included.")
        else:
            self.fail("ValidationError is not raised.")


class AuthMixin(SimpleTestCase):

    # If every test requires an authenticated user to perform an HTTP request,
    # set this to True. This is helpful to avoid repeating
    # ``self.login_tester()`` or ``self.client.login(...)``.
    auto_login = False

    tester = None

    @classmethod
    def setUpTestData(cls):
        cls.tester = User.objects.create_user(
            username="nitrate-tester", email="nitrate-tester@example.com"
        )
        cls.tester.set_password("password")
        cls.tester.save()

    def setUp(self):
        if self.auto_login:
            self.login_tester()

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
            login_password = "password"

        self.client.login(username=login_user.username, password=login_password)


class NitrateTestCase(test.TestCase):
    """Base test case for writing tests for Nitrate"""

    @classmethod
    def create_bz_tracker(cls):
        """Helper function to create a Bugzilla issue tracker"""
        return f.IssueTrackerFactory(
            name="bz",
            service_url="http://bugs.example.com/",
            issue_report_endpoint="/enter_bug.cgi",
            issue_url_fmt="http://bugs.example.com/?id={issue_key}",
            issues_display_url_fmt="http://bugs.example.com/?bug_id={issue_keys}",
            validate_regex=r"^\d+$",
        )

    @classmethod
    def create_jira_tracker(cls):
        """Helper function to create a Bugzilla issue tracker"""
        return f.IssueTrackerFactory(
            name="jira",
            service_url="http://jira.example.com/",
            issue_report_endpoint="/enter_bug.cgi",
            issue_url_fmt="http://jira.example.com/browse/{issue_key}",
            issues_display_url_fmt="http://jira.example.com/?jql=issuekey in ({issue_keys})",
            validate_regex=r"^[A-Z]+-\d+$",
        )

    def get_max_plan_id(self):
        return TestPlan.objects.aggregate(max_pk=Max("pk"))["max_pk"]


class BasePlanCase(AuthMixin, HelperAssertions, NitrateTestCase):
    """Base test case by providing essential Plan and Case objects used in tests"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_status_confirmed = TestCaseStatus.objects.get(name="CONFIRMED")
        cls.case_status_proposed = TestCaseStatus.objects.get(name="PROPOSED")

        cls.product = f.ProductFactory(name="Nitrate")
        cls.version = f.VersionFactory(value="0.1", product=cls.product)

        cls.plan = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        case_creator = partial(
            f.TestCaseFactory,
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan],
        )

        cls.case = case_creator(summary="Test case 0")
        cls.case_1 = case_creator(summary="Test case 1")
        cls.case_2 = case_creator(summary="Test case 2")
        cls.case_3 = case_creator(summary="Test case 3")
        cls.case_4 = case_creator(summary="Test case 4")
        cls.case_5 = case_creator(summary="Test case 5")
        cls.case_6 = case_creator(summary="Test case 6")

    @classmethod
    def create_treeview_data(cls):
        """Create data for testing plan tree view"""

        plan_creator = partial(
            f.TestPlanFactory,
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
        )

        # Sample tree view
        # plan 1
        #   plan 2
        #     plan 3
        #       plan 4
        #         plan 5
        #         plan 6
        #       plan 7
        #     plan 8

        cls.plan_2 = plan_creator(parent=cls.plan)
        cls.plan_3 = plan_creator(parent=cls.plan_2)
        cls.plan_4 = plan_creator(parent=cls.plan_3)
        cls.plan_5 = plan_creator(parent=cls.plan_4)
        cls.plan_6 = plan_creator(parent=cls.plan_4)
        cls.plan_7 = plan_creator(parent=cls.plan_3)
        cls.plan_8 = plan_creator(parent=cls.plan_2)

        # Floating plan used to test adding child plan
        cls.plan_9 = plan_creator()


class BaseCaseRun(BasePlanCase):
    """Base test case containing test run and case runs"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_run_status_idle = TestCaseRunStatus.objects.get(name="IDLE")
        cls.build = f.TestBuildFactory(product=cls.product)

        case_run_creator = partial(
            f.TestCaseRunFactory,
            assignee=cls.tester,
            tested_by=cls.tester,
            build=cls.build,
            case_run_status=cls.case_run_status_idle,
        )

        cls.test_run = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            build=cls.build,
            manager=cls.tester,
            default_tester=cls.tester,
        )

        cls.case_run_1 = case_run_creator(run=cls.test_run, case=cls.case_1, sortkey=10)

        cls.case_run_2 = case_run_creator(run=cls.test_run, case=cls.case_2, sortkey=20)

        cls.case_run_3 = case_run_creator(run=cls.test_run, case=cls.case_3, sortkey=30)

        cls.test_run_1 = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            build=cls.build,
            manager=cls.tester,
            default_tester=cls.tester,
        )

        cls.case_run_4 = case_run_creator(run=cls.test_run_1, case=cls.case_4, sortkey=10)

        cls.case_run_5 = case_run_creator(run=cls.test_run_1, case=cls.case_5, sortkey=20)

        cls.case_run_6 = case_run_creator(run=cls.test_run_1, case=cls.case_6, sortkey=30)


class BaseDataContext:
    classification: Classification = None
    product: Product = None
    product_version: Version = None
    p1 = None
    p2 = None
    p3 = None
    dev_build = None
    alpha_build = None
    candidate_build = None

    # for case
    case_status_proposed = None
    case_status_confirmed = None
    case_status_disabled = None
    case_status_need_update = None
    case_category_smoke = None
    case_category_regression = None

    # for plan
    plan_type_function: TestPlanType = None
    plan_type_smoke: TestPlanType = None
    plan_type_regression: TestPlanType = None

    # for run and case run
    case_run_status_idle = None
    case_run_status_running = None
    case_run_status_failed = None

    # helper actions
    plan_creator = None
    case_creator = None
    run_creator = None

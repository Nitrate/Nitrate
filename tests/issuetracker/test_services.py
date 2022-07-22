# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock

from django import test

from tcms.issuetracker import services
from tcms.issuetracker.services import IssueTrackerService
from tests import BaseCaseRun
from tests import factories as f


class TestFindService(test.TestCase):
    """Test factory method find_service"""

    @classmethod
    def setUpTestData(cls):
        cls.issue_tracker_1 = f.IssueTrackerFactory()
        cls.issue_tracker_2 = f.IssueTrackerFactory()

    def test_class_path_must_be_set(self):
        self.issue_tracker_1.class_path = ""
        self.assertRaisesRegex(
            ValueError,
            "class_path must be set",
            services.find_service,
            self.issue_tracker_1,
        )

    def test_find_the_service(self):
        srv = services.find_service(self.issue_tracker_2)
        self.assertTrue(isinstance(srv, services.IssueTrackerService))
        self.assertEqual(self.issue_tracker_2, srv.tracker_model)


class TestBaseIssueTrackerService(BaseCaseRun):
    """Test default issue tracker behaviors"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tracker_product = f.IssueTrackerProductFactory()

    def test_get_issue_report_url(self):
        tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            tracker_product=self.tracker_product,
        )
        s = IssueTrackerService(tracker)
        url = s.make_issue_report_url(self.case_run_1)
        self.assertEqual("http://localhost/enter_bug.cgi", url)

    def test_subclass_could_provide_extra_issue_report_url_args(self):
        class CoolService(IssueTrackerService):
            def get_extra_issue_report_url_args(self, case_run):
                return {"body": "content"}

        fake_tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            tracker_product=self.tracker_product,
            issue_report_endpoint="/new_issue",
            issue_report_params="subject: hello",
        )

        service = CoolService(fake_tracker)
        url = service.make_issue_report_url(self.case_run_1)

        expected_url = "http://localhost/new_issue?subject=hello&body=content"
        self.assert_url(expected_url, url)

    def test_extra_arg_is_overwritten_by_predefined_service_supported_arg(self):
        class CoolService(IssueTrackerService):
            def get_extra_issue_report_url_args(self, case_run):
                return {"body": "content"}

        fake_tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            tracker_product=self.tracker_product,
            issue_report_endpoint="/new_issue",
            # body listed here will overwrite that body above
            issue_report_params="subject: hello\nbody: write content here",
        )

        service = CoolService(fake_tracker)
        url = service.make_issue_report_url(self.case_run_1)

        expected_url = "http://localhost/new_issue?subject=hello&body=write%20content%20here"
        self.assert_url(expected_url, url)

    def test_use_service_supported_args(self):
        """
        Ensure supported args listed in issue_report_params are filled with
        correct value.
        """

        class CoolService(IssueTrackerService):
            def get_stock_issue_report_args(self, case_run):
                return {
                    "case_summary": "test case 1",
                    "verbose": True,
                }

        fake_tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            tracker_product=self.tracker_product,
            issue_report_endpoint="/new_issue",
            # case_summary should be in the final URL with supported value.
            issue_report_params="subject: hello\ncase_summary:",
        )

        service = CoolService(fake_tracker)
        url = service.make_issue_report_url(self.case_run_1)

        expected_url = "http://localhost/new_issue?subject=hello&case_summary=test%20case%201"
        self.assert_url(expected_url, url)


class TestMakeIssueReportURLForBugzilla(BaseCaseRun):
    """Test the default behavior of Bugzilla to make issue report URL"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.cp_db = f.ComponentFactory(name="db")
        cls.cp_docs = f.ComponentFactory(name="docs")

        f.TestCaseComponentFactory(case=cls.case_1, component=cls.cp_db)
        f.TestCaseComponentFactory(case=cls.case_1, component=cls.cp_docs)

        cls.tracker = f.IssueTrackerProductFactory(name="myissuetracker")

        cls.issue_tracker_bz = f.IssueTrackerFactory(
            service_url="http://bugs.example.com",
            tracker_product=cls.tracker,
            issue_report_endpoint="/enter_bug.cgi",
            issue_report_params="product:\ncomponent:\n",
            issue_report_templ="content:",
        )

        PITRF = f.ProductIssueTrackerRelationshipFactory
        cls.rel_bz_product = PITRF(product=cls.product, issue_tracker=cls.issue_tracker_bz)

    def setUp(self):
        self.rel_bz_product.refresh_from_db()

    def test_use_default_values(self):
        srv = services.Bugzilla(self.issue_tracker_bz)
        url = srv.make_issue_report_url(self.case_run_1)

        expected_url = (
            "http://bugs.example.com/enter_bug.cgi?"
            "product={}&comment=content:&component=db&component=docs".format(self.product.name)
        )

        self.assert_url(expected_url, url)

    def test_alias_is_set(self):
        self.rel_bz_product.alias = "alternative-name"
        self.rel_bz_product.save(update_fields=["alias"])

        srv = services.Bugzilla(self.issue_tracker_bz)
        url = srv.make_issue_report_url(self.case_run_1)

        expected_url = (
            "http://bugs.example.com/enter_bug.cgi?"
            "product=alternative-name&comment=content:&"
            "component=db&component=docs"
        )

        self.assert_url(expected_url, url)

    def test_namespace_is_set(self):
        self.rel_bz_product.namespace = "upstream"
        self.rel_bz_product.save(update_fields=["namespace"])

        srv = services.Bugzilla(self.issue_tracker_bz)
        url = srv.make_issue_report_url(self.case_run_1)

        expected_url = (
            "http://bugs.example.com/enter_bug.cgi?"
            "product=upstream&comment=content:&component={}".format(self.product.name)
        )

        self.assert_url(expected_url, url)

    def test_use_alias_and_namespace_if_both_are_set(self):
        self.rel_bz_product.alias = "alternative-name"
        self.rel_bz_product.namespace = "upstream"
        self.rel_bz_product.save(update_fields=["alias", "namespace"])

        srv = services.Bugzilla(self.issue_tracker_bz)
        url = srv.make_issue_report_url(self.case_run_1)

        expected_url = (
            "http://bugs.example.com/enter_bug.cgi?"
            "product=upstream&comment=content:&component=alternative-name"
        )

        self.assert_url(expected_url, url)


class TestFormatIssuesDisplayURL(unittest.TestCase):
    """Test IssueTrackerService.make_issues_display_url_fmt"""

    def test_format_url(self):
        tracker = Mock(issues_display_url_fmt="http://bugs.example.com/?ids={issue_keys}")
        service = services.IssueTrackerService(tracker)
        url = service.make_issues_display_url([1, 2, 3, 4])

        expected_url = "http://bugs.example.com/?ids=1,2,3,4"
        self.assertEqual(expected_url, url)

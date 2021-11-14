# -*- coding: utf-8 -*-

import unittest
from datetime import datetime

from tcms.issuetracker.models import Issue
from tcms.linkreference.models import LinkReference
from tcms.testruns.models import TestCaseRunStatus
from tcms.xmlrpc.api import testcaserun
from tests import encode
from tests import factories as f
from tests.xmlrpc.utils import XmlrpcAPIBaseTest, make_http_request


class TestCaseRunCreate(XmlrpcAPIBaseTest):
    """Test testcaserun.create"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory(username="tcr_admin", email="tcr_admin@example.com")
        cls.staff = f.UserFactory(username="tcr_staff", email="tcr_staff@example.com")
        cls.default_tester = f.UserFactory(
            username="default_tester", email="default-tester@example.com"
        )
        cls.admin_request = make_http_request(user=cls.admin, user_perm="testruns.add_testcaserun")
        cls.staff_request = make_http_request(user=cls.staff)
        cls.product = f.ProductFactory(name="Nitrate")
        cls.version = f.VersionFactory(value="0.1", product=cls.product)
        cls.build = cls.product.build.all()[0]
        cls.plan = f.TestPlanFactory(author=cls.admin, owner=cls.admin, product=cls.product)
        cls.test_run = f.TestRunFactory(
            product_version=cls.version,
            build=cls.build,
            default_tester=None,
            plan=cls.plan,
        )
        cls.case_run_status = TestCaseRunStatus.objects.get(name="IDLE")
        cls.case = f.TestCaseFactory(author=cls.admin, default_tester=None, plan=[cls.plan])

        cls.case_run_pks = []

    def test_create_with_no_args(self):
        bad_args = (None, [], {}, (), 1, 0, -1, True, False, "", "aaaa", object)
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.create, self.admin_request, arg)

    def test_create_with_no_required_fields(self):
        values = [
            {
                "assignee": self.staff.pk,
                "case_run_status": self.case_run_status.pk,
                "notes": "unit test 2",
            },
            {
                "build": self.build.pk,
                "assignee": self.staff.pk,
                "case_run_status": 1,
                "notes": "unit test 2",
            },
            {
                "run": self.test_run.pk,
                "build": self.build.pk,
                "assignee": self.staff.pk,
                "case_run_status": self.case_run_status.pk,
                "notes": "unit test 2",
            },
        ]
        for value in values:
            self.assertXmlrpcFaultBadRequest(testcaserun.create, self.admin_request, value)

    def test_create_with_required_fields(self):
        tcr = testcaserun.create(
            self.admin_request,
            {
                "run": self.test_run.pk,
                "build": self.build.pk,
                "case": self.case.pk,
                "case_text_version": 15,
            },
        )
        self.assertIsNotNone(tcr)
        self.case_run_pks.append(tcr["case_run_id"])
        self.assertEqual(tcr["build_id"], self.build.pk)
        self.assertEqual(tcr["case_id"], self.case.pk)
        self.assertEqual(tcr["run_id"], self.test_run.pk)

    def test_create_with_all_fields(self):
        tcr = testcaserun.create(
            self.admin_request,
            {
                "run": self.test_run.pk,
                "build": self.build.pk,
                "case": self.case.pk,
                "assignee": self.admin.pk,
                "notes": "test_create_with_all_fields",
                "sortkey": 90,
                "case_run_status": self.case_run_status.pk,
                "case_text_version": 3,
            },
        )
        self.assertIsNotNone(tcr)
        self.case_run_pks.append(tcr["case_run_id"])
        self.assertEqual(tcr["build_id"], self.build.pk)
        self.assertEqual(tcr["case_id"], self.case.pk)
        self.assertEqual(tcr["assignee_id"], self.admin.pk)
        self.assertEqual(tcr["notes"], "test_create_with_all_fields")
        self.assertEqual(tcr["sortkey"], 90)
        self.assertEqual(tcr["case_run_status"], "IDLE")
        self.assertEqual(tcr["case_text_version"], 3)

    def test_create_with_non_exist_fields(self):
        values = [
            {
                "run": self.test_run.pk,
                "build": self.build.pk,
                "case": 111111,
            },
            {
                "run": 11111,
                "build": self.build.pk,
                "case": self.case.pk,
            },
            {
                "run": self.test_run.pk,
                "build": 11222222,
                "case": self.case.pk,
            },
        ]
        for value in values:
            self.assertXmlrpcFaultBadRequest(testcaserun.create, self.admin_request, value)

    def test_create_with_chinese(self):
        tcr = testcaserun.create(
            self.admin_request,
            {
                "run": self.test_run.pk,
                "build": self.build.pk,
                "case": self.case.pk,
                "notes": "开源中国",
                "case_text_version": 2,
            },
        )
        self.assertIsNotNone(tcr)
        self.case_run_pks.append(tcr["case_run_id"])
        self.assertEqual(tcr["build_id"], self.build.pk)
        self.assertEqual(tcr["case_id"], self.case.pk)
        self.assertEqual(tcr["assignee_id"], None)
        self.assertEqual(tcr["case_text_version"], 2)
        self.assertEqual(tcr["notes"], "\u5f00\u6e90\u4e2d\u56fd")

    def test_create_with_long_field(self):
        large_str = """aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        """
        tcr = testcaserun.create(
            self.admin_request,
            {
                "run": self.test_run.pk,
                "build": self.build.pk,
                "case": self.case.pk,
                "notes": large_str,
                "case_text_version": 2,
            },
        )
        self.assertIsNotNone(tcr)
        self.case_run_pks.append(tcr["case_run_id"])
        self.assertEqual(tcr["build_id"], self.build.pk)
        self.assertEqual(tcr["case_id"], self.case.pk)
        self.assertEqual(tcr["assignee_id"], None)
        self.assertEqual(tcr["case_text_version"], 2)
        self.assertEqual(tcr["notes"], large_str.strip())

    def test_create_with_no_perm(self):
        values = {
            "run": self.test_run.pk,
            "build": self.build.pk,
            "case": self.case.pk,
            "assignee": self.admin.pk,
            "notes": "test_create_with_all_fields",
            "sortkey": 2,
            "case_run_status": self.case_run_status.pk,
        }
        self.assertXmlrpcFaultForbidden(testcaserun.create, self.staff_request, values)

    def test_use_case_default_user(self):
        self.case.default_tester = self.default_tester
        self.case.save()

        # No assignee is passed. Case's default user should be checked
        values = {
            "run": self.test_run.pk,
            "build": self.build.pk,
            "case": self.case.pk,
            "notes": "test_create_with_all_fields",
            "sortkey": 2,
            "case_run_status": self.case_run_status.pk,
        }

        case_run = testcaserun.create(self.admin_request, values)
        self.assertEqual(self.case.default_tester.pk, case_run["assignee_id"])

    def test_use_run_default_user(self):
        self.test_run.default_tester = self.default_tester
        self.test_run.save()

        # No assignee is passed. Test run's default user should be checked
        values = {
            "run": self.test_run.pk,
            "build": self.build.pk,
            "case": self.case.pk,
            "notes": "test_create_with_all_fields",
            "sortkey": 2,
            "case_run_status": self.case_run_status.pk,
        }

        case_run = testcaserun.create(self.admin_request, values)
        self.assertEqual(self.test_run.default_tester.pk, case_run["assignee_id"])


class TestCaseRunAddComment(XmlrpcAPIBaseTest):
    """Test testcaserun.add_comment"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory(username="update_admin", email="update_admin@example.com")
        cls.admin_request = make_http_request(
            user=cls.admin, user_perm="testruns.change_testcaserun"
        )

        cls.case_run_1 = f.TestCaseRunFactory()
        cls.case_run_2 = f.TestCaseRunFactory()

    @unittest.skip("TODO: not implemented yet.")
    def test_add_comment_with_no_args(self):
        pass

    @unittest.skip("TODO: not implemented yet.")
    def test_add_comment_with_illegal_args(self):
        pass

    def test_add_comment_with_string(self):
        comment = testcaserun.add_comment(
            self.admin_request,
            f"{self.case_run_1.pk},{self.case_run_2.pk}",
            "Hello World!",
        )
        self.assertIsNone(comment)

        comment = testcaserun.add_comment(
            self.admin_request, str(self.case_run_1.pk), "Hello World!"
        )
        self.assertIsNone(comment)

    def test_add_comment_with_list(self):
        comment = testcaserun.add_comment(
            self.admin_request, [self.case_run_1.pk, self.case_run_2.pk], "Hello World!"
        )
        self.assertIsNone(comment)

    def test_add_comment_with_int(self):
        comment = testcaserun.add_comment(self.admin_request, self.case_run_2.pk, "Hello World!")
        self.assertIsNone(comment)


class TestCaseRunAttachIssue(XmlrpcAPIBaseTest):
    """Test testcaserun.attach_issue"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory(username="update_admin", email="update_admin@example.com")
        cls.staff = f.UserFactory(username="update_staff", email="update_staff@example.com")
        cls.admin_request = make_http_request(user=cls.admin, user_perm="issuetracker.add_issue")
        cls.staff_request = make_http_request(user=cls.staff)
        cls.case_run = f.TestCaseRunFactory()

        cls.tracker_product = f.IssueTrackerProductFactory(name="MyBugzilla")
        cls.tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            tracker_product=cls.tracker_product,
        )

        f.ProductIssueTrackerRelationshipFactory(
            product=cls.case_run.run.plan.product, issue_tracker=cls.tracker
        )

    def test_attach_issue_with_no_perm(self):
        self.assertXmlrpcFaultForbidden(testcaserun.attach_issue, self.staff_request, {})

    @unittest.skip("TODO: not implemented yet.")
    def test_attach_issue_with_incorrect_type_value(self):
        pass

    @unittest.skip("TODO: fix code to make this test pass.")
    def test_attach_issue_with_no_required_args(self):
        values = [
            {"summary": "This is summary.", "description": "This is description."},
            {"description": "This is description."},
            {
                "summary": "This is summary.",
            },
        ]
        for value in values:
            self.assertXmlrpcFaultBadRequest(testcaserun.attach_issue, self.admin_request, value)

    def test_attach_issue_with_required_args(self):
        bug = testcaserun.attach_issue(
            self.admin_request,
            {
                "case_run": [self.case_run.pk],
                "issue_key": "1",
                "tracker": self.tracker.pk,
            },
        )
        self.assertIsNone(bug)

        self.assertTrue(
            Issue.objects.filter(
                issue_key="1",
                case=self.case_run.case,
                case_run=self.case_run,
                tracker=self.tracker.pk,
            ).exists()
        )

    def test_attach_issue_with_all_fields(self):
        issue_summary = "This is summary."
        issue_description = "This is description."
        bug = testcaserun.attach_issue(
            self.admin_request,
            {
                "case_run": [self.case_run.pk],
                "issue_key": "2",
                "tracker": self.tracker.pk,
                "summary": issue_summary,
                "description": issue_description,
            },
        )
        self.assertIsNone(bug)

        added_issue = Issue.objects.filter(
            issue_key="2",
            case=self.case_run.case,
            case_run=self.case_run,
            tracker=self.tracker.pk,
        ).first()

        self.assertIsNotNone(added_issue)
        self.assertEqual(issue_summary, added_issue.summary)
        self.assertEqual(issue_description, added_issue.description)

    def test_succeed_to_attach_issue_by_passing_extra_data(self):
        testcaserun.attach_issue(
            self.admin_request,
            {
                "case_run": [self.case_run.pk],
                "issue_key": "1200",
                "tracker": self.tracker.pk,
                "summary": "This is summary.",
                "description": "This is description.",
                "FFFF": "aaa",
            },
        )

        self.assertTrue(
            Issue.objects.filter(
                issue_key="1200",
                case=self.case_run.case,
                case_run=self.case_run,
                tracker=self.tracker.pk,
            ).exists()
        )

    def test_attach_issue_with_non_existing_case_run(self):
        value = {
            "case_run": [111111111],
            "issue_key": "2",
            "tracker": self.tracker.pk,
        }
        self.assertXmlrpcFaultBadRequest(testcaserun.attach_issue, self.admin_request, value)

    def test_attach_issue_with_non_existing_issue_tracker(self):
        value = {
            "case_run": [self.case_run.pk],
            "issue_key": "2",
            "tracker": 111111111,
        }
        self.assertXmlrpcFaultBadRequest(testcaserun.attach_issue, self.admin_request, value)

    def test_attach_issue_with_chinese(self):
        issue_summary = "你好，中国"
        issue_description = "中国是一个具有悠久历史的文明古国"

        bug = testcaserun.attach_issue(
            self.admin_request,
            {
                "case_run": [self.case_run.pk],
                "issue_key": "12",
                "tracker": self.tracker.pk,
                "summary": issue_summary,
                "description": issue_description,
            },
        )
        self.assertIsNone(bug)

        added_issue = Issue.objects.filter(
            issue_key="12",
            case=self.case_run.case,
            case_run=self.case_run,
            tracker=self.tracker.pk,
        ).first()

        self.assertIsNotNone(added_issue)
        self.assertEqual(issue_summary, added_issue.summary)
        self.assertEqual(issue_description, added_issue.description)


class TestCaseRunAttachLog(XmlrpcAPIBaseTest):
    """Test testcaserun.attach_log"""

    @classmethod
    def setUpTestData(cls):
        cls.case_run = f.TestCaseRunFactory()

    @unittest.skip("TODO: not implemented yet.")
    def test_attach_log_with_bad_args(self):
        pass

    def test_attach_log_with_not_enough_args(self):
        self.assertXmlrpcFaultBadRequest(testcaserun.attach_log, None, "", "")
        self.assertXmlrpcFaultBadRequest(testcaserun.attach_log, None, "")
        self.assertXmlrpcFaultBadRequest(testcaserun.attach_log, None)
        self.assertXmlrpcFaultBadRequest(testcaserun.attach_log, None, "", "", "")

    def test_attach_log_with_non_exist_id(self):
        self.assertXmlrpcFaultNotFound(testcaserun.attach_log, None, 5523533, "", "")

    @unittest.skip("TODO: code should be fixed to make this test pass")
    def test_attach_log_with_invalid_url(self):
        self.assertXmlrpcFaultBadRequest(
            testcaserun.attach_log, None, self.case_run.pk, "UT test logs", "aaaaaaaaa"
        )

    def test_attach_log(self):
        url = "http://127.0.0.1/test/test-log.log"
        log = testcaserun.attach_log(None, self.case_run.pk, "UT test logs", url)
        self.assertIsNone(log)


class TestCaseRunCheckStatus(XmlrpcAPIBaseTest):
    """Test testcaserun.check_case_run_status"""

    @unittest.skip("TODO: fix code to make this test pass.")
    def test_check_status_with_no_args(self):
        bad_args = (None, [], {}, ())
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.check_case_run_status, None, arg)

    @unittest.skip("TODO: fix code to make this test pass.")
    def test_check_status_with_empty_name(self):
        self.assertXmlrpcFaultBadRequest(testcaserun.check_case_run_status, None, "")

    @unittest.skip("TODO: fix code to make this test pass.")
    def test_check_status_with_non_basestring(self):
        bad_args = (True, False, 1, 0, -1, [1], (1,), dict(a=1), 0.7)
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.check_case_run_status, None, arg)

    def test_check_status_with_name(self):
        status = testcaserun.check_case_run_status(None, "IDLE")
        self.assertIsNotNone(status)
        self.assertEqual(status["id"], 1)
        self.assertEqual(status["name"], "IDLE")

    def test_check_status_with_non_exist_name(self):
        self.assertXmlrpcFaultNotFound(testcaserun.check_case_run_status, None, "ABCDEFG")


class TestCaseRunDetachIssue(XmlrpcAPIBaseTest):
    """Test detach_issue"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory()
        cls.staff = f.UserFactory()
        cls.admin_request = make_http_request(user=cls.admin, user_perm="issuetracker.delete_issue")
        cls.staff_request = make_http_request(user=cls.staff, user_perm="issuetracker.add_issue")

        cls.case_run = f.TestCaseRunFactory()

        cls.tracker_product = f.IssueTrackerProductFactory(name="MyBZ")
        cls.bz_tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            tracker_product=cls.tracker_product,
            validate_regex=r"^\d+$",
        )
        cls.jira_tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            tracker_product=cls.tracker_product,
            validate_regex=r"^[A-Z]+-\d+$",
        )

        product = cls.case_run.run.plan.product
        f.ProductIssueTrackerRelationshipFactory(product=product, issue_tracker=cls.bz_tracker)
        f.ProductIssueTrackerRelationshipFactory(product=product, issue_tracker=cls.jira_tracker)

    def setUp(self):
        self.bz_bug = "67890"
        testcaserun.attach_issue(
            self.staff_request,
            {
                "case_run": [self.case_run.pk],
                "issue_key": self.bz_bug,
                "tracker": self.bz_tracker.pk,
                "summary": "Testing TCMS",
                "description": "Just foo and bar",
            },
        )

        self.jira_key = "AWSDF-112"
        testcaserun.attach_issue(
            self.staff_request,
            {
                "case_run": [self.case_run.pk],
                "issue_key": self.jira_key,
                "tracker": self.jira_tracker.pk,
                "summary": "Testing TCMS",
                "description": "Just foo and bar",
            },
        )

    def tearDown(self):
        self.case_run.case.issues.all().delete()

    @unittest.skip("TODO: fix get_issues_s to make this test pass.")
    def test_detach_issue_with_no_args(self):
        bad_args = (None, [], {}, ())
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(
                testcaserun.detach_issue, self.admin_request, arg, "12345"
            )
            self.assertXmlrpcFaultBadRequest(
                testcaserun.detach_issue, self.admin_request, self.case_run.pk, arg
            )

    def test_detach_issue_with_non_exist_id(self):
        original_links_count = self.case_run.case.issues.count()
        testcaserun.detach_issue(self.admin_request, 9999999, "123456")
        self.assertEqual(original_links_count, self.case_run.case.issues.count())

    @unittest.skip("Refer to #148.")
    def test_detach_issue_with_non_exist_bug(self):
        original_links_count = self.case_run.case.issues.count()
        nonexisting_bug = f"{self.bz_bug}111"
        testcaserun.detach_issue(self.admin_request, self.case_run.pk, nonexisting_bug)
        self.assertEqual(original_links_count, self.case_run.case.issues.count())

    @unittest.skip("Refer to #148.")
    def test_detach_issue(self):
        testcaserun.detach_issue(self.admin_request, self.case_run.pk, self.bz_bug)
        self.assertFalse(self.case_run.case.issues.filter(issue_key=self.bz_bug).exists())

    @unittest.skip("TODO: fix get_issues_s to make this test pass.")
    def test_detach_issue_with_illegal_args(self):
        bad_args = (
            "AAAA",
            ["A", "B", "C"],
            dict(A=1, B=2),
            True,
            False,
            (1, 2, 3, 4),
            -100,
        )
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(
                testcaserun.detach_issue, self.admin_request, arg, self.bz_bug
            )
            self.assertXmlrpcFaultBadRequest(
                testcaserun.detach_issue, self.admin_request, self.case_run.pk, arg
            )

    def test_detach_issue_with_no_perm(self):
        self.assertXmlrpcFaultForbidden(
            testcaserun.detach_issue, self.staff_request, self.case_run.pk, self.bz_bug
        )


class TestCaseRunDetachLog(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.status_idle = TestCaseRunStatus.objects.get(name="IDLE")
        cls.tester = f.UserFactory()
        cls.case_run = f.TestCaseRunFactory(
            assignee=cls.tester,
            tested_by=None,
            notes="testing ...",
            sortkey=10,
            case_run_status=cls.status_idle,
        )

    def setUp(self):
        testcaserun.attach_log(None, self.case_run.pk, "Related issue", "https://localhost/issue/1")
        self.link = self.case_run.links.all()[0]

    @unittest.skip("TODO: fix get_issues_s to make this test pass.")
    def test_detach_log_with_no_args(self):
        bad_args = (None, [], {}, ())
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.detach_log, None, arg, self.link.pk)
            self.assertXmlrpcFaultBadRequest(testcaserun.detach_log, None, self.case_run.pk, arg)

    def test_detach_log_with_not_enough_args(self):
        self.assertXmlrpcFaultBadRequest(testcaserun.detach_log, None, "")
        self.assertXmlrpcFaultBadRequest(testcaserun.detach_log, None)
        self.assertXmlrpcFaultBadRequest(testcaserun.detach_log, None, "", "", "")

    def test_detach_log_with_non_exist_id(self):
        self.assertXmlrpcFaultNotFound(testcaserun.detach_log, None, 9999999, self.link.pk)

    def test_detach_log_with_non_exist_log(self):
        testcaserun.detach_log(None, self.case_run.pk, 999999999)
        self.assertEqual(1, self.case_run.links.count())
        self.assertEqual(self.link.pk, self.case_run.links.all()[0].pk)

    @unittest.skip("TODO: fix get_issues_s to make this test pass.")
    def test_detach_log_with_invalid_type_args(self):
        bad_args = ("", "AAA", (1,), [1], dict(a=1), True, False)
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.detach_log, None, arg, self.link.pk)
            self.assertXmlrpcFaultBadRequest(testcaserun.detach_log, None, self.case_run.pk, arg)

    def test_detach_log(self):
        testcaserun.detach_log(None, self.case_run.pk, self.link.pk)
        self.assertEqual([], list(self.case_run.links.all()))


@unittest.skip("not implemented yet.")
class TestCaseRunFilter(XmlrpcAPIBaseTest):
    pass


@unittest.skip("not implemented yet.")
class TestCaseRunFilterCount(XmlrpcAPIBaseTest):
    pass


class TestCaseRunGet(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.status_idle = TestCaseRunStatus.objects.get(name="IDLE")
        cls.tester = f.UserFactory()
        cls.case_run = f.TestCaseRunFactory(
            assignee=cls.tester,
            tested_by=None,
            notes="testing ...",
            sortkey=10,
            case_run_status=cls.status_idle,
        )

    @unittest.skip("TODO: fix function get to make this test pass.")
    def test_get_with_no_args(self):
        bad_args = (None, [], {}, ())
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.get, None, arg)

    @unittest.skip("TODO: fix function get to make this test pass.")
    def test_get_with_non_integer(self):
        non_integer = (True, False, "", "aaaa", self, [1], (1,), dict(a=1), 0.7)
        for arg in non_integer:
            self.assertXmlrpcFaultBadRequest(testcaserun.get, None, arg)

    def test_get_with_non_exist_id(self):
        self.assertXmlrpcFaultNotFound(testcaserun.get, None, 11111111)

    def test_get_with_id(self):
        tcr = testcaserun.get(None, self.case_run.pk)
        self.assertIsNotNone(tcr)
        self.assertEqual(tcr["build_id"], self.case_run.build.pk)
        self.assertEqual(tcr["case_id"], self.case_run.case.pk)
        self.assertEqual(tcr["assignee_id"], self.tester.pk)
        self.assertEqual(tcr["tested_by_id"], None)
        self.assertEqual(tcr["notes"], "testing ...")
        self.assertEqual(tcr["sortkey"], 10)
        self.assertEqual(tcr["case_run_status"], "IDLE")
        self.assertEqual(tcr["case_run_status_id"], self.status_idle.pk)


class TestCaseRunGetSet(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.status_idle = TestCaseRunStatus.objects.get(name="IDLE")
        cls.tester = f.UserFactory()
        cls.case_run = f.TestCaseRunFactory(
            assignee=cls.tester,
            tested_by=None,
            notes="testing ...",
            case_run_status=cls.status_idle,
        )

    @unittest.skip("TODO: fix function get_s to make this test pass.")
    def test_get_with_no_args(self):
        bad_args = (None, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(
                testcaserun.get_s,
                None,
                arg,
                self.case_run.run.pk,
                self.case_run.build.pk,
                0,
            )
            self.assertXmlrpcFaultBadRequest(
                testcaserun.get_s,
                None,
                self.case_run.case.pk,
                arg,
                self.case_run.build.pk,
                0,
            )
            self.assertXmlrpcFaultBadRequest(
                testcaserun.get_s,
                None,
                self.case_run.case.pk,
                self.case_run.run.pk,
                arg,
                0,
            )
            self.assertXmlrpcFaultBadRequest(
                testcaserun.get_s,
                None,
                self.case_run.case.pk,
                self.case_run.run.pk,
                self.case_run.build.pk,
                arg,
            )

    def test_get_with_non_exist_run(self):
        self.assertXmlrpcFaultNotFound(
            testcaserun.get_s,
            None,
            self.case_run.case.pk,
            1111111,
            self.case_run.build.pk,
            0,
        )

    def test_get_with_non_exist_case(self):
        self.assertXmlrpcFaultNotFound(
            testcaserun.get_s,
            None,
            11111111,
            self.case_run.run.pk,
            self.case_run.build.pk,
            0,
        )

    def test_get_with_non_exist_build(self):
        self.assertXmlrpcFaultNotFound(
            testcaserun.get_s,
            None,
            self.case_run.case.pk,
            self.case_run.run.pk,
            1111111,
            0,
        )

    def test_get_with_non_exist_env(self):
        self.assertXmlrpcFaultNotFound(
            testcaserun.get_s,
            None,
            self.case_run.case.pk,
            self.case_run.run.pk,
            self.case_run.build.pk,
            999999,
        )

    def test_get_with_no_env(self):
        tcr = testcaserun.get_s(
            None, self.case_run.case.pk, self.case_run.run.pk, self.case_run.build.pk
        )
        self.assertIsNotNone(tcr)
        self.assertEqual(tcr["case_run_id"], self.case_run.pk)
        self.assertEqual(tcr["run_id"], self.case_run.run.pk)
        self.assertEqual(tcr["case_id"], self.case_run.case.pk)
        self.assertEqual(tcr["assignee_id"], self.tester.pk)
        self.assertEqual(tcr["tested_by_id"], None)
        self.assertEqual(tcr["build_id"], self.case_run.build.pk)
        self.assertEqual(tcr["notes"], "testing ...")
        self.assertEqual(tcr["case_run_status_id"], self.status_idle.pk)
        self.assertEqual(tcr["environment_id"], 0)


class TestCaseRunGetIssues(XmlrpcAPIBaseTest):
    """Test get_issues"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory()
        cls.admin_request = make_http_request(user=cls.admin, user_perm="issuetracker.add_issue")

        cls.case_run = f.TestCaseRunFactory()
        cls.bz_tracker = f.IssueTrackerFactory(name="MyBZ")
        f.ProductIssueTrackerRelationshipFactory(
            product=cls.case_run.run.plan.product,
            issue_tracker=cls.bz_tracker,
        )
        testcaserun.attach_issue(
            cls.admin_request,
            {
                "case_run": [cls.case_run.pk],
                "issue_key": "67890",
                "tracker": cls.bz_tracker.pk,
                "summary": "Testing TCMS",
                "description": "Just foo and bar",
            },
        )

    def test_get_issues_with_no_args(self):
        for bad_arg in [None, [], {}, ()]:
            self.assertXmlrpcFaultBadRequest(testcaserun.get_issues, None, bad_arg)

    @unittest.skip("TODO: fix function get_issues to make this test pass.")
    def test_get_issues_with_non_integer(self):
        non_integer = (True, False, "", "aaaa", self, [1], (1,), dict(a=1), 0.7)
        for arg in non_integer:
            self.assertXmlrpcFaultBadRequest(testcaserun.get_issues, None, arg)

    def test_get_issues_with_non_exist_id(self):
        issues = testcaserun.get_issues(None, 11111111)
        self.assertEqual(len(issues), 0)
        self.assertIsInstance(issues, list)

    def test_get_issues_with_id(self):
        issues = testcaserun.get_issues(None, self.case_run.pk)
        self.assertIsNotNone(issues)
        self.assertEqual(1, len(issues))
        self.assertEqual(issues[0]["summary"], "Testing TCMS")
        self.assertEqual(issues[0]["issue_key"], "67890")


class TestCaseRunGetIssuesSet(XmlrpcAPIBaseTest):
    """Test get_issues_s"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory(username="update_admin", email="update_admin@example.com")
        cls.admin_request = make_http_request(user=cls.admin, user_perm="issuetracker.add_issue")

        cls.case_run = f.TestCaseRunFactory()
        cls.bz_tracker = f.IssueTrackerFactory(name="MyBugzilla")
        f.ProductIssueTrackerRelationshipFactory(
            product=cls.case_run.run.plan.product,
            issue_tracker=cls.bz_tracker,
        )
        testcaserun.attach_issue(
            cls.admin_request,
            {
                "case_run": [cls.case_run.pk],
                "issue_key": "67890",
                "tracker": cls.bz_tracker.pk,
                "summary": "Testing TCMS",
                "description": "Just foo and bar",
            },
        )

    def test_get_issue_set_with_no_args(self):
        bad_args = (None, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(
                testcaserun.get_issues_s,
                None,
                arg,
                self.case_run.case.pk,
                self.case_run.build.pk,
                0,
            )
            self.assertXmlrpcFaultBadRequest(
                testcaserun.get_issues_s,
                None,
                self.case_run.run.pk,
                arg,
                self.case_run.build.pk,
                0,
            )
            self.assertXmlrpcFaultBadRequest(
                testcaserun.get_issues_s,
                None,
                self.case_run.run.pk,
                self.case_run.case.pk,
                arg,
                0,
            )

    @unittest.skip("TODO: fix get_issues_s to make this test pass.")
    def test_get_issue_set_with_invalid_environment_value(self):
        bad_args = (None, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(
                testcaserun.get_issues_s,
                None,
                self.case_run.run.pk,
                self.case_run.case.pk,
                self.case_run.build.pk,
                arg,
            )

    def test_get_issue_set_with_non_exist_run(self):
        issues = testcaserun.get_issues_s(
            None, 1111111, self.case_run.case.pk, self.case_run.build.pk, 0
        )
        self.assertIsNotNone(issues)
        self.assertIsInstance(issues, list)
        self.assertEqual(len(issues), 0)

    def test_get_issue_set_with_non_exist_case(self):
        issues = testcaserun.get_issues_s(
            None, self.case_run.run.pk, 11111111, self.case_run.build.pk, 0
        )
        self.assertIsNotNone(issues)
        self.assertIsInstance(issues, list)
        self.assertEqual(len(issues), 0)

    def test_get_issue_set_with_non_exist_build(self):
        issues = testcaserun.get_issues_s(
            None, self.case_run.run.pk, self.case_run.case.pk, 1111111, 0
        )
        self.assertIsNotNone(issues)
        self.assertIsInstance(issues, list)
        self.assertEqual(len(issues), 0)

    def test_get_issue_set_with_non_exist_env(self):
        issues = testcaserun.get_issues_s(
            None,
            self.case_run.run.pk,
            self.case_run.case.pk,
            self.case_run.build.pk,
            999999,
        )
        self.assertIsNotNone(issues)
        self.assertIsInstance(issues, list)
        self.assertEqual(len(issues), 0)

    def test_get_issue_set_by_omitting_argument_environment(self):
        issues = testcaserun.get_issues_s(
            None, self.case_run.run.pk, self.case_run.case.pk, self.case_run.build.pk
        )
        self.assertIsNotNone(issues)
        self.assertIsInstance(issues, list)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue_key"], "67890")
        self.assertEqual(issues[0]["summary"], "Testing TCMS")


class TestCaseRunGetStatus(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.status_running = TestCaseRunStatus.objects.get(name="RUNNING")

    def test_get_all_status(self):
        rows = testcaserun.get_case_run_status(None)
        self.assertEqual(8, len(rows))
        names = [row["name"] for row in rows]
        self.assertTrue("IDLE" in names)
        self.assertTrue("PASSED" in names)
        self.assertTrue("FAILED" in names)
        self.assertTrue("RUNNING" in names)
        self.assertTrue("PAUSED" in names)
        self.assertTrue("BLOCKED" in names)
        self.assertTrue("ERROR" in names)
        self.assertTrue("WAIVED" in names)

        rows = testcaserun.get_case_run_status(None, None)
        self.assertEqual(8, len(rows))
        names = [row["name"] for row in rows]
        self.assertTrue("IDLE" in names)
        self.assertTrue("PASSED" in names)
        self.assertTrue("FAILED" in names)
        self.assertTrue("RUNNING" in names)
        self.assertTrue("PAUSED" in names)
        self.assertTrue("BLOCKED" in names)
        self.assertTrue("ERROR" in names)
        self.assertTrue("WAIVED" in names)

    @unittest.skip("TODO: fix method to make this test pass.")
    def test_get_status_with_no_args(self):
        bad_args = ([], {}, (), "", "AAAA", self)
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.get_case_run_status, None, arg)

    def test_get_status_with_non_exist_id(self):
        self.assertXmlrpcFaultNotFound(testcaserun.get_case_run_status, None, 999999)

    def test_get_status_with_id(self):
        status = testcaserun.get_case_run_status(None, self.status_running.pk)
        self.assertIsNotNone(status)
        self.assertEqual(status["id"], self.status_running.pk)
        self.assertEqual(status["name"], "RUNNING")

    def test_get_status_with_name(self):
        self.assertXmlrpcFaultBadRequest(testcaserun.get_case_run_status, None, "PROPOSED")


@unittest.skip("not implemented yet.")
class TestCaseRunGetCompletionTime(XmlrpcAPIBaseTest):
    pass


@unittest.skip("not implemented yet.")
class TestCaseRunGetCompletionTimeSet(XmlrpcAPIBaseTest):
    pass


@unittest.skip("not implemented yet.")
class TestCaseRunGetHistory(XmlrpcAPIBaseTest):
    def test_get_history(self):
        self.assertXmlrpcFaultNotImplemented(testcaserun.get_history, None, None)


@unittest.skip("not implemented yet.")
class TestCaseRunGetHistorySet(XmlrpcAPIBaseTest):
    def test_get_history(self):
        self.assertXmlrpcFaultNotImplemented(testcaserun.get_history_s, None, None, None, None)


class TestCaseRunGetLogs(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.case_run_1 = f.TestCaseRunFactory()
        cls.case_run_2 = f.TestCaseRunFactory()
        testcaserun.attach_log(None, cls.case_run_1.pk, "Test logs", "http://www.google.com")

    @unittest.skip("TODO: fix method to make this test pass.")
    def test_get_logs_with_no_args(self):
        bad_args = (None, [], (), {}, "")
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.get_logs, None, arg)

    @unittest.skip("TODO: fix method to make this test pass.")
    def test_get_logs_with_non_integer(self):
        bad_args = (True, False, "AAA", 0.7, -1)
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.get_logs, None, arg)

    def test_get_logs_with_non_exist_id(self):
        self.assertXmlrpcFaultNotFound(testcaserun.get_logs, None, 99999999)

    def test_get_empty_logs(self):
        logs = testcaserun.get_logs(None, self.case_run_2.pk)
        self.assertIsInstance(logs, list)
        self.assertEqual(len(logs), 0)

    def test_get_logs(self):
        tcr_log = LinkReference.get_from(self.case_run_1)[0]
        logs = testcaserun.get_logs(None, self.case_run_1.pk)
        self.assertIsInstance(logs, list)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["id"], tcr_log.pk)
        self.assertEqual(logs[0]["name"], "Test logs")
        self.assertEqual(logs[0]["url"], "http://www.google.com")


class TestCaseRunUpdate(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory()
        cls.staff = f.UserFactory()
        cls.user = f.UserFactory()
        cls.admin_request = make_http_request(
            user=cls.admin, user_perm="testruns.change_testcaserun"
        )
        cls.staff_request = make_http_request(user=cls.staff)

        cls.build = f.TestBuildFactory()
        cls.case_run_1 = f.TestCaseRunFactory()
        cls.case_run_2 = f.TestCaseRunFactory()
        cls.status_running = TestCaseRunStatus.objects.get(name="RUNNING")

    @unittest.skip("TODO: fix method to make this test pass.")
    def test_update_with_no_args(self):
        bad_args = (None, [], (), {}, "")
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(testcaserun.update, self.admin_request, arg, {})
            self.assertXmlrpcFaultBadRequest(
                testcaserun.update, self.admin_request, self.case_run_1.pk, arg
            )

    def test_update_with_single_caserun(self):
        tcr = testcaserun.update(
            self.admin_request,
            self.case_run_1.pk,
            {
                "build": self.build.pk,
                "assignee": self.user.pk,
                "case_run_status": self.status_running.pk,
                "notes": "AAAAAAAA",
                "sortkey": 90,
            },
        )
        self.assertIsNotNone(tcr)
        self.assertIsInstance(tcr, list)
        self.assertEqual(1, len(tcr))
        self.assertEqual(tcr[0]["build"], encode(self.build.name))
        self.assertEqual(tcr[0]["assignee"], self.user.username)
        self.assertEqual(tcr[0]["case_run_status"], encode("RUNNING"))
        self.assertEqual(tcr[0]["notes"], "AAAAAAAA")
        self.assertEqual(tcr[0]["sortkey"], 90)

    def test_update_with_multi_caserun(self):
        tcr = testcaserun.update(
            self.admin_request,
            [self.case_run_1.pk, self.case_run_2.pk],
            {
                "build": self.build.pk,
                "assignee": self.user.pk,
                "case_run_status": self.status_running.pk,
                "notes": "Hello World!",
                "sortkey": 180,
            },
        )
        self.assertIsNotNone(tcr)
        self.assertIsInstance(tcr, list)
        self.assertEqual(len(tcr), 2)
        self.assertEqual(tcr[0]["build"], tcr[1]["build"])
        self.assertEqual(tcr[0]["assignee"], tcr[1]["assignee"])
        self.assertEqual(tcr[0]["case_run_status"], tcr[1]["case_run_status"])
        self.assertEqual(tcr[0]["notes"], tcr[1]["notes"])
        self.assertEqual(tcr[0]["sortkey"], tcr[1]["sortkey"])

    def test_update_with_non_exist_build(self):
        self.assertXmlrpcFaultBadRequest(
            testcaserun.update,
            self.admin_request,
            self.case_run_1.pk,
            {"build": 1111111},
        )

    def test_update_with_non_exist_assignee(self):
        self.assertXmlrpcFaultBadRequest(
            testcaserun.update,
            self.admin_request,
            self.case_run_1.pk,
            {"assignee": 1111111},
        )

    def test_update_with_non_exist_status(self):
        self.assertXmlrpcFaultBadRequest(
            testcaserun.update,
            self.admin_request,
            self.case_run_1.pk,
            {"case_run_status": 1111},
        )

    def test_update_by_ignoring_undoced_fields(self):
        case_run = testcaserun.update(
            self.admin_request,
            self.case_run_1.pk,
            {
                "notes": "AAAA",
                "close_date": datetime.now(),
                "anotherone": "abc",
            },
        )
        self.assertEqual("AAAA", case_run[0]["notes"])

    def test_update_with_no_perm(self):
        self.assertXmlrpcFaultForbidden(
            testcaserun.update,
            self.staff_request,
            self.case_run_1.pk,
            {"notes": "AAAA"},
        )

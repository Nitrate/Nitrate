# -*- coding: utf-8 -*-

import operator

from django import test

from tcms.integration.issuetracker.factories import IssueTrackerFactory
from tcms.tests.factories import ProductFactory
from tcms.tests.factories import TestBuildFactory
from tcms.tests.factories import TestCaseFactory
from tcms.tests.factories import TestCaseRunFactory
from tcms.tests.factories import TestPlanFactory
from tcms.tests.factories import TestRunFactory
from tcms.tests.factories import TestTagFactory
from tcms.tests.factories import UserFactory
from tcms.tests.factories import VersionFactory
from tcms.xmlrpc.api import testrun as testrun_api
from tcms.xmlrpc.serializer import datetime_to_str
from tcms.xmlrpc.tests.utils import make_http_request
from tcms.xmlrpc.tests.utils import XmlrpcAPIBaseTest


class TestGet(test.TestCase):
    """Test TestRun.get"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.http_req = make_http_request(user=cls.user)

        cls.product = ProductFactory()
        cls.version = VersionFactory(product=cls.product)
        cls.build = TestBuildFactory(product=cls.product)
        cls.plan = TestPlanFactory(
            product=cls.product,
            product_version=cls.version,
        )
        cls.plan_manager = UserFactory()
        cls.plan_default_tester = UserFactory()
        cls.tag_fedora = TestTagFactory(name='fedora')
        cls.tag_python = TestTagFactory(name='automation')
        cls.test_run = TestRunFactory(
            plan_text_version=1,
            notes='Running tests ...',
            product_version=cls.version,
            build=cls.build,
            plan=cls.plan,
            manager=cls.plan_manager,
            default_tester=cls.plan_default_tester,
            tag=[cls.tag_fedora, cls.tag_python]
        )

    def test_get(self):
        expected_run = {
            'run_id': self.test_run.pk,
            'errata_id': None,
            'summary': self.test_run.summary,
            'plan_text_version': 1,
            'start_date': datetime_to_str(self.test_run.start_date),
            'stop_date': None,
            'notes': self.test_run.notes,
            'estimated_time': '00:00:00',
            'environment_id': 0,

            'plan_id': self.plan.pk,
            'plan': self.plan.name,
            'build_id': self.build.pk,
            'build': self.build.name,
            'manager_id': self.plan_manager.pk,
            'manager': self.plan_manager.username,
            'product_version_id': self.version.pk,
            'product_version': self.version.value,
            'default_tester_id': self.plan_default_tester.pk,
            'default_tester': self.plan_default_tester.username,
            'env_value': [],
            'tag': ['automation', 'fedora'],
            'cc': [],
            'auto_update_run_status': False,
        }

        run = testrun_api.get(self.http_req, self.test_run.pk)
        run['tag'].sort()
        self.assertEqual(expected_run, run)


class TestGetIssues(XmlrpcAPIBaseTest):
    """Test get_issues"""

    @classmethod
    def setUpTestData(cls):
        super(TestGetIssues, cls).setUpTestData()

        cls.run_1 = TestRunFactory()
        cls.case_1 = TestCaseFactory(plan=[cls.run_1.plan])
        cls.case_2 = TestCaseFactory(plan=[cls.run_1.plan])
        cls.case_run_1 = TestCaseRunFactory(case=cls.case_1, run=cls.run_1)
        cls.case_run_2 = TestCaseRunFactory(case=cls.case_2, run=cls.run_1)

        cls.run_2 = TestRunFactory()
        cls.case_3 = TestCaseFactory(plan=[cls.run_2.plan])
        cls.case_4 = TestCaseFactory(plan=[cls.run_2.plan])
        cls.case_run_3 = TestCaseRunFactory(case=cls.case_3, run=cls.run_2)
        cls.case_run_4 = TestCaseRunFactory(case=cls.case_4, run=cls.run_2)

        cls.tracker = IssueTrackerFactory(
            name='coolbz',
            service_url='http://localhost/',
            issue_report_endpoint='/enter_bug.cgi',
            validate_regex=r'^\d+$')

        cls.case_run_1.add_issue('1', cls.tracker)
        cls.case_run_1.add_issue('2', cls.tracker)
        cls.case_run_2.add_issue('3', cls.tracker)
        cls.case_run_3.add_issue('4', cls.tracker)
        cls.case_run_4.add_issue('5', cls.tracker)
        cls.case_run_4.add_issue('6', cls.tracker)

    def test_get_issues(self):
        test_data = (
            (self.run_1.pk, ('1', '2', '3')),
            ([self.run_1.pk, self.run_2.pk], ('1', '2', '3', '4', '5', '6')),
            ('{}, {}'.format(self.run_1.pk, self.run_2.pk),
             ('1', '2', '3', '4', '5', '6')),
        )

        for run_ids, expected_issue_keys in test_data:
            issues = testrun_api.get_issues(self.request, run_ids)
            issue_keys = tuple(
                item['issue_key'] for item in
                sorted(issues, key=operator.itemgetter('issue_key'))
            )
            self.assertEqual(expected_issue_keys, issue_keys)

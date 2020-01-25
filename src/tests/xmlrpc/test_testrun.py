# -*- coding: utf-8 -*-

import operator

from django import test

from tcms.xmlrpc.api import testrun as testrun_api
from tcms.xmlrpc.serializer import datetime_to_str
from tests import factories as f
from tests.xmlrpc.utils import make_http_request
from tests.xmlrpc.utils import XmlrpcAPIBaseTest


class TestGet(test.TestCase):
    """Test TestRun.get"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory()
        cls.http_req = make_http_request(user=cls.user)

        cls.product = f.ProductFactory()
        cls.version = f.VersionFactory(product=cls.product)
        cls.build = f.TestBuildFactory(product=cls.product)
        cls.plan = f.TestPlanFactory(
            product=cls.product,
            product_version=cls.version,
        )
        cls.plan_manager = f.UserFactory()
        cls.plan_default_tester = f.UserFactory()
        cls.tag_fedora = f.TestTagFactory(name='fedora')
        cls.tag_python = f.TestTagFactory(name='automation')
        cls.test_run = f.TestRunFactory(
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
        super().setUpTestData()

        cls.run_1 = f.TestRunFactory()
        cls.case_1 = f.TestCaseFactory(plan=[cls.run_1.plan])
        cls.case_2 = f.TestCaseFactory(plan=[cls.run_1.plan])
        cls.case_run_1 = f.TestCaseRunFactory(case=cls.case_1, run=cls.run_1)
        cls.case_run_2 = f.TestCaseRunFactory(case=cls.case_2, run=cls.run_1)

        cls.run_2 = f.TestRunFactory()
        cls.case_3 = f.TestCaseFactory(plan=[cls.run_2.plan])
        cls.case_4 = f.TestCaseFactory(plan=[cls.run_2.plan])
        cls.case_run_3 = f.TestCaseRunFactory(case=cls.case_3, run=cls.run_2)
        cls.case_run_4 = f.TestCaseRunFactory(case=cls.case_4, run=cls.run_2)

        cls.tracker = f.IssueTrackerFactory(
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
            (f'{self.run_1.pk}, {self.run_2.pk}',
             ('1', '2', '3', '4', '5', '6')),
        )

        for run_ids, expected_issue_keys in test_data:
            issues = testrun_api.get_issues(self.request, run_ids)
            issue_keys = tuple(
                item['issue_key'] for item in
                sorted(issues, key=operator.itemgetter('issue_key'))
            )
            self.assertEqual(expected_issue_keys, issue_keys)

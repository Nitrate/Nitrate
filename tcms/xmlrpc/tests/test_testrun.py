# -*- coding: utf-8 -*-

from django import test

from tcms.tests.factories import ProductFactory
from tcms.tests.factories import TestBuildFactory
from tcms.tests.factories import TestPlanFactory
from tcms.tests.factories import TestRunFactory
from tcms.tests.factories import TestTagFactory
from tcms.tests.factories import UserFactory
from tcms.tests.factories import VersionFactory
from tcms.xmlrpc.api import testrun as testrun_api
from tcms.xmlrpc.serializer import datetime_to_str
from tcms.xmlrpc.tests.utils import make_http_request


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
        expected_run = dict(
            run_id=self.test_run.pk,
            errata_id=None,
            summary=self.test_run.summary,
            plan_text_version=1,
            start_date=datetime_to_str(self.test_run.start_date),
            stop_date=None,
            notes=self.test_run.notes,
            estimated_time='00:00:00',
            environment_id=0,

            plan_id=self.plan.pk,
            plan=self.plan.name,
            build_id=self.build.pk,
            build=self.build.name,
            manager_id=self.plan_manager.pk,
            manager=self.plan_manager.username,
            product_version_id=self.version.pk,
            product_version=self.version.value,
            default_tester_id=self.plan_default_tester.pk,
            default_tester=self.plan_default_tester.username,
            env_value=[],
            tag=['automation', 'fedora'],
            cc=[],
            auto_update_run_status=False,
        )

        run = testrun_api.get(self.http_req, self.test_run.pk)
        run['tag'].sort()
        self.assertEqual(expected_run, run)

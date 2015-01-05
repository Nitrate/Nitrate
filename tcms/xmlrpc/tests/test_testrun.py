# -*- coding: utf-8 -*-
from xmlrpclib import Fault

from django.contrib.auth.models import User
from django_nose import FastFixtureTestCase

from tcms.xmlrpc.api import testrun
from tcms.xmlrpc.tests.utils import make_http_request
from tcms.testruns.models import TestCaseRun, TestRun, TestRunTag, \
    TCMSEnvRunValueMap


class AssertMessage(object):
    NOT_VALIDATE_ARGS = "Missing validations for args."
    NOT_VALIDATE_REQUIRED_ARGS = "Missing validations for required args."
    NOT_VALIDATE_ILLEGAL_ARGS = "Missing validations for illegal args."
    NOT_VALIDATE_FOREIGN_KEY = "Missing validations for foreign key."
    NOT_VALIDATE_LENGTH = "Missing validations for length of value."
    NOT_VALIDATE_URL_FORMAT = "Missing validations for URL format."

    SHOULD_BE_400 = "Error code should be 400."
    SHOULD_BE_409 = "Error code should be 409."
    SHOULD_BE_500 = "Error code should be 500."
    SHOULD_BE_403 = "Error code should be 403."
    SHOULD_BE_401 = "Error code should be 401."
    SHOULD_BE_404 = "Error code should be 404."
    SHOULD_BE_501 = "Error code should be 501."
    SHOULD_BE_1 = "Error code should be 1."

    UNEXCEPT_ERROR = "Unexcept error occurs."
    NEED_ENCODE_UTF8 = "Need to encode with utf8."

    NOT_IMPLEMENT_FUNC = "Not implement yet."
    XMLRPC_INTERNAL_ERROR = "xmlrpc library error."
    NOT_VALIDATE_PERMS = "Missing validations for user perms."


class TestAddCases(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestAddCases, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.add_testcaserun'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestAddCases, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_add_cases(self):
        try:
            ret = testrun.add_cases(self.admin_request, 2, 10)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(ret)
            tcr = TestCaseRun.objects.get(run_id=2, case_id=10)
            self.assertIsNotNone(tcr)

    def test_add_cases_no_perms(self):
        try:
            testrun.add_cases(self.staff_request, None, None)
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_PERMS)

    def test_add_multi_cases(self):
        try:
            ret = testrun.add_cases(self.admin_request, 2, [6, 7, 8])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(ret)
            tcr = TestCaseRun.objects.filter(run_id=2, case_id__in=[6, 7, 8])
            self.assertEqual(len(tcr), 3)

    def test_add_cases_string(self):
        try:
            ret = testrun.add_cases(self.admin_request, 2, ['6', '7', '8'])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(ret)
            tcr = TestCaseRun.objects.filter(run_id=2, case_id__in=[6, 7, 8])
            self.assertEqual(len(tcr), 3)


class TestAddTag(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestAddTag, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.add_testruntag'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestAddTag, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_add_tag(self):
        try:
            ret = testrun.add_tag(self.admin_request, 2, 'QWER')
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(ret)
            trt = TestRunTag.objects.get(run_id=2, tag__name='QWER')
            self.assertIsNotNone(trt)

    def test_add_tag_no_perms(self):
        try:
            testrun.add_tag(self.staff_request, None, None)
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_PERMS)

    def test_add_multi_tags(self):
        try:
            ret = testrun.add_tag(self.admin_request, 2, ['ASDF', 'ZXCV',
                                                          'P'])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(ret)
            tcr = TestRunTag.objects.filter(run_id=2,
                                            tag__name__in=['ASDF', 'ZXCV',
                                                           'P'])
            self.assertEqual(len(tcr), 3)

    def test_add_tag_string(self):
        try:
            ret = testrun.add_tag(self.admin_request, 2, ['ASDF', 'ZXCV',
                                                          'P'])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(ret)
            tcr = TestRunTag.objects.filter(run_id=2,
                                            tag__name__in=['ASDF', 'ZXCV',
                                                           'P'])
            self.assertEqual(len(tcr), 3)


class TestCreate(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestCreate, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.add_testrun'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestCreate, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_create(self):
        try:
            tr = testrun.create(self.admin_request, {
                'plan': 1,
                'build': 14,
                'manager': 1,
                'summary': 'Unittest plan',
                'product': 4,
                'product_version': 35,
                'estimated_time': '2h30m30s',
                'case': [1, 2],
                'tag': [1, 2]
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(tr['summary'], 'Unittest plan')

    def test_create_without_required_fields(self):
        try:
            testrun.create(self.admin_request, {
                'plan': 1,
                'build': 14,
                'manager': 1,
                'summary': 'Unittest plan',
                'product_version': 35,
                'estimated_time': '2h30m30s',
                'case': [1, 2],
                'tag': [1, 2]
            })
        except Fault as f:
            self.assertEqual(f.faultCode, 400, AssertMessage.SHOULD_BE_400)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_REQUIRED_ARGS)

        try:
            testrun.create(self.admin_request, {})
        except Fault as f:
            self.assertEqual(f.faultCode, 400, AssertMessage.SHOULD_BE_400)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_REQUIRED_ARGS)

    def test_create_with_invalid_values(self):
        try:
            testrun.create(self.admin_request, {
                'plan': 1,
                'build': 14,
                'manager': 1,
                'summary': 'Unittest plan',
                'product': 94,
                'product_version': 35,
                'estimated_time': '2h30m30s',
                'case': [1, 2],
                'tag': [1, 2]
            })
        except Fault as f:
            self.assertEqual(f.faultCode, 400, AssertMessage.SHOULD_BE_400)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)


class TestEnvValue(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestEnvValue, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.change_tcmsenvrunvaluemap'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestEnvValue, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_add_env_value(self):
        try:
            ret = testrun.env_value(self.admin_request, 'add', 2, [1, 2, 3])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(ret)
            values = TCMSEnvRunValueMap.objects.filter(run_id=2, value_id__in=[
                1, 2, 3])
            self.assertEqual(len(values), 3)

    def test_remove_env_value(self):
        try:
            ret = testrun.env_value(self.admin_request, 'remove', 2, [1, 2, 3])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(ret)
            values = TCMSEnvRunValueMap.objects.filter(run_id=2, value_id__in=[
                1, 2, 3])
            self.assertEqual(len(values), 0)

    def test_invalid_env_value_action(self):
        try:
            testrun.env_value(self.admin_request, 'unknown', 2, [1, 2, 3])
        except Fault as f:
            self.assertEqual(f.faultCode, 400, AssertMessage.SHOULD_BE_400)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_with_no_perms(self):
        try:
            testrun.env_value(self.staff_request, 'remove', 2, [1, 2, 3])
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_env_not_exist(self):
        try:
            testrun.env_value(self.staff_request, 'add', 2, 999)
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_run_not_exist(self):
        try:
            testrun.env_value(self.staff_request, 'add', 999, [1, 2, 3])
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)


class TestFilter(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_filter(self):
        try:
            tr = testrun.filter(None, {
                'build': 6,
                'run_id': 1,
                'plan': 1
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(tr), 1)
            self.assertEqual(tr[0]['build_id'], 6)
            self.assertEqual(tr[0]['run_id'], 1)
            self.assertEqual(tr[0]['plan_id'], 1)

    def test_filter_with_no_args(self):
        try:
            tr = testrun.filter(None, {})
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(tr), 2)


class TestFilterCount(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_filter_count(self):
        try:
            count = testrun.filter_count(None, {
                'build': 6,
                'run_id': 1,
                'plan': 1
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(count, 1)


class TestGet(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_get(self):
        try:
            tr = testrun.get(None, 1)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(tr['build_id'], 6)
            self.assertEqual(tr['product_version_id'], 6)
            self.assertEqual(tr['plan_id'], 1)

    def test_get_non_exist_testrun(self):
        try:
            testrun.get(None, 999)
        except Fault as f:
            self.assertEqual(f.faultCode, 404, AssertMessage.SHOULD_BE_404)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)


class TestGetBugs(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestGetBugs, self).setUp()

        from tcms.testruns.models import TestCaseBug

        bug_1 = TestCaseBug.objects.get(bug_id=11111)
        bug_1.case_run_id = 1
        bug_1.save()

        bug_2 = TestCaseBug.objects.get(bug_id=22222)
        bug_2.case_run_id = 1
        bug_2.save()

        self.bug_1, self.bug_2 = bug_1, bug_2

    def tearDown(self):
        super(TestGetBugs, self).tearDown()

        bug_1, bug_2 = self.bug_1, self.bug_2
        bug_1.case_run_id = None
        bug_1.save()

        bug_2.case_run_id = None
        bug_2.save()

    def test_get_bugs(self):
        try:
            bugs = testrun.get_bugs(None, 1)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(bugs), 2)
            self.assertEqual(bugs[0]['bug_id'], '11111')
            self.assertEqual(bugs[1]['bug_id'], '22222')

    def test_get_bugs_with_non_exist(self):
        try:
            bugs = testrun.get_bugs(None, 999)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(bugs), 0)


class TestChangeHistory(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_get_change_history(self):
        try:
            testrun.get_change_history(None, 1)
        except Fault as f:
            self.assertEqual(f.faultCode, 501, AssertMessage.SHOULD_BE_501)
        else:
            self.fail(AssertMessage.NOT_IMPLEMENT_FUNC)


class TestCompletionReport(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def get_get_completion_report(self):
        try:
            testrun.get_completion_report(None, 1)
        except Fault as f:
            self.assertEqual(f.faultCode, 501, AssertMessage.SHOULD_BE_501)
        else:
            self.fail(AssertMessage.NOT_IMPLEMENT_FUNC)


class TestEnvValues(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_get_env_values(self):
        try:
            values = testrun.get_env_values(None, 1)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(values), 3)
            self.assertEqual(values[0]['property'], 'disk')
            self.assertEqual(values[0]['value'], '120G')
            self.assertEqual(values[1]['property'], 'video')
            self.assertEqual(values[1]['value'], 'ATI')
            self.assertEqual(values[2]['property'], 'cpu')
            self.assertEqual(values[2]['value'], 'i3')

    def test_get_env_values_with_non_exist(self):
        try:
            values = testrun.get_env_values(None, 9999)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(values), 0)


class TestLinkEnvValues(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestLinkEnvValues, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.add_tcmsenvrunvaluemap'
        )
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.change_tcmsenvrunvaluemap'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestLinkEnvValues, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_link_env_values(self):
        try:
            testrun.link_env_value(self.admin_request, 1, 4)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            values = TCMSEnvRunValueMap.objects.filter(run_id=1, value_id=4)
            self.assertTrue(values.exists())
            self.assertEqual(values.count(), 1)

    def test_link_env_values_with_no_perms(self):
        try:
            testrun.link_env_value(self.staff_request, 1, 4)
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_PERMS)

    def test_link_env_values_with_array(self):
        try:
            testrun.link_env_value(self.admin_request, 1, [4, 5, 6])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            values = TCMSEnvRunValueMap.objects.filter(run_id=1,
                                                       value_id__in=[4, 5, 6])
            self.assertTrue(values.exists())
            self.assertEqual(values.count(), 3)


class TestUnlinkEnvValues(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestUnlinkEnvValues, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        make_http_request(
            user=self.admin,
            user_perm='testruns.delete_tcmsenvrunvaluemap'
        )
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.change_tcmsenvrunvaluemap'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestUnlinkEnvValues, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_link_env_values(self):
        try:
            testrun.unlink_env_value(self.admin_request, 1, 15)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            values = TCMSEnvRunValueMap.objects.filter(run_id=1, value_id=15)
            self.assertFalse(values.exists())
            self.assertEqual(values.count(), 0)

    def test_link_env_values_with_no_perms(self):
        try:
            testrun.unlink_env_value(self.staff_request, 1, 4)
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_PERMS)

    def test_link_env_values_with_array(self):
        try:
            testrun.unlink_env_value(self.admin_request, 1, [1, 19])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            values = TCMSEnvRunValueMap.objects.filter(run_id=1,
                                                       value_id__in=[1, 19])
            self.assertFalse(values.exists())
            self.assertEqual(values.count(), 0)


class TestRemoveCases(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestRemoveCases, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.delete_testcaserun'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestRemoveCases, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_remove_case(self):
        try:
            testrun.remove_cases(self.admin_request, 1, 9)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            case = TestCaseRun.objects.filter(run_id=1, case_id=9)
            self.assertFalse(case.exists())

    def test_remove_case_with_no_perms(self):
        try:
            testrun.remove_cases(self.staff_request, 1, 9)
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_PERMS)

    def test_remove_case_with_array(self):
        try:
            testrun.remove_cases(self.admin_request, [1, 2], [4, 5])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            case = TestCaseRun.objects.filter(run_id__in=[1, 2],
                                              case_id__in=[4, 5])
            self.assertFalse(case.exists())


class TestGetTags(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_get_tags(self):
        try:
            tags = testrun.get_tags(None, 1)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(tags), 4)
            self.assertEqual(tags[0]['name'], 'R1')
            self.assertEqual(tags[0]['id'], 11)

            self.assertEqual(tags[1]['name'], 'R2')
            self.assertEqual(tags[1]['id'], 12)

            self.assertEqual(tags[2]['name'], 'R3')
            self.assertEqual(tags[2]['id'], 13)

            self.assertEqual(tags[3]['name'], 'R4')
            self.assertEqual(tags[3]['id'], 14)

    def test_get_tags_with_non_exist(self):
        try:
            testrun.get_tags(None, 9999)
        except Fault as f:
            self.assertEqual(f.faultCode, 404, AssertMessage.SHOULD_BE_404)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)


class TestGetTestCaseRuns(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_get_test_case_runs(self):
        try:
            caseruns = testrun.get_test_case_runs(None, 1)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(caseruns), 16)

    def test_get_test_case_runs_with_non_exist(self):
        try:
            caseruns = testrun.get_test_case_runs(None, 999)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(caseruns), 0)


class TestGetCases(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_get_test_cases(self):
        try:
            caseruns = testrun.get_test_cases(None, 1)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(caseruns), 16)

    def test_get_test_cases_with_non_exist(self):
        try:
            caseruns = testrun.get_test_cases(None, 999)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(caseruns), 0)


class TestGetPlan(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_get_plan(self):
        try:
            plan = testrun.get_test_plan(None, 1)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(plan['name'], 'StarCraft: Init')

    def test_get_plan_with_non_exist(self):
        try:
            testrun.get_test_plan(None, 9999)
        except Fault as f:
            self.assertEqual(f.faultCode, 404, AssertMessage.SHOULD_BE_404)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)


class TestRemoveTag(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestRemoveTag, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.delete_testruntag'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestRemoveTag, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_remove_tags(self):
        try:
            testrun.remove_tag(self.admin_request, 1, 'R1')
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            tags = TestRunTag.objects.filter(tag_id=11, run_id=1)
            self.assertFalse(tags.exists())

    def test_remove_tags_with_no_perms(self):
        try:
            testrun.remove_tag(self.staff_request, 1, 'R1')
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_PERMS)

    def test_remove_tags_with_non_exist(self):
        try:
            testrun.remove_tag(self.admin_request, 1, 'R11')
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            tags = TestRunTag.objects.filter(run_id=1)
            self.assertTrue(tags.exists())
            self.assertEqual(tags.count(), 4)

    def test_remove_tags_with_array(self):
        try:
            testrun.remove_tag(self.admin_request, 1, ['R1', 'R2', 'R3', 'R4'])
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            tags = TestRunTag.objects.filter(run_id=1)
            self.assertFalse(tags.exists())


class TestUpdate(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestUpdate, self).setUp()

        self.admin = User(username='tcr_admin',
                          email='tcr_admin@example.com')
        self.staff = User(username='tcr_staff',
                          email='tcr_staff@example.com')
        self.admin.save()
        self.staff.save()
        self.admin_request = make_http_request(
            user=self.admin,
            user_perm='testruns.change_testrun'
        )
        self.staff_request = make_http_request(
            user=self.staff
        )

    def tearDown(self):
        super(TestUpdate, self).tearDown()

        self.admin.delete()
        self.staff.delete()

    def test_update(self):
        try:
            tr = testrun.update(self.admin_request, 1, {
                'plan': 2,
                'build': 2,
                'errata_id': 1,
                'manager': self.admin.pk,
                'default_tester': self.staff.pk,
                'summary': 'test update',
                'estimated_time': '2h30m30s',
                'product_version': 11,
                'product': 2,
                'plan_text_version': 13,
                'status': 1,
                'notes': 'only test.'
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(tr[0]['plan_id'], 2)
            self.assertEqual(tr[0]['build_id'], 2)
            self.assertEqual(tr[0]['errata_id'], 1)
            self.assertEqual(tr[0]['manager'], 'tcr_admin')
            self.assertEqual(tr[0]['default_tester'], 'tcr_staff')
            self.assertEqual(tr[0]['summary'], 'test update')
            self.assertEqual(tr[0]['estimated_time'], '02:30:30')
            self.assertEqual(tr[0]['product_version_id'], 11)
            self.assertEqual(tr[0]['plan_text_version'], 13)

    def test_update_with_no_perms(self):
        try:
            testrun.update(self.staff_request, 1, {
                'plan': 2,
                'build': 1,
                'errata_id': 1,
                'manager': self.admin.pk,
                'default_tester': self.staff.pk,
                'summary': 'test update',
                'estimated_time': '2h30m30s',
                'product_version': 11,
                'product': 2,
                'plan_text_version': 13,
                'status': 1,
            })
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_PERMS)

    def test_update_with_non_exist(self):
        try:
            testrun.update(self.admin_request, 1, {
                'build': 999
            })
        except Fault as f:
            self.assertEqual(f.faultCode, 400, AssertMessage.SHOULD_BE_400)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_update_with_no_product_version(self):
        try:
            testrun.update(self.admin_request, 1, {
                'product_version': 11
            })
        except Fault as f:
            self.assertEqual(f.faultCode, 400, AssertMessage.SHOULD_BE_400)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_update_with_delete_some_fields(self):
        try:
            tr = testrun.update(self.admin_request, 1, {
                'notes': ''
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(tr[0]['notes'], '')

        try:
            testrun.update(self.admin_request, 1, {
                'default_tester': ''
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(tr[0]['default_tester'], None)

        try:
            testrun.update(self.admin_request, 1, {
                'status': 0
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(tr[0]['stop_date'], None)
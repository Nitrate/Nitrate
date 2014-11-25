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

    pass


class TestLinkEnvValues(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass


class TestUnlinkEnvValues(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass


class TestRemoveCases(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass


class TestGetTags(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass


class TestGetTestCaseRuns(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass


class TestGetCases(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass


class TestGetPlan(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass


class TestRemoveTag(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass


class TestUpdate(FastFixtureTestCase):
    fixtures = ['unittest.json']

    pass

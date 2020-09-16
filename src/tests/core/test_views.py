# -*- coding: utf-8 -*-

import json
from http import HTTPStatus

from django import test
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.urls import reverse
from django_comments.models import Comment

from tcms.logs.models import TCMSLogModel
from tcms.management.models import Priority
from tcms.management.models import TCMSEnvGroup
from tcms.management.models import TCMSEnvProperty
from tcms.testcases.forms import CaseAutomatedForm
from tcms.testcases.forms import TestCase
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestCaseRun
from tcms.testruns.models import TestCaseRunStatus
from tests import AuthMixin, BaseCaseRun, BasePlanCase
from tests import remove_perm_from_user
from tests import user_should_have_perm
from tests import factories as f


class TestQuickSearch(BaseCaseRun):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = reverse('nitrate-search')

    def test_goto_plan(self):
        response = self.client.get(
            self.search_url,
            {'search_type': 'plans', 'search_content': self.plan.pk})
        self.assertRedirects(
            response,
            reverse('plan-get', args=[self.plan.pk]),
            target_status_code=HTTPStatus.MOVED_PERMANENTLY)

    def test_goto_case(self):
        response = self.client.get(
            self.search_url,
            {'search_type': 'cases', 'search_content': self.case_1.pk})

        self.assertRedirects(
            response,
            reverse('case-get', args=[self.case_1.pk]))

    def test_goto_run(self):
        response = self.client.get(
            self.search_url,
            {'search_type': 'runs', 'search_content': self.test_run.pk})
        self.assertRedirects(
            response,
            reverse('run-get', args=[self.test_run.pk]))

    def test_goto_plan_search(self):
        response = self.client.get(
            self.search_url,
            {'search_type': 'plans', 'search_content': 'keyword'})
        url = '{}?a=search&search=keyword'.format(reverse('plans-all'))
        self.assertRedirects(response, url)

    def test_goto_case_search(self):
        response = self.client.get(
            self.search_url,
            {'search_type': 'cases', 'search_content': 'keyword'})
        url = '{}?a=search&search=keyword'.format(reverse('cases-all'))
        self.assertRedirects(response, url)

    def test_goto_run_search(self):
        response = self.client.get(
            self.search_url,
            {'search_type': 'runs', 'search_content': 'keyword'})
        url = '{}?a=search&search=keyword'.format(reverse('runs-all'))
        self.assertRedirects(response, url)

    def test_goto_search_if_no_object_is_found(self):
        non_existing_pk = 9999999
        response = self.client.get(
            self.search_url,
            {'search_type': 'cases', 'search_content': non_existing_pk})
        url = '{}?a=search&search={}'.format(
            reverse('cases-all'), non_existing_pk)
        self.assertRedirects(response, url)

    def test_404_if_unknown_search_type(self):
        response = self.client.get(
            self.search_url,
            {'search_type': 'unknown type', 'search_content': self.plan.pk})
        self.assert404(response)

    def test_404_when_missing_search_content(self):
        response = self.client.get(self.search_url, {'search_type': 'plan'})
        self.assert404(response)

    def test_404_when_missing_search_type(self):
        response = self.client.get(self.search_url, {'search_content': 'python'})
        self.assert404(response)


class TestCommentCaseRuns(BaseCaseRun):
    """Test case for ajax.comment_case_runs"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.many_comments_url = reverse('caserun-comment-caseruns')

    def test_refuse_if_missing_comment(self):
        response = self.client.post(self.many_comments_url,
                                    {'run': [self.case_run_1.pk, self.case_run_2.pk]})
        self.assertJsonResponse(
            response,
            {'message': 'Comments needed'},
            status_code=HTTPStatus.BAD_REQUEST
        )

    def test_refuse_if_missing_no_case_run_pk(self):
        response = self.client.post(self.many_comments_url,
                                    {'comment': 'new comment', 'run': []})
        self.assertJsonResponse(
            response,
            {'message': 'No runs selected.'},
            status_code=HTTPStatus.BAD_REQUEST
        )

        response = self.client.post(self.many_comments_url,
                                    {'comment': 'new comment'})
        self.assertJsonResponse(
            response,
            {'message': 'No runs selected.'},
            status_code=HTTPStatus.BAD_REQUEST
        )

    def test_refuse_if_passed_case_run_pks_not_exist(self):
        response = self.client.post(self.many_comments_url, {
            'comment': 'new comment',
            'run': [99999998, 1009900]
        })
        self.assertJsonResponse(
            response,
            {'message': 'No caserun found.'},
            status_code=HTTPStatus.BAD_REQUEST
        )

    def test_add_comment_to_case_runs(self):
        new_comment = 'new comment'
        response = self.client.post(self.many_comments_url, {
            'comment': new_comment,
            'run': [self.case_run_1.pk, self.case_run_2.pk]
        })
        self.assertJsonResponse(response, {})

        # Assert comments are added
        case_run_ct = ContentType.objects.get_for_model(TestCaseRun)

        for case_run_pk in (self.case_run_1.pk, self.case_run_2.pk):
            comments = Comment.objects.filter(object_pk=case_run_pk,
                                              content_type=case_run_ct)
            self.assertEqual(new_comment, comments[0].comment)
            self.assertEqual(self.tester, comments[0].user)


class TestUpdateObject(BasePlanCase):
    """Test case for update"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = 'testplans.change_testplan'
        cls.update_url = reverse('ajax-update')

    def setUp(self):
        super().setUp()
        user_should_have_perm(self.tester, self.permission)

    def test_refuse_if_missing_permission(self):
        remove_perm_from_user(self.tester, self.permission)

        response = self.client.post(self.update_url, {
            'content_type': 'testplans.testplan',
            'object_pk': self.plan.pk,
            'field': 'is_active',
            'value': 'False',
            'value_type': 'bool'
        })

        self.assertJsonResponse(
            response,
            {'message': 'Permission Denied.'},
            status_code=HTTPStatus.FORBIDDEN
        )

    def test_update_plan_is_active(self):
        response = self.client.post(self.update_url, {
            'content_type': 'testplans.testplan',
            'object_pk': self.plan.pk,
            'field': 'is_active',
            'value': 'False',
            'value_type': 'bool'
        })

        self.assertJsonResponse(response, {})
        plan = TestPlan.objects.get(pk=self.plan.pk)
        self.assertFalse(plan.is_active)


class TestAddPlanParent(AuthMixin, test.TestCase):
    """
    Another case of ajax.update by adding a parent plan to a plan which does
    not have one yet

    This test expects to ensure log_action succeeds by setting original_value
    properly.
    """

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.product = f.ProductFactory()
        cls.product_version = f.VersionFactory(value='1.0', product=cls.product)
        cls.plan = f.TestPlanFactory(
            product=cls.product,
            product_version=cls.product_version)
        cls.parent = f.TestPlanFactory(
            product=cls.product,
            product_version=cls.product_version)

    def test_set_plan_parent_for_the_first_time(self):
        user_should_have_perm(self.tester, 'testplans.change_testplan')

        self.client.post(reverse('ajax-update'), {
            'content_type': 'testplans.testplan',
            'object_pk': self.plan.pk,
            'field': 'parent',
            'value': self.parent.pk,
            'value_type': 'int'
        })

        plan = TestPlan.objects.get(pk=self.plan.pk)
        assert self.parent.pk == plan.parent.pk

        log = TCMSLogModel.objects.first()
        assert log.field == 'parent'
        assert log.original_value == 'None'
        assert log.new_value == str(self.parent.pk)


class TestUpdateCaseRunStatus(BaseCaseRun):
    """Test case for update_case_run_status"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = 'testruns.change_testcaserun'
        cls.update_url = reverse('ajax-update-caserun-status')

    def setUp(self):
        super().setUp()
        user_should_have_perm(self.tester, self.permission)

    def test_refuse_if_missing_permission(self):
        remove_perm_from_user(self.tester, self.permission)

        response = self.client.post(self.update_url, {
            'content_type': 'testruns.testcaserun',
            'object_pk': self.case_run_1.pk,
            'field': 'case_run_status',
            'value': str(TestCaseRunStatus.objects.get(name='PAUSED').pk),
            'value_type': 'int',
        })

        self.assertJsonResponse(
            response,
            {'message': 'Permission Denied.'},
            status_code=HTTPStatus.FORBIDDEN
        )

    def test_change_case_run_status(self):
        response = self.client.post(self.update_url, {
            'content_type': 'testruns.testcaserun',
            'object_pk': self.case_run_1.pk,
            'field': 'case_run_status',
            'value': str(TestCaseRunStatus.objects.get(name='PAUSED').pk),
            'value_type': 'int',
        })

        self.assertJsonResponse(response, {})
        self.assertEqual(
            'PAUSED', TestCaseRun.objects.get(pk=self.case_run_1.pk).case_run_status.name)


class TestGetForm(test.TestCase):
    """Test case for form"""

    def test_get_form(self):
        response = self.client.get(reverse('ajax-form'),
                                   {'app_form': 'testcases.CaseAutomatedForm'})
        form = CaseAutomatedForm()

        resp_content = response.content.decode('utf-8')
        self.assertHTMLEqual(resp_content, form.as_p())


class TestUpdateCasePriority(BasePlanCase):
    """Test case for update_cases_default_tester"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = 'testcases.change_testcase'
        cls.case_update_url = reverse('ajax-update-cases-default-tester')

    def setUp(self):
        super().setUp()
        user_should_have_perm(self.tester, self.permission)

    def test_refuse_if_missing_permission(self):
        remove_perm_from_user(self.tester, self.permission)

        response = self.client.post(
            self.case_update_url,
            {
                'target_field': 'priority',
                'from_plan': self.plan.pk,
                'case': [self.case_1.pk, self.case_3.pk],
                'new_value': Priority.objects.get(value='P3').pk,
            })

        self.assertJsonResponse(
            response,
            {'message': "You don't have enough permission to update TestCases."},
            status_code=HTTPStatus.FORBIDDEN
        )

    def test_update_case_priority(self):
        response = self.client.post(
            self.case_update_url,
            {
                'target_field': 'priority',
                'from_plan': self.plan.pk,
                'case': [self.case_1.pk, self.case_3.pk],
                'new_value': Priority.objects.get(value='P3').pk,
            })

        self.assertJsonResponse(response, {})

        for pk in (self.case_1.pk, self.case_3.pk):
            self.assertEqual('P3', TestCase.objects.get(pk=pk).priority.value)


class TestGetObjectInfo(BasePlanCase):
    """Test case for info view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.get_info_url = reverse('ajax-getinfo')

        cls.group_nitrate = f.TCMSEnvGroupFactory(name='nitrate')
        cls.group_new = f.TCMSEnvGroupFactory(name='NewGroup')

        cls.property_os = f.TCMSEnvPropertyFactory(name='os')
        cls.property_python = f.TCMSEnvPropertyFactory(name='python')
        cls.property_django = f.TCMSEnvPropertyFactory(name='django')

        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_nitrate,
                                         property=cls.property_os)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_nitrate,
                                         property=cls.property_python)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_new,
                                         property=cls.property_django)

    def test_get_env_properties(self):
        response = self.client.get(self.get_info_url, {'info_type': 'env_properties'})

        expected_json = json.loads(
            serializers.serialize(
                'json',
                TCMSEnvProperty.objects.all(),
                fields=('name', 'value')))
        self.assertEqual(expected_json, json.loads(response.content))

    def test_get_env_properties_by_group(self):
        response = self.client.get(self.get_info_url,
                                   {'info_type': 'env_properties',
                                    'env_group_id': self.group_new.pk})

        group = TCMSEnvGroup.objects.get(pk=self.group_new.pk)
        expected_json = json.loads(
            serializers.serialize(
                'json',
                group.property.all(),
                fields=('name', 'value')))
        self.assertEqual(expected_json, json.loads(response.content))

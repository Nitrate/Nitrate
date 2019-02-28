# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
import unittest
import xml.etree.ElementTree

from bs4 import BeautifulSoup
from datetime import datetime
from operator import attrgetter, itemgetter
import http.client

import mock

from django import test
from django.contrib.auth.models import User
from django.urls import reverse
from django.forms import ValidationError
from django.test import RequestFactory
from uuslug import slugify

from tcms.issuetracker.models import Issue
from tcms.management.models import TestTag, Component
from tcms.testcases.fields import MultipleEmailField
from tcms.testcases.forms import CaseTagForm
from tcms.testcases.models import TestCase
from tcms.testcases.models import TestCaseComponent
from tcms.testcases.models import TestCasePlan
from tcms.testcases.models import TestCaseTag
from tcms.testcases.views import ajax_response
from tests.factories import ComponentFactory
from tests.factories import IssueTrackerFactory
from tests.factories import IssueTrackerProductFactory
from tests.factories import TestCaseCategoryFactory
from tests.factories import TestCaseComponentFactory
from tests.factories import TestCaseFactory
from tests.factories import TestCaseTagFactory
from tests.factories import TestPlanFactory
from tests.factories import TestTagFactory
from tests import BaseCaseRun
from tests import BasePlanCase
from tests import remove_perm_from_user
from tests import user_should_have_perm


class TestMultipleEmailField(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_delimiter = ','
        cls.field = MultipleEmailField(delimiter=cls.default_delimiter)

    def test_to_python(self):
        value = 'zhangsan@localhost'
        pyobj = self.field.to_python(value)
        self.assertEqual(pyobj, [value])

        value = 'zhangsan@localhost,,lisi@example.com,'
        pyobj = self.field.to_python(value)
        self.assertEqual(pyobj, ['zhangsan@localhost', 'lisi@example.com'])

        for value in ('', None, []):
            pyobj = self.field.to_python(value)
            self.assertEqual(pyobj, [])

    def test_clean(self):
        value = 'zhangsan@localhost'
        data = self.field.clean(value)
        self.assertEqual(data, [value])

        value = 'zhangsan@localhost,lisi@example.com'
        data = self.field.clean(value)
        self.assertEqual(data, ['zhangsan@localhost', 'lisi@example.com'])

        value = ',zhangsan@localhost, ,lisi@example.com, \n'
        data = self.field.clean(value)
        self.assertEqual(data, ['zhangsan@localhost', 'lisi@example.com'])

        value = ',zhangsan,zhangsan@localhost, \n,lisi@example.com, '
        self.assertRaises(ValidationError, self.field.clean, value)

        value = ''
        self.field.required = True
        self.assertRaises(ValidationError, self.field.clean, value)

        value = ''
        self.field.required = False
        data = self.field.clean(value)
        self.assertEqual(data, [])


class CaseTagFormTest(test.TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tag_1 = TestTagFactory(name='tag one')
        cls.tag_2 = TestTagFactory(name='tag two')
        cls.tag_3 = TestTagFactory(name='tag three')

        cls.cases = []
        for i in range(5):
            case = TestCaseFactory(summary='test_case_number_%d' % i)
            case.add_tag(cls.tag_1)
            if i % 2 == 0:
                case.add_tag(cls.tag_2)
            if i % 3 == 0:
                case.add_tag(cls.tag_3)
            cls.cases.append(case)

    def test_populate_from_cases_contains_all_three_tags(self):
        case_ids = [case.pk for case in self.cases]
        form = CaseTagForm()
        form.populate(case_ids=case_ids)

        self.assertEqual(3, len(form.fields['o_tag'].queryset))
        form_tags = form.fields['o_tag'].queryset.values_list('name', flat=True)
        self.assertIn(self.tag_1.name, form_tags)
        self.assertIn(self.tag_2.name, form_tags)
        self.assertIn(self.tag_3.name, form_tags)


# ### Test cases for view methods ###


class TestOperateComponentView(BasePlanCase):
    """Tests for operating components on cases"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.comp_application = ComponentFactory(name='Application',
                                                product=cls.product,
                                                initial_owner=cls.tester,
                                                initial_qa_contact=cls.tester)
        cls.comp_database = ComponentFactory(name='Database',
                                             product=cls.product,
                                             initial_owner=cls.tester,
                                             initial_qa_contact=cls.tester)
        cls.comp_cli = ComponentFactory(name='CLI',
                                        product=cls.product,
                                        initial_owner=cls.tester,
                                        initial_qa_contact=cls.tester)
        cls.comp_api = ComponentFactory(name='API',
                                        product=cls.product,
                                        initial_owner=cls.tester,
                                        initial_qa_contact=cls.tester)

        TestCaseComponentFactory(case=cls.case_1, component=cls.comp_cli)
        TestCaseComponentFactory(case=cls.case_1, component=cls.comp_api)

        user_should_have_perm(cls.tester, 'testcases.add_testcasecomponent')

    def tearDown(self):
        remove_perm_from_user(self.tester,
                              'testcases.delete_testcasecomponent')

    def test_show_components_form(self):
        self.client.login(username=self.tester.username, password='password')

        response = self.client.post(reverse('cases-get-component-form'),
                                    {'product': self.product.pk})

        self.assertContains(
            response,
            '<option value="{}" selected="selected">{}</option>'.format(
                self.product.pk, self.product.name),
            html=True)

        comp_options = (
            f'<option value="{comp.pk}">{comp.name}</option>'
            for comp in (self.comp_application,
                         self.comp_database,
                         self.comp_cli,
                         self.comp_api)
        )
        self.assertContains(
            response,
            '''<select multiple="multiple" id="id_o_component" name="o_component">
{}
</select>'''.format(''.join(comp_options)),
            html=True)

    def test_add_components(self):
        self.client.login(username=self.tester.username, password='password')

        post_data = {
            'product': self.product.pk,
            'o_component': [self.comp_application.pk, self.comp_database.pk],
            'case': [self.case_1.pk],
            'a': 'add',
            'from_plan': self.plan.pk,
        }
        response = self.client.post(reverse('cases-add-component'), post_data)

        data = json.loads(response.content)
        self.assertEqual(
            {
                'rc': 0,
                'response': 'Succeed to add component(s) Application, Database.',
            },
            data)

        for comp in (self.comp_application, self.comp_database):
            case_components = TestCaseComponent.objects.filter(
                case=self.case_1, component=comp)
            self.assertTrue(case_components.exists())

    def test_remove_components(self):
        self.client.login(username=self.tester.username, password='password')

        user_should_have_perm(self.tester,
                              'testcases.delete_testcasecomponent')

        post_data = {
            'o_component': [self.comp_cli.pk, self.comp_api.pk],
            'case': [self.case_1.pk],
            'a': 'remove',
        }
        response = self.client.post(reverse('cases-remove-component'),
                                    post_data)

        data = json.loads(response.content)
        self.assertEqual(
            {
                'rc': 0,
                'response': 'Succeed to remove component(s) CLI, API.'
            },
            data)

        for comp in (self.comp_cli, self.comp_api):
            case_components = TestCaseComponent.objects.filter(
                case=self.case_1, component=comp)
            self.assertFalse(case_components.exists())


class TestOperateCategoryView(BasePlanCase):
    """Tests for operating category on cases"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case_cat_full_auto = TestCaseCategoryFactory(name='Full Auto', product=cls.product)
        cls.case_cat_full_manual = TestCaseCategoryFactory(name='Full Manual', product=cls.product)

        user_should_have_perm(cls.tester, 'testcases.add_testcasecomponent')

        cls.case_category_url = reverse('cases-category')

    def test_show_categories_form(self):
        self.client.login(username=self.tester.username, password='password')

        response = self.client.post(self.case_category_url, {'product': self.product.pk})

        self.assertContains(
            response,
            '<option value="{}" selected="selected">{}</option>'.format(
                self.product.pk, self.product.name),
            html=True)

        categories = (f'<option value="{category.pk}">{category.name}</option>'
                      for category in self.product.category.all())
        self.assertContains(
            response,
            '''<select multiple="multiple" id="id_o_category" name="o_category">
{}
</select>'''.format(''.join(categories)),
            html=True)

    def test_update_cases_category(self):
        self.client.login(username=self.tester.username, password='password')

        post_data = {
            'from_plan': self.plan.pk,
            'product': self.product.pk,
            'case': [self.case_1.pk, self.case_3.pk],
            'a': 'update',
            'o_category': self.case_cat_full_auto.pk,
        }
        response = self.client.post(self.case_category_url, post_data)

        data = json.loads(response.content)
        self.assertEqual({'rc': 0, 'response': 'ok', 'errors_list': []}, data)

        for pk in (self.case_1.pk, self.case_3.pk):
            case = TestCase.objects.get(pk=pk)
            self.assertEqual(self.case_cat_full_auto, case.category)


class TestAddIssueToCase(BasePlanCase):
    """Tests for adding issue to case"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.plan_tester = User.objects.create_user(username='plantester',
                                                   email='plantester@example.com',
                                                   password='password')
        user_should_have_perm(cls.plan_tester, 'issuetracker.change_issue')

        cls.case_issue_url = reverse('case-issue', args=[cls.case_1.pk])
        cls.issue_tracker = IssueTrackerFactory(name='TestBZ')

    def test_add_and_remove_a_issue(self):
        user_should_have_perm(self.plan_tester, 'issuetracker.add_issue')
        user_should_have_perm(self.plan_tester, 'issuetracker.delete_issue')

        self.client.login(username=self.plan_tester.username, password='password')
        request_data = {
            'handle': 'add',
            'issue_key': '123456',
            'tracker': self.issue_tracker.pk,
        }
        self.client.get(self.case_issue_url, request_data)
        self.assertTrue(self.case_1.issues.filter(issue_key='123456').exists())

        request_data = {
            'handle': 'remove',
            'issue_key': '123456',
        }
        response = self.client.get(self.case_issue_url, request_data)

        self.assertEqual(200, response.status_code)
        self.assertFalse(self.case_1.issues.filter(issue_key='123456').exists())


class TestOperateCasePlans(BasePlanCase):
    """Test operation in case' plans tab"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Besides the plan and its cases created in parent class, this test case
        # also needs other cases in order to list multiple plans of a case and
        # remove a plan from a case.

        cls.plan_test_case_plans = TestPlanFactory(author=cls.tester,
                                                   owner=cls.tester,
                                                   product=cls.product,
                                                   product_version=cls.version)
        cls.plan_test_add = TestPlanFactory(author=cls.tester,
                                            owner=cls.tester,
                                            product=cls.product,
                                            product_version=cls.version)
        cls.plan_test_remove = TestPlanFactory(author=cls.tester,
                                               owner=cls.tester,
                                               product=cls.product,
                                               product_version=cls.version)

        cls.case_1.add_to_plan(cls.plan_test_case_plans)
        cls.case_1.add_to_plan(cls.plan_test_remove)

        cls.plan_tester = User.objects.create_user(username='plantester',
                                                   email='plantester@example.com',
                                                   password='password')

        cls.case_plans_url = reverse('case-plan', args=[cls.case_1.pk])

    def tearDown(self):
        remove_perm_from_user(self.plan_tester, 'testcases.add_testcaseplan')
        remove_perm_from_user(self.plan_tester, 'testcases.change_testcaseplan')

    def assert_list_case_plans(self, response, case):
        for case_plan_rel in TestCasePlan.objects.filter(case=case):
            plan = case_plan_rel.plan
            self.assertContains(
                response,
                '<a href="/plan/{0}/{1}">{0}</a>'.format(plan.pk, slugify(plan.name)),
                html=True)

            self.assertContains(
                response,
                '<a href="/plan/{}/{}">{}</a>'.format(plan.pk, slugify(plan.name), plan.name),
                html=True)

    def test_list_plans(self):
        response = self.client.get(self.case_plans_url)
        self.assert_list_case_plans(response, self.case_1)

    def test_missing_permission_to_add(self):
        response = self.client.get(self.case_plans_url,
                                   {'a': 'add', 'plan_id': self.plan_test_add.pk})
        self.assertContains(response, 'Permission denied')

    def test_missing_permission_to_remove(self):
        response = self.client.get(self.case_plans_url,
                                   {'a': 'remove', 'plan_id': self.plan_test_remove.pk})
        self.assertContains(response, 'Permission denied')

    def test_add_a_plan(self):
        user_should_have_perm(self.plan_tester, 'testcases.add_testcaseplan')
        self.client.login(username=self.plan_tester.username, password='password')
        response = self.client.get(self.case_plans_url,
                                   {'a': 'add', 'plan_id': self.plan_test_add.pk})

        self.assert_list_case_plans(response, self.case_1)

        self.assertTrue(TestCasePlan.objects.filter(
            plan=self.plan_test_add, case=self.case_1).exists())

    def test_remove_a_plan(self):
        user_should_have_perm(self.plan_tester, 'testcases.change_testcaseplan')
        self.client.login(username=self.plan_tester.username, password='password')
        response = self.client.get(self.case_plans_url,
                                   {'a': 'remove', 'plan_id': self.plan_test_remove.pk})

        self.assert_list_case_plans(response, self.case_1)

        not_linked_to_plan = not TestCasePlan.objects.filter(
            case=self.case_1, plan=self.plan_test_remove).exists()
        self.assertTrue(not_linked_to_plan)

    def test_add_a_few_plans(self):
        user_should_have_perm(self.plan_tester, 'testcases.add_testcaseplan')
        self.client.login(username=self.plan_tester.username, password='password')
        # This time, add a few plans to another case
        url = reverse('case-plan', args=[self.case_2.pk])

        response = self.client.get(url,
                                   {'a': 'add', 'plan_id': [self.plan_test_add.pk,
                                                            self.plan_test_remove.pk]})

        self.assert_list_case_plans(response, self.case_2)

        self.assertTrue(TestCasePlan.objects.filter(
            case=self.case_2, plan=self.plan_test_add).exists())
        self.assertTrue(TestCasePlan.objects.filter(
            case=self.case_2, plan=self.plan_test_remove).exists())


class TestOperateCaseTag(BasePlanCase):
    """Test remove tags to and from cases in a plan"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tag_fedora = TestTagFactory(name='fedora')
        cls.tag_rhel = TestTagFactory(name='rhel')
        cls.tag_python = TestTagFactory(name='python')

        TestCaseTagFactory(case=cls.case_1, tag=cls.tag_fedora)
        TestCaseTagFactory(case=cls.case_1, tag=cls.tag_rhel)
        TestCaseTagFactory(case=cls.case_1, tag=cls.tag_python)
        TestCaseTagFactory(case=cls.case_3, tag=cls.tag_rhel)
        TestCaseTagFactory(case=cls.case_3, tag=cls.tag_python)

        cls.cases_tag_url = reverse('cases-tag')

    def test_show_cases_list(self):
        response = self.client.post(self.cases_tag_url,
                                    {'case': [self.case_1.pk, self.case_3.pk]})

        tags = TestTag.objects.filter(
            cases__in=[self.case_1, self.case_3]).order_by('name').distinct()
        tag_options = [f'<option value="{tag.pk}">{tag.name}</option>'
                       for tag in tags]

        self.assertContains(
            response,
            '''<p><label for="id_o_tag">Tags:</label>
<select multiple="multiple" id="id_o_tag" name="o_tag">{}
</select></p>'''.format(''.join(tag_options)),
            html=True)

    def test_remove_tags_from_cases(self):
        tags_to_remove = [self.tag_rhel.pk, self.tag_python.pk]
        remove_from_cases = [self.case_1.pk, self.case_3.pk]
        response = self.client.post(
            self.cases_tag_url,
            {'a': 'remove', 'o_tag': tags_to_remove, 'case': remove_from_cases})

        data = json.loads(response.content)
        self.assertEqual({'rc': 0, 'response': 'ok', 'errors_list': []}, data)

        self.assertFalse(
            TestCaseTag.objects.filter(
                case=self.case_1.pk, tag=self.tag_rhel.pk).exists())
        self.assertFalse(
            TestCaseTag.objects.filter(
                case=self.case_1.pk, tag=self.tag_python.pk).exists())
        self.assertFalse(
            TestCaseTag.objects.filter(
                case=self.case_3.pk, tag=self.tag_rhel.pk).exists())
        self.assertFalse(
            TestCaseTag.objects.filter(
                case=self.case_3.pk, tag=self.tag_python.pk).exists())

    @mock.patch('tcms.testcases.models.TestCase.remove_tag',
                side_effect=ValueError('value error'))
    def test_ensure_response_if_error_happens_when_remove_tag(self, remove_tag):
        # This test does not care about what tags are removed from which cases
        response = self.client.post(
            self.cases_tag_url,
            {'a': 'remove', 'o_tag': self.tag_fedora.pk, 'case': self.case_1.pk})

        remove_tag.assert_called_once()

        data = json.loads(response.content)
        self.assertEqual(
            {
                'rc': 1,
                'response': 'value error',
                'errors_list': [{'case': self.case_1.pk, 'tag': self.tag_fedora.pk}],
            },
            data)


class TestEditCase(BasePlanCase):
    """Test edit view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.proposed_case = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_proposed,
            plan=[cls.plan])

        user_should_have_perm(cls.tester, 'testcases.change_testcase')
        cls.case_edit_url = reverse('case-edit', args=[cls.case_1.pk])

        # Copy, then modify or add new data for specific tests below
        cls.edit_data = {
            'from_plan': cls.plan.pk,
            'summary': cls.case_1.summary,
            'product': cls.case_1.category.product.pk,
            'category': cls.case_1.category.pk,
            'default_tester': '',
            'estimated_time': '0m',
            'case_status': cls.case_status_confirmed.pk,
            'arguments': '',
            'extra_link': '',
            'notes': '',
            'is_automated': '0',
            'requirement': '',
            'script': '',
            'alias': '',
            'priority': cls.case_1.priority.pk,
            'tag': 'RHEL',
            'setup': '',
            'action': '',
            'breakdown': '',
            'effect': '',
            'cc_list': '',
        }

    def test_404_if_case_id_not_exist(self):
        self.login_tester()
        url = reverse('case-edit', args=[99999])
        response = self.client.get(url)
        self.assert404(response)

    def test_404_if_from_plan_not_exist(self):
        self.login_tester()
        response = self.client.get(self.case_edit_url, {'from_plan': 9999})
        self.assert404(response)

    def test_show_edit_page(self):
        self.login_tester()
        response = self.client.get(self.case_edit_url)
        self.assertEqual(200, response.status_code)

    def test_edit_a_case(self):
        self.login_tester()

        edit_data = self.edit_data.copy()
        new_summary = f'Edited: {self.case_1.summary}'
        edit_data['summary'] = new_summary

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = '{}?from_plan={}'.format(
            reverse('case-get', args=[self.case_1.pk]),
            self.plan.pk,
        )
        self.assertRedirects(response, redirect_url)

        edited_case = TestCase.objects.get(pk=self.case_1.pk)
        self.assertEqual(new_summary, edited_case.summary)

    def test_continue_edit_this_case_after_save(self):
        self.login_tester()

        edit_data = self.edit_data.copy()
        edit_data['_continue'] = 'continue edit'

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = '{}?from_plan={}'.format(
            reverse('case-edit', args=[self.case_1.pk]),
            self.plan.pk,
        )
        self.assertRedirects(response, redirect_url)

    def test_continue_edit_next_confirmed_case_after_save(self):
        self.login_tester()

        edit_data = self.edit_data.copy()
        edit_data['_continuenext'] = 'continue edit next case'

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = '{}?from_plan={}'.format(
            reverse('case-edit', args=[self.case_2.pk]),
            self.plan.pk,
        )
        self.assertRedirects(response, redirect_url)

    def test_continue_edit_next_non_confirmed_case_after_save(self):
        self.login_tester()

        edit_data = self.edit_data.copy()
        edit_data['case_status'] = self.case_status_proposed.pk
        edit_data['_continuenext'] = 'continue edit next case'

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = '{}?from_plan={}'.format(
            reverse('case-edit', args=[self.proposed_case.pk]),
            self.plan.pk,
        )
        self.assertRedirects(response, redirect_url)

    def test_return_to_plan_confirmed_cases_tab(self):
        self.login_tester()

        edit_data = self.edit_data.copy()
        edit_data['_returntoplan'] = 'return to plan'

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = '{}#testcases'.format(
            reverse('plan-get', args=[self.plan.pk])
        )
        self.assertRedirects(response, redirect_url, target_status_code=301)

    def test_return_to_plan_review_cases_tab(self):
        self.login_tester()

        edit_data = self.edit_data.copy()
        edit_data['case_status'] = self.case_status_proposed.pk
        edit_data['_returntoplan'] = 'return to plan'

        response = self.client.post(self.case_edit_url, edit_data)

        redirect_url = '{}#reviewcases'.format(
            reverse('plan-get', args=[self.plan.pk])
        )
        self.assertRedirects(response, redirect_url, target_status_code=301)


class TestAJAXSearchCases(BasePlanCase):
    """Test ajax_search"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.search_data = {
            'summary': '',
            'author': '',
            'product': '',
            'plan': '',
            'is_automated': '',
            'category': '',
            'component': '',
            'issue_key': '',
            'tag__name__in': '',
            'a': 'search',
        }

        cls.search_url = reverse('cases-ajax-search')

    def test_search_all_cases(self):
        response = self.client.get(self.search_url, self.search_data)

        data = json.loads(response.content)

        cases_count = self.plan.case.count()
        self.assertEqual(cases_count, data['iTotalRecords'])
        self.assertEqual(cases_count, data['iTotalDisplayRecords'])


class TestChangeCasesAutomated(BasePlanCase):
    """Test automated view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.change_data = {
            'case': [cls.case_1.pk, cls.case_2.pk],
            'a': 'change',
            # Add necessary automated value here:
            # o_is_automated
            # o_is_manual
            # o_is_automated_proposed
        }

        user_should_have_perm(cls.tester, 'testcases.change_testcase')
        cls.change_url = reverse('cases-automated')

    def test_update_automated(self):
        self.login_tester()

        change_data = self.change_data.copy()
        change_data['o_is_automated'] = 'on'

        response = self.client.post(self.change_url, change_data)

        self.assertJsonResponse(response, {'rc': 0, 'response': 'ok'})

        for pk in self.change_data['case']:
            case = TestCase.objects.get(pk=pk)
            self.assertEqual(1, case.is_automated)

    def test_update_manual(self):
        self.login_tester()

        change_data = self.change_data.copy()
        change_data['o_is_manual'] = 'on'

        response = self.client.post(self.change_url, change_data)

        self.assertJsonResponse(response, {'rc': 0, 'response': 'ok'})

        for pk in self.change_data['case']:
            case = TestCase.objects.get(pk=pk)
            self.assertEqual(0, case.is_automated)

    def test_update_automated_proposed(self):
        self.login_tester()

        change_data = self.change_data.copy()
        change_data['o_is_automated_proposed'] = 'on'

        response = self.client.post(self.change_url, change_data)

        self.assertJsonResponse(response, {'rc': 0, 'response': 'ok'})

        for pk in self.change_data['case']:
            case = TestCase.objects.get(pk=pk)
            self.assertTrue(case.is_automated_proposed)


class PlanCaseExportTestHelper:
    """Used to verify exported cases

    This could be reused for two use cases of export from cases or plans.
    """

    def assert_exported_case(self, case, element, expected_text,
                             expected_components, expected_tags,
                             expected_products):
        """Verify exported case info inside XML document

        :param case: a test case object to be exported.
        :type case: :class:`TestCase`
        :param element: an XML element object representing a test case inside
            XML document. It is the return value from ``ElementTree.findall``
            or ``ElementTree.find``.
        :param dict expected_text: a mapping representing expected case text object.
            It must have four key/value pairs ``action``, ``effect``, ``breakdown``
            and ``setup``.
        :param expected_components: a list of expected component names in
            whatever order.
        :type expected_components: list[str]
        :param expected_tags: a list of expected tag names in whatever order.
        :type expected_tags: list[str]
        :param expected_products: a list of expected product names in whatever
            order.
        :type expected_tags: list[str]
        """
        self.assertEqual(case.author.email, element.attrib['author'])
        self.assertEqual(case.priority.value, element.attrib['priority'])
        self.assertEqual(case.is_automated, int(element.attrib['automated']))
        self.assertEqual(case.case_status.name, element.attrib['status'])
        self.assertEqual(case.summary, element.find('summary').text)
        self.assertEqual(case.category.name, element.find('categoryname').text)
        if not case.default_tester:
            self.assertEqual(None, element.find('defaulttester').text)
        else:
            self.assertEqual(case.default_tester.email,
                             element.find('defaulttester').text)
        self.assertEqual(case.notes or None, element.find('notes').text)
        self.assertEqual(expected_text['action'], element.find('action').text)
        self.assertEqual(expected_text['effect'],
                         element.find('expectedresults').text)
        self.assertEqual(expected_text['setup'], element.find('setup').text)
        self.assertEqual(expected_text['breakdown'],
                         element.find('breakdown').text)

        self.assertEqual(
            sorted(expected_components),
            sorted(elem.text.strip() for elem in element.findall('component')))

        self.assertEqual(
            set(expected_products),
            set(map(itemgetter('product'),
                    map(attrgetter('attrib'), element.findall('component'))
                    ))
        )

        self.assertEqual(
            sorted(expected_tags),
            sorted(elem.text.strip() for elem in element.findall('tag'))
        )

        self.assertEqual(
            sorted(map(attrgetter('name'), case.plan.all())),
            sorted(item.text.strip() for item in
                   element.find('testplan_reference').findall('item'))
        )


class TestExportCases(PlanCaseExportTestHelper, BasePlanCase):
    """Test export view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.export_url = reverse('cases-export')

        # Change case status in order to test cases in expected scope can be exported.
        cls.case_1.case_status = cls.case_status_proposed
        cls.case_1.save()

        # Add components to case 1 and case 2
        for name in ['vi', 'emacs']:
            component = Component.objects.create(
                name=name,
                product=cls.product,
                initial_owner=cls.tester,
                initial_qa_contact=cls.tester)
            cls.case_1.add_component(component)

        for name in ['db', 'cli', 'webui']:
            component = Component.objects.create(
                name=name,
                product=cls.product,
                initial_owner=cls.tester,
                initial_qa_contact=cls.tester)
            cls.case_2.add_component(component)

        # Add tags to case 2
        for name in ['python', 'nitrate']:
            tag = TestTag.objects.create(name=name)
            cls.case_2.add_tag(tag)

        # Add text to case 1 with several verions
        cls.case_1.add_text('action', 'effect', 'setup', 'breakdown')
        cls.case_1.add_text('action 1', 'effect 1', 'setup 1', 'breakdown 1')
        cls.case_1.add_text('action 2', 'effect 2', 'setup 2', 'breakdown 2')

    def assert_exported_case_1(self, element):
        self.assert_exported_case(
            self.case_1,
            element,
            {
                'action': 'action 2',
                'effect': 'effect 2',
                'setup': 'setup 2',
                'breakdown': 'breakdown 2'
            },
            ['emacs', 'vi'],
            [],
            [self.product.name]
        )

    def assert_exported_case_2(self, element):
        self.assert_exported_case(
            self.case_2,
            element,
            {
                'action': None,
                'effect': None,
                'setup': None,
                'breakdown': None,
            },
            ['cli', 'db', 'webui'],
            ['nitrate', 'python'],
            [self.product.name]
        )

    def test_export_cases(self):
        response = self.client.post(self.export_url,
                                    {'case': [self.case_1.pk, self.case_2.pk]})

        today = datetime.now()
        # Verify header
        self.assertEqual(
            'attachment; filename=tcms-testcases-%02i-%02i-%02i.xml' % (
                today.year, today.month, today.day),
            response['Content-Disposition'])
        # verify content

        xmldoc = xml.etree.ElementTree.fromstring(response.content)
        exported_cases_elements = xmldoc.findall('testcase')
        self.assertEqual(2, len(exported_cases_elements))

        for element in exported_cases_elements:
            summary = element.find('summary').text
            if summary == self.case_1.summary:
                self.assert_exported_case_1(element)
            elif summary == self.case_2.summary:
                self.assert_exported_case_2(element)

    def test_no_cases_to_be_exported(self):
        response = self.client.post(self.export_url, {})
        self.assertContains(response, 'At least one target is required')


class TestPrintablePage(BasePlanCase):
    """Test printable page view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.printable_url = reverse('cases-printable')

        cls.case_1.add_text(action='action',
                            effect='effect',
                            setup='setup',
                            breakdown='breakdown')
        cls.case_2.add_text(action='action',
                            effect='effect',
                            setup='setup',
                            breakdown='breakdown')

    def test_no_cases_to_print(self):
        response = self.client.post(self.printable_url, {})
        self.assertContains(response, 'At least one target is required')

    def test_printable_page(self):
        response = self.client.post(self.printable_url,
                                    {'case': [self.case_1.pk, self.case_2.pk]})

        for case in [self.case_1, self.case_2]:
            self.assertContains(
                response,
                f'<h3>[{case.pk}] {case.summary}</h3>',
                html=True
            )


class TestCloneCase(BasePlanCase):
    """Test clone view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user_should_have_perm(cls.tester, 'testcases.add_testcase')
        cls.clone_url = reverse('cases-clone')

    def test_refuse_if_missing_argument(self):
        self.login_tester()

        # Refuse to clone cases if missing selectAll and case arguments
        response = self.client.get(self.clone_url, {})

        self.assertContains(response, 'At least one case is required')

    def test_show_clone_page_with_from_plan(self):
        self.login_tester()

        response = self.client.get(self.clone_url,
                                   {'from_plan': self.plan.pk,
                                    'case': [self.case_1.pk, self.case_2.pk]})

        self.assertContains(
            response,
            '''<div>
    <input type="radio" id="id_use_sameplan" name="selectplan" value="{0}">
    <label for="id_use_sameplan" class="strong">Use the same Plan -- {0} : {1}</label>
</div>'''.format(self.plan.pk, self.plan.name),
            html=True)

        # The order of cases is important for running tests against PostgreSQL.
        # Instead of calling assertContains to assert a piece of HTML inside the
        # response, it is necessary to inspect the response content directly.

        bs = BeautifulSoup(response.content.decode('utf-8'), 'html.parser')
        case_ids = sorted(map(int, [
            elem.attrs['value'] for elem in bs.find(id='id_case').find_all('input')
        ]))
        self.assertEqual([self.case_1.pk, self.case_2.pk], case_ids)

    def test_show_clone_page_without_from_plan(self):
        self.login_tester()

        response = self.client.get(self.clone_url, {'case': self.case_1.pk})

        self.assertNotContains(
            response,
            'Use the same Plan -- {} : {}'.format(self.plan.pk,
                                                  self.plan.name),
        )

        self.assertContains(
            response,
            '<label for="id_case_0">'
            '<input checked="checked" id="id_case_0" name="case" '
            'type="checkbox" value="{}"> {}</label>'.format(
                self.case_1.pk, self.case_1.summary),
            html=True)


class TestSearchCases(BasePlanCase):
    """Test search view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.search_url = reverse('cases-search')

    def test_search_without_selected_product(self):
        response = self.client.get(self.search_url, {})
        self.assertContains(
            response,
            '<option value="" selected="selected">---------</option>',
            html=True)

    def test_search_with_selected_product(self):
        response = self.client.get(self.search_url,
                                   {'product': self.product.pk})
        self.assertContains(
            response,
            '<option value="{}" selected="selected">{}</option>'.format(
                self.product.pk, self.product.name),
            html=True
        )


class TestAJAXResponse(BasePlanCase):
    """Test ajax_response"""

    def setUp(self):
        self.factory = RequestFactory()

        self.column_names = [
            'case_id',
            'summary',
            'author__username',
            'default_tester__username',
            'is_automated',
            'case_status__name',
            'category__name',
            'priority__value',
            'create_date',
        ]

        self.template = 'case/common/json_cases.txt'

    def test_return_empty_cases(self):
        url = reverse('cases-ajax-search')
        request = self.factory.get(url, {

        })
        request.user = self.tester

        empty_cases = TestCase.objects.none()
        response = ajax_response(request, empty_cases, self.column_names, self.template)

        data = json.loads(response.content)

        self.assertEqual(0, data['sEcho'])
        self.assertEqual(0, data['iTotalRecords'])
        self.assertEqual(0, data['iTotalDisplayRecords'])
        self.assertEqual([], data['aaData'])

    def test_return_sorted_cases_by_name_desc(self):
        url = reverse('cases-ajax-search')
        request = self.factory.get(url, {
            'sEcho': 1,
            'iDisplayStart': 0,
            'iDisplayLength': 2,
            'iSortCol_0': 0,
            'sSortDir_0': 'desc',
            'iSortingCols': 1,
            'bSortable_0': 'true',
            'bSortable_1': 'true',
            'bSortable_2': 'true',
            'bSortable_3': 'true',
        })
        request.user = self.tester

        cases = self.plan.case.all()
        response = ajax_response(request, cases, self.column_names, self.template)

        data = json.loads(response.content)

        total = self.plan.case.count()
        self.assertEqual(1, data['sEcho'])
        self.assertEqual(total, data['iTotalRecords'])
        self.assertEqual(total, data['iTotalDisplayRecords'])
        self.assertEqual(2, len(data['aaData']))

        id_links = [row[2] for row in data['aaData']]
        id_links.sort()
        expected_id_links = [
            "<a href='{}'>{}</a>".format(
                reverse('case-get', args=[case.pk]),
                case.pk,
            )
            for case in self.plan.case.order_by('-pk')[0:2]
        ]
        expected_id_links.sort()
        self.assertEqual(expected_id_links, id_links)


class TestAddComponent(BasePlanCase):
    """Test AddComponentView"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.component_db = ComponentFactory(name='db', product=cls.product)
        cls.component_doc = ComponentFactory(name='doc', product=cls.product)
        cls.component_cli = ComponentFactory(name='cli', product=cls.product)

    def setUp(self):
        user_should_have_perm(self.tester, 'testcases.add_testcasecomponent')
        self.add_component_url = reverse('cases-add-component')

        self.login_tester()

    def test_add_one_component(self):
        resp = self.client.post(self.add_component_url, {
            'product': self.product.pk,
            'case': self.case_1.pk,
            'o_component': [self.component_db.pk],
        })

        self.assertEqual(200, resp.status_code)

        components = self.case_1.component.all()
        self.assertEqual(1, len(components))
        self.assertEqual(self.component_db, components[0])

    def test_add_multiple_components(self):
        resp = self.client.post(self.add_component_url, {
            'product': self.product.pk,
            'case': self.case_1.pk,
            'o_component': [self.component_db.pk, self.component_cli.pk],
        })

        self.assertEqual(200, resp.status_code)

        components = self.case_1.component.order_by('name')
        self.assertEqual(2, len(components))
        self.assertEqual(self.component_cli, components[0])
        self.assertEqual(self.component_db, components[1])

    def test_avoid_duplicate_components(self):
        TestCaseComponent.objects.create(case=self.case_1,
                                         component=self.component_doc)

        resp = self.client.post(self.add_component_url, {
            'product': self.product.pk,
            'case': self.case_1.pk,
            'o_component': [self.component_doc.pk, self.component_cli.pk],
        })

        self.assertEqual(200, resp.status_code)

        components = self.case_1.component.order_by('name')
        self.assertEqual(2, len(components))
        self.assertEqual(self.component_cli, components[0])
        self.assertEqual(self.component_doc, components[1])


class TestIssueManagement(BaseCaseRun):
    """Test add and remove issue to and from a test case"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user_should_have_perm(cls.tester, 'issuetracker.change_issue')
        cls.issue_manage_url = reverse('case-issue', args=[cls.case_1.pk])

        cls.tracker_product = IssueTrackerProductFactory(name='BZ')
        cls.issue_tracker = IssueTrackerFactory(
            service_url='http://localhost/',
            issue_report_endpoint='/enter_bug.cgi',
            tracker_product=cls.tracker_product,
            validate_regex=r'^\d+$',
        )

        # Used for testing removing issue from test case.
        cls.case_2_issue_manage_url = reverse('case-issue', args=[cls.case_2.pk])
        cls.case_2.add_issue('67890', cls.issue_tracker)
        cls.case_2.add_issue('78901', cls.issue_tracker)

    def setUp(self):
        self.login_tester()

    def tearDown(self):
        self.client.logout()
        remove_perm_from_user(self.tester, 'issuetracker.add_issue')
        remove_perm_from_user(self.tester, 'issuetracker.delete_issue')

    def test_bad_issue_key_to_remove(self):
        user_should_have_perm(self.tester, 'issuetracker.delete_issue')

        resp = self.client.get(self.issue_manage_url, data={
            'handle': 'remove',
            'issue_key': '',
            'case_run': self.case_run_1.pk,
        })

        self.assertEqual(http.client.BAD_REQUEST, resp.status_code)
        self.assertIn('Missing issue key to delete.', resp.json()['messages'])

    def test_bad_case_run_to_remove(self):
        user_should_have_perm(self.tester, 'issuetracker.delete_issue')

        resp = self.client.get(self.issue_manage_url, data={
            'handle': 'remove',
            # Whatever the issue key is, which does not impact this test.
            'issue_key': '123456',
            'case_run': 1000,
        })

        self.assertEqual(http.client.BAD_REQUEST, resp.status_code)
        self.assertIn('Test case run does not exists.', resp.json()['messages'])

    def test_bad_case_run_case_rel_to_remove(self):
        user_should_have_perm(self.tester, 'issuetracker.delete_issue')

        resp = self.client.get(self.issue_manage_url, data={
            'handle': 'remove',
            # Whatever the issue key is, which does not impact this test.
            'issue_key': '123456',
            'case_run': self.case_run_2.pk,
        })

        self.assertEqual(http.client.BAD_REQUEST, resp.status_code)
        self.assertIn(
            'Case run {} is not associated with case {}.'.format(
                self.case_run_2.pk, self.case_1.pk),
            resp.json()['messages'])

    def test_no_permission_to_add(self):
        # Note that, required permission is not granted by default. Hence, the
        # request should be forbidden.
        resp = self.client.get(self.issue_manage_url, data={
            'handle': 'add',
            # Whatever the issue key is, which does not impact this test.
            'issue_key': '123456',
            'tracker': self.issue_tracker.pk,
        })

        self.assertEqual(http.client.FORBIDDEN, resp.status_code)

    def test_no_permission_to_remove(self):
        # Note that, no permission is set for self.tester.
        resp = self.client.get(self.issue_manage_url, data={
            'handle': 'remove',
            # Whatever the issue key is, which does not impact this test.
            'issue_key': '123456',
            'case_run': self.case_run_1.pk,
        })

        self.assertEqual(http.client.FORBIDDEN, resp.status_code)

    def test_add_an_issue(self):
        user_should_have_perm(self.tester, 'issuetracker.add_issue')

        resp = self.client.get(self.issue_manage_url, data={
            'handle': 'add',
            'issue_key': '123456',
            'case': self.case_1.pk,
            'tracker': self.issue_tracker.pk,
        })

        self.assertEqual(200, resp.status_code)

        added_issue = Issue.objects.filter(
            issue_key='123456', case=self.case_1, case_run__isnull=True
        ).first()

        self.assertIsNotNone(added_issue)
        self.assertIn(added_issue.get_absolute_url(), resp.json()['html'])

    def test_remove_an_issue(self):
        user_should_have_perm(self.tester, 'issuetracker.delete_issue')

        # Assert later
        removed_issue_url = Issue.objects.filter(
            issue_key='67890', case=self.case_2, case_run__isnull=True
        ).first().get_absolute_url()

        resp = self.client.get(self.case_2_issue_manage_url, data={
            'handle': 'remove',
            'issue_key': '67890',
            'case': self.case_2.pk,
        })

        self.assertEqual(200, resp.status_code)

        removed_issue = Issue.objects.filter(
            issue_key='67890', case=self.case_2, case_run__isnull=True
        ).first()

        self.assertIsNone(removed_issue)
        self.assertNotIn(removed_issue_url, resp.json()['html'])

        # There were two issues added to self.case_2. This issue should be
        # still there after removing the above one.

        remained_issue = Issue.objects.filter(
            issue_key='78901', case=self.case_2, case_run__isnull=True
        ).first()

        self.assertIsNotNone(remained_issue)
        self.assertIn(remained_issue.get_absolute_url(), resp.json()['html'])

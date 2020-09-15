# -*- coding: utf-8 -*-

import unittest
from http import HTTPStatus

from django import test
from django.urls import reverse
from tcms.core.ajax import strip_parameters
from tests import factories as f
from tests import AuthMixin, HelperAssertions, user_should_have_perm


class TestStripParameters(unittest.TestCase):

    def setUp(self):
        self.request_dict = {
            'name__startswith': 'something',
            'info_type': 'tags',
            'format': 'ulli',
            'case__plan': 1,
            'field': 'tag__name',
        }
        self.internal_parameters = ('info_type', 'field', 'format')

    def test_remove_parameters_in_dict(self):
        simplified_dict = strip_parameters(self.request_dict, self.internal_parameters)
        for p in self.internal_parameters:
            self.assertFalse(p in simplified_dict)

        self.assertEqual('something', simplified_dict['name__startswith'])
        self.assertEqual(1, simplified_dict['case__plan'])

    def test_remove_parameters_not_in_dict(self):
        simplified_dict = strip_parameters(self.request_dict, ['non-existing-parameter'])
        self.assertEqual(self.request_dict, simplified_dict)


class TestUpdateCasesDefaultTester(AuthMixin, HelperAssertions, test.TestCase):
    """Test set default tester to selected cases"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.plan = f.TestPlanFactory(owner=cls.tester, author=cls.tester)
        cls.case_1 = f.TestCaseFactory(
            author=cls.tester, reviewer=cls.tester, default_tester=None,
            plan=[cls.plan])
        cls.case_2 = f.TestCaseFactory(
            author=cls.tester, reviewer=cls.tester, default_tester=None,
            plan=[cls.plan])

        user_should_have_perm(cls.tester, 'testcases.change_testcase')

        cls.user_1 = f.UserFactory(username='user1')
        cls.url = reverse('ajax-update-cases-default-tester')

    def test_set_default_tester(self):
        resp = self.client.post(self.url, data={
            'from_plan': self.plan.pk,
            'case': [self.case_1.pk, self.case_2.pk],
            'target_field': 'default_tester',
            'new_value': self.user_1.username,
        })

        self.assertJsonResponse(resp, {})

        for case in [self.case_1, self.case_2]:
            case.refresh_from_db()
            self.assertEqual(self.user_1, case.default_tester)

    def test_given_username_does_not_exist(self):
        resp = self.client.post(self.url, data={
            'from_plan': self.plan.pk,
            'case': [self.case_1.pk, self.case_2.pk],
            'target_field': 'default_tester',
            'new_value': 'unknown',
        })

        self.assertJsonResponse(
            resp,
            {
                'message': 'unknown cannot be set as a default tester, '
                           'since this user does not exist.'
            },
            status_code=HTTPStatus.NOT_FOUND
        )

        for case in [self.case_1, self.case_2]:
            case.refresh_from_db()
            self.assertIsNone(case.default_tester)

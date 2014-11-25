# -*- coding: utf-8 -*-
from xmlrpclib import Fault

from django.contrib.auth.models import User
from django_nose import FastFixtureTestCase

from tcms.xmlrpc.api import env
from tcms.management.models import (TCMSEnvGroup, TCMSEnvProperty,
                                    TCMSEnvValue, TCMSEnvGroupPropertyMap)


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


class TestGetENV(FastFixtureTestCase):
    fixtures = ['unittest.json']

    # TODO: need more testcases.
    def test_filter_groups(self):
        try:
            groups = env.filter_groups(None, {
                'id': 1,
                'name': 'hardware',
                'is_active': True,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNotNone(groups)
            self.assertEqual(groups[0]['name'], 'hardware')
            self.assertEqual(groups[0]['is_active'], True)
            self.assertEqual(groups[0]['id'], 1)

    def test_filter_properties(self):
        try:
            properties = env.filter_properties(None, {
                'name': 'cpu',
                'is_active': True,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNotNone(properties)
            self.assertEqual(properties[0]['name'], 'cpu')
            self.assertEqual(properties[0]['is_active'], True)

    def test_filter_values(self):
        try:
            values = env.filter_values(None, {
                'value': 'i3',
                'is_active': True,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNotNone(values)
            self.assertEqual(values[0]['value'], 'i3')
            self.assertEqual(values[0]['is_active'], True)

    def test_get_properties(self):
        try:
            properties = env.get_properties(None, env_group_id=1,
                                            is_active=True)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertFalse(properties)

    def test_get_values(self):
        try:
            values = env.get_values(None, env_property_id=1, is_active=True)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNotNone(values)
            self.assertEqual(len(values), 3)
            self.assertEqual(values[0]['value'], 'i3')
            self.assertEqual(values[1]['value'], 'i5')
            self.assertEqual(values[2]['value'], 'i7')


class TestENV(FastFixtureTestCase):
    def setUp(self):
        super(TestENV, self).setUp()
        self.user = User(username='tester')
        self.user.save()
        self.active_group = TCMSEnvGroup(name='ActiveGroup',
                                         manager=self.user,
                                         is_active=True)
        self.deactive_group = TCMSEnvGroup(name='DeactiveGroup',
                                           manager=self.user,
                                           is_active=False)

        self.aps = (TCMSEnvProperty(name='AP_1', is_active=True),
                    TCMSEnvProperty(name='AP_2', is_active=True),
                    TCMSEnvProperty(name='AP_3', is_active=True),)

        self.dps = (TCMSEnvProperty(name='DP_1', is_active=False),
                    TCMSEnvProperty(name='DP_2', is_active=False),
                    TCMSEnvProperty(name='DP_3', is_active=False),)

        self.active_group.save()
        self.deactive_group.save()
        for ap in self.aps:
            ap.save()
            TCMSEnvGroupPropertyMap(group=self.active_group, property=ap).save()
        for dp in self.dps:
            dp.save()
            TCMSEnvGroupPropertyMap(group=self.deactive_group,
                                    property=dp).save()

        values = (TCMSEnvValue(value='1', property=self.aps[0], is_active=True),
                  TCMSEnvValue(value='2', property=self.aps[0],
                               is_active=False))

        for value in values:
            value.save()

    def tearDown(self):
        super(TestENV, self).tearDown()

        for ap in self.aps:
            ap.delete()
        for dp in self.dps:
            dp.delete()

        self.active_group.delete()
        self.deactive_group.delete()

    def test_filter_active_groups(self):
        try:
            groups = env.filter_groups(None, {
                'is_active': True,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(groups[0]['name'], 'ActiveGroup')
            self.assertEqual(groups[0]['property'], [1, 2, 3])

    def test_filter_deactive_groups(self):
        try:
            groups = env.filter_groups(None, {
                'is_active': False,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(groups[0]['name'], 'DeactiveGroup')
            self.assertEqual(groups[0]['property'], [4, 5, 6])

    def test_filter_groups(self):
        try:
            env.filter_groups(None, {})
        except Fault as f:
            self.assertEqual(AssertMessage.SHOULD_BE_400, f.faultCode)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_filter_groups_with_non_exists(self):
        try:
            groups = env.filter_groups(None, {
                'id': 999
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertFalse(groups)

        try:
            groups = env.filter_groups(None, {
                'property': 999
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertFalse(groups)

    def test_filter_properties(self):
        try:
            properties = env.filter_properties(None, {
                'is_active': True,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNotNone(properties)
            self.assertEqual(len(properties), 3)
            self.assertEqual(properties[0]['name'], 'AP_1')
            self.assertEqual(properties[1]['name'], 'AP_2')
            self.assertEqual(properties[2]['name'], 'AP_3')

    def test_filter_properties_with_empty(self):
        try:
            env.filter_properties(None, {})
        except Fault as f:
            self.assertEqual(AssertMessage.SHOULD_BE_400, f.faultCode)
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_filter_properties_with_non_exists(self):
        try:
            properties = env.filter_properties(None, {
                'id': 999,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertFalse(properties)

        try:
            properties = env.filter_properties(None, {
                'group': 999,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertFalse(properties)

        try:
            properties = env.filter_properties(None, {
                'value': 999,
            })
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertFalse(properties)

    def test_get_properties(self):
        try:
            properties = env.get_properties(None)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(len(properties), 3)
            self.assertEqual(properties[0]['name'], 'AP_1')
            self.assertEqual(properties[1]['name'], 'AP_2')
            self.assertEqual(properties[2]['name'], 'AP_3')

    def test_get_properties_with_non_exists(self):
        try:
            properties = env.get_properties(None, env_group_id=999)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertFalse(properties)

    def test_get_values(self):
        try:
            values = env.get_values(None)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual(values[0]['value'], '1')

    def test_get_values_with_non_exists(self):
        try:
            values = env.get_values(None)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertFalse(values)

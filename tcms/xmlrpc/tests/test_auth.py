# -*- coding: utf-8 -*-
from xmlrpclib import Fault

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django_nose import FastFixtureTestCase

from tcms.xmlrpc.api import auth
from tcms.xmlrpc.tests.utils import make_session_request, make_http_request, \
    make_remote_request


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


class TestCheckUserName(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_check_user_name(self):
        try:
            retvalue = auth.check_user_name({
                'username': 'aaa',
                'password': 'bbb'
            })
        except Exception:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertEqual('aaa', retvalue[0])
            self.assertEqual('bbb', retvalue[1])

    def test_check_user_name_with_empty(self):
        try:
            auth.check_user_name({
                'password': 'bbb'
            })
        except PermissionDenied as e:
            self.assertEqual(str(e), 'Username and password is required')
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

        try:
            auth.check_user_name({
                'username': '',
                'password': 'bbb'
            })
        except PermissionDenied as e:
            self.assertEqual(str(e), 'Username and password is required')
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

        try:
            auth.check_user_name({
                'username': 'aaa',
            })
        except PermissionDenied as e:
            self.assertEqual(str(e), 'Username and password is required')
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

        try:
            auth.check_user_name({
                'username': 'aaa',
                'password': ''
            })
        except PermissionDenied as e:
            self.assertEqual(str(e), 'Username and password is required')
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)


class TestLoginAndLogout(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def setUp(self):
        super(TestLoginAndLogout, self).setUp()

        self.user = User.objects.create_user('test_user',
                                             'test_user@example.com',
                                             '123qwe')
        self.user.save()
        self.request = make_remote_request(make_session_request(
            make_http_request(self.user)))

        self.kerb_user = User.objects.create_user('test_user1',
                                                  'test_user1@example.com',
                                                  '123qwe')
        self.kerb_user.save()
        self.kerb_request = make_remote_request(make_session_request(
            make_http_request(self.kerb_user)))

    def tearDown(self):
        super(TestLoginAndLogout, self).tearDown()

        self.user.delete()
        self.kerb_user.delete()

    def test_login(self):
        try:
            session_key = auth.login(self.request, {'username': 'test_user',
                                                    'password': '123qwe'})
        except Fault as f:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNotNone(session_key)

    def test_login_with_wrong_password(self):
        try:
            auth.login(self.request, {'username': 'test_user',
                                      'password': '44444'})
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
            self.assertEqual(f.faultString, ['Wrong username or password'])
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_login_with_non_exist_user(self):
        try:
            auth.login(self.request, {'username': 'notexists',
                                      'password': '44444'})
        except Fault as f:
            self.assertEqual(f.faultCode, 403, AssertMessage.SHOULD_BE_403)
            self.assertEqual(f.faultString, ['Wrong username or password'])
        else:
            self.fail(AssertMessage.NOT_VALIDATE_ARGS)

    def test_logout(self):
        retval = auth.logout(self.request)
        self.assertEqual(retval, None)

    def test_login_kerb(self):
        try:
            session_key = auth.login_krbv(self.kerb_request)
            print session_key
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(session_key)

    def test_login_kerb_with_non_exist_user(self):
        try:
            self.kerb_request.META['REMOTE_USER'] = 'doesnotexist'
            session_key = auth.login_krbv(self.kerb_request)
        except Fault:
            self.fail(AssertMessage.UNEXCEPT_ERROR)
        else:
            self.assertIsNone(session_key)
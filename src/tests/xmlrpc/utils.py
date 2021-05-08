# -*- coding: utf-8 -*-

from http import HTTPStatus
from typing import Optional
from xmlrpc.client import Fault

from django import test
from django.contrib.auth.models import User

from tests import user_should_have_perm
from tests.factories import UserFactory


class XmlrpcAPIBaseTest(test.TestCase):
    """Base class for writing test case for XMLRPC functions"""

    # A string set to user in order to call function to test.
    permission = None

    @classmethod
    def setUpTestData(cls):
        cls.tester = UserFactory(username="tester", email="tester@example.com")
        cls.request = make_http_request(user=cls.tester, user_perm=cls.permission)

    def assertRaisesXmlrpcFault(self, faultCode, method, *args, **kwargs):
        assert callable(method)
        try:
            method(*args, **kwargs)
        except Fault as f:
            self.assertEqual(
                f.faultCode,
                faultCode,
                f"Except raising fault error with code {faultCode},"
                f" but {f.faultCode} is raised",
            )
        except Exception as e:
            self.fail(
                "Expect raising xmlrpclib.Fault, but {} is raised and "
                'message is "{}".'.format(e.__class__.__name__, str(e))
            )
        else:
            self.fail(
                "Expect to raise Fault error with faultCode {}, "
                "but no exception is raised.".format(faultCode)
            )

    def assertXmlrpcFaultNotFound(self, func, *args, **kwargs):
        self.assertRaisesXmlrpcFault(HTTPStatus.NOT_FOUND, func, *args, **kwargs)

    def assertXmlrpcFaultBadRequest(self, func, *args, **kwargs):
        self.assertRaisesXmlrpcFault(HTTPStatus.BAD_REQUEST, func, *args, **kwargs)

    def assertXmlrpcFaultForbidden(self, func, *args, **kwargs):
        self.assertRaisesXmlrpcFault(HTTPStatus.FORBIDDEN, func, *args, **kwargs)

    def assertXmlrpcFaultNotImplemented(self, func, *args, **kwargs):
        self.assertRaisesXmlrpcFault(HTTPStatus.NOT_IMPLEMENTED, func, *args, **kwargs)

    def assertXmlrpcFaultConflict(self, func, *args, **kwargs):
        self.assertRaisesXmlrpcFault(HTTPStatus.CONFLICT, func, *args, **kwargs)

    def assertXmlrpcFaultInternalServerError(self, func, *args, **kwargs):
        self.assertRaisesXmlrpcFault(HTTPStatus.INTERNAL_SERVER_ERROR, func, *args, **kwargs)


class FakeHTTPRequest:
    def __init__(self, user, data=None):
        self.user = user
        self.META = {}


def create_http_user():
    user, _ = User.objects.get_or_create(username="http_user", email="http_user@example.com")
    user.set_password(user.username)
    user.save()
    return user


def make_http_request(user: Optional[User] = None, user_perm: Optional[str] = None, data=None):
    """Factory method to make instance of FakeHTTPRequest

    :param user: a user bound to created fake HTTP request. That simulates a
        user requests an HTTP request. If omitted, a user will be created
        automatically.
    :type user: :class:`User <django.contrib.auth.models.User>`
    :param str user_perm: the permission user should have to perform the
        request. If omitted, no permission is set.
    :param data: not used at this moment.
    :return: a fake HTTP request object.
    :rtype: :class:`FakeHTTPRequest <tcms.xmlrpc.tests.utils.FakeHTTPRequest>`
    """
    _user = user
    if _user is None:
        _user = create_http_user()

    if user_perm is not None:
        user_should_have_perm(_user, user_perm)

    return FakeHTTPRequest(_user, data)

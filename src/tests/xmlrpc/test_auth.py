# -*- coding: utf-8 -*-

from unittest.mock import Mock

from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from tcms.xmlrpc.api import auth


class TestLoginWithModelBackend(TestCase):
    """Test auth.login with ModelBackend"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = User.objects.create_user(
            username="tester", email="tester@localhost", password="123"
        )

    def test_login(self):
        # ModelBackend is already configured in settings
        request = RequestFactory().post("/xmlrpc/")
        request.user = self.tester
        # Ensure request.session is set
        SessionMiddleware(Mock()).process_request(request)
        session_key = auth.login(request, {"username": "tester", "password": "123"})

        self.assertTrue(request.user.is_authenticated)
        self.assertGreater(len(session_key), 0)

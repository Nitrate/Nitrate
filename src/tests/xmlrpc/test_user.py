# -*- coding: utf-8 -*-

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

import tcms.xmlrpc.api.user as XUser
from tests import factories as f
from tests import user_should_have_perm
from tests.xmlrpc.utils import XmlrpcAPIBaseTest, make_http_request


class TestUserSerializer(TestCase):
    """Test User.get_user_dict"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory()
        cls.http_req = make_http_request(user=cls.user)

    def test_ensure_password_not_returned(self):
        data = XUser.get_user_dict(self.user)
        self.assertEqual(data["username"], self.user.username)
        self.assertEqual(data["email"], self.user.email)
        self.assertNotIn("password", data)


class TestUserFilter(TestCase):
    """Test User.filter"""

    @classmethod
    def setUpTestData(cls):
        cls.group_tester = f.GroupFactory()
        cls.group_reviewer = f.GroupFactory()

        cls.user1 = f.UserFactory(
            username="user 1",
            email="user1@exmaple.com",
            is_active=True,
            groups=[cls.group_tester],
        )
        cls.user2 = f.UserFactory(
            username="user 2",
            email="user2@example.com",
            is_active=False,
            groups=[cls.group_reviewer],
        )
        cls.user3 = f.UserFactory(
            username="user 3",
            email="user3@example.com",
            is_active=True,
            groups=[cls.group_reviewer],
        )

        cls.http_req = make_http_request()

    def test_normal_search(self):
        users = XUser.filter(self.http_req, {"email": "user2@example.com"})
        self.assertEqual(len(users), 1)
        user = users[0]
        self.assertEqual(user["id"], self.user2.pk)
        self.assertEqual(user["username"], self.user2.username)

        users = XUser.filter(
            self.http_req,
            {
                "pk__in": [self.user1.pk, self.user2.pk, self.user3.pk],
                "is_active": True,
            },
        )
        self.assertEqual(len(users), 2)

    def test_search_by_groups(self):
        users = XUser.filter(self.http_req, {"groups__name": self.group_reviewer.name})
        self.assertEqual(len(users), 2)


class TestUserGet(XmlrpcAPIBaseTest):
    """Test User.get"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory()
        cls.http_req = make_http_request(user=cls.user)

    def test_get(self):
        test_user = self.http_req.user
        data = XUser.get(self.http_req, test_user.pk)

        self.assertEqual(data["username"], test_user.username)
        self.assertEqual(data["id"], test_user.pk)
        self.assertEqual(data["first_name"], test_user.first_name)
        self.assertEqual(data["last_name"], test_user.last_name)
        self.assertEqual(data["email"], test_user.email)

    def test_get_not_exist(self):
        self.assertXmlrpcFaultNotFound(XUser.get, self.http_req, self.http_req.user.pk + 1)


class TestUserGetMe(TestCase):
    """Test User.get_me"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory()
        cls.http_req = make_http_request(user=cls.user)

    def test_get_me(self):
        test_user = self.http_req.user
        data = XUser.get_me(self.http_req)
        self.assertEqual(data["id"], test_user.pk)
        self.assertEqual(data["username"], test_user.username)


class TestUserJoin(XmlrpcAPIBaseTest):
    """Test User.join"""

    @classmethod
    def setUpTestData(cls):
        cls.http_req = make_http_request(user_perm="auth.change_user")
        cls.username = "test_username"
        cls.user = f.UserFactory(username=cls.username, email="username@example.com")
        cls.group_name = "test_group"
        cls.group = f.GroupFactory(name=cls.group_name)

    def test_join_normally(self):
        XUser.join(self.http_req, self.username, self.group_name)

        user = User.objects.get(username=self.username)
        user_added_to_group = user.groups.filter(name=self.group_name).exists()
        self.assertTrue(user_added_to_group, "User should be added to group.")

    def test_join_nonexistent_user(self):
        self.assertXmlrpcFaultNotFound(
            XUser.join, self.http_req, "nonexistent user", "whatever group name"
        )

    def test_join_nonexistent_group(self):
        self.assertXmlrpcFaultNotFound(
            XUser.join, self.http_req, self.username, "nonexistent group name"
        )


class TestUserUpdate(XmlrpcAPIBaseTest):
    """Test User.update"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="bob", email="bob@example.com")
        cls.user.set_password(cls.user.username)
        cls.user.save()

        cls.user_with_perm = User.objects.create(username="mike", email="mike@example.com")
        cls.user_with_perm.set_password(cls.user_with_perm.username)
        cls.user_with_perm.save()
        user_should_have_perm(cls.user_with_perm, "auth.change_user")

        cls.another_user = f.UserFactory()

        cls.user_new_attrs = {
            "first_name": "new first name",
            "last_name": "new last name",
            "email": "new email",
        }

    def test_update_myself(self):
        request = make_http_request(user=self.user)
        data = XUser.update(request, self.user_new_attrs, request.user.pk)
        user: User = User.objects.get(pk=request.user.pk)
        self.assertEqual(data["first_name"], user.first_name)
        self.assertEqual(data["last_name"], user.last_name)
        self.assertEqual(data["email"], user.email)

    def test_update_myself_without_passing_my_id(self):
        request = make_http_request(user=self.user)
        data = XUser.update(request, self.user_new_attrs)
        user: User = User.objects.get(pk=request.user.pk)
        self.assertEqual(data["first_name"], user.first_name)
        self.assertEqual(data["last_name"], user.last_name)
        self.assertEqual(data["email"], user.email)

    def test_cannot_update_other_user_without_permission(self):
        new_values = {"some_attr": "xxx"}
        request = make_http_request(user=self.user)
        self.assertXmlrpcFaultForbidden(XUser.update, request, new_values, self.another_user.pk)

    def test_update_other_with_proper_permission(self):
        request = make_http_request(user=self.user_with_perm)
        data = XUser.update(request, self.user_new_attrs, self.user.pk)
        user: User = User.objects.get(pk=self.user.pk)
        self.assertEqual(data["first_name"], user.first_name)
        self.assertEqual(data["last_name"], user.last_name)
        self.assertEqual(data["email"], user.email)

    def test_update_user_own_password_with_perm_set(self) -> None:
        user_new_attrs = self.user_new_attrs.copy()
        new_password = "new password"
        user_new_attrs["password"] = new_password

        request = make_http_request(user=self.user_with_perm)
        XUser.update(request, user_new_attrs)

        user: User = User.objects.get(pk=request.user.pk)
        self.assertTrue(user.check_password(new_password))

    def test_update_user_own_password_without_perm_set(self) -> None:
        user_new_attrs = self.user_new_attrs.copy()
        new_password = "new password"
        user_new_attrs["password"] = new_password
        user_new_attrs["old_password"] = self.user.username

        request = make_http_request(user=self.user)
        XUser.update(request, user_new_attrs)

        user: User = User.objects.get(pk=request.user.pk)
        self.assertTrue(user.check_password(new_password))

    def test_do_nothing(self):
        original_user = self.user
        request = make_http_request(user=self.user)
        XUser.update(request)
        updated_user = User.objects.get(pk=request.user.pk)
        self.assertEqual(original_user.first_name, updated_user.first_name)
        self.assertEqual(original_user.last_name, updated_user.last_name)
        self.assertEqual(original_user.email, updated_user.email)
        self.assertEqual(original_user.password, updated_user.password)


class TestGetUserDict(TestCase):
    """Test get_user_dict"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = f.UserFactory(username="tester")
        cls.tester.set_password("security password")
        cls.tester.save()

    def test_get_dict(self):
        user = User.objects.get(username="tester")
        result = XUser.get_user_dict(user)

        self.assertEqual(user.pk, result["id"])
        self.assertEqual(user.username, result["username"])
        self.assertEqual(user.email, result["email"])
        self.assertTrue(result["is_active"])
        self.assertFalse(result["is_staff"])
        self.assertFalse(result["is_superuser"])

    @patch("tcms.xmlrpc.api.user.XMLRPCSerializer.serialize_model")
    def test_no_password_is_in_serialized_result(self, serialize_model):
        expected = {
            "id": 1,
            "username": "tester",
        }
        serialize_model.return_value = expected

        user = User.objects.get(username="tester")
        self.assertEqual(expected, XUser.get_user_dict(user))

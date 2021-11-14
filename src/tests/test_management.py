# -*- coding: utf-8 -*-

from http import HTTPStatus
from unittest.mock import patch

from django import test
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.test.client import Client
from django.urls import reverse
from pytest_django.asserts import assertContains

from tcms.logs.models import TCMSLogModel
from tcms.management.models import (
    Component,
    Product,
    TCMSEnvGroup,
    TCMSEnvGroupPropertyMap,
    TCMSEnvProperty,
    TCMSEnvValue,
    Version,
)
from tcms.testplans.models import TestPlan, _disconnect_signals, _listen
from tests import AuthMixin, BaseDataContext, HelperAssertions
from tests import factories as f
from tests import remove_perm_from_user, user_should_have_perm


class TestVisitAndSearchGroupPage(TestCase):
    """Test case for opening group page"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.group_url = reverse("management-env-groups")

        cls.new_tester = User.objects.create_user(
            username="new-tester", email="new-tester@example.com", password="password"
        )

        cls.group_1 = f.TCMSEnvGroupFactory(name="rhel-7", manager=cls.new_tester, modified_by=None)
        cls.group_2 = f.TCMSEnvGroupFactory(name="fedora", manager=cls.new_tester, modified_by=None)

        cls.group_1.log_action(
            who=cls.new_tester,
            field="",
            original_value="",
            new_value=f"Add group {cls.group_1.name}",
        )

        cls.group_1.log_action(
            who=cls.new_tester,
            field="",
            original_value="",
            new_value=f"Edit group {cls.group_1.name}",
        )

        cls.group_2.log_action(
            who=cls.new_tester,
            field="",
            original_value="",
            new_value=f"Edit group {cls.group_2.name}",
        )

        cls.property_1 = f.TCMSEnvPropertyFactory()
        cls.property_2 = f.TCMSEnvPropertyFactory()
        cls.property_3 = f.TCMSEnvPropertyFactory()

        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_1, property=cls.property_1)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_1, property=cls.property_2)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_1, property=cls.property_3)

        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_2, property=cls.property_1)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_2, property=cls.property_3)

    def tearDown(self):
        remove_perm_from_user(self.new_tester, "management.change_tcmsenvgroup")

    def assert_group_logs_are_displayed(self, response, group):
        env_group_ct = ContentType.objects.get_for_model(TCMSEnvGroup)
        logs = TCMSLogModel.objects.filter(content_type=env_group_ct, object_pk=group.pk)

        for log in logs:
            self.assertContains(response, f"<td>{log.who.username}</td>", html=True)
            self.assertContains(response, f"<td>{log.new_value}</td>", html=True)

    def test_visit_group_page(self):
        response = self.client.get(self.group_url)

        for group in (self.group_1, self.group_2):
            self.assertContains(response, f'<label class=" ">{group.name}</label>', html=True)

            self.assert_group_logs_are_displayed(response, group)

    # def test_visit_group_page_with_permission(self):
    #     self.client.login(username=self.new_tester.username, password='password')
    #
    #     user_should_have_perm(self.new_tester, 'management.change_tcmsenvgroup')
    #     group_edit_url = reverse('management-env-group-edit')
    #
    #     response = self.client.get(self.group_url)
    #
    #     for group in (self.group_1, self.group_2):
    #         self.assertContains(
    #             response,
    #             '<a href="{}?id={}">{}</a>'.format(group_edit_url,
    #                                                group.pk,
    #                                                group.name),
    #             html=True)

    def test_search_groups(self):
        response = self.client.get(self.group_url, {"name": "el"})

        self.assertContains(response, f'<label class=" ">{self.group_1.name}</label>', html=True)
        self.assertNotContains(response, f'<label class=" ">{self.group_2.name}</label>', html=True)


class TestAddGroup(AuthMixin, HelperAssertions, TestCase):
    """Test case for adding a group"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.group_add_url = reverse("management-add-env-group")

        cls.tester = User.objects.create_user(
            username="new-tester", email="new-tester@example.com", password="password"
        )
        cls.new_group_name = "nitrate-dev"

        cls.permission = "management.add_tcmsenvgroup"
        user_should_have_perm(cls.tester, cls.permission)

    def test_missing_permission(self):
        remove_perm_from_user(self.tester, self.permission)

        response = self.client.post(self.group_add_url, {"name": self.new_group_name})
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_code)

    def test_missing_group_name(self):
        response = self.client.post(self.group_add_url, {})
        self.assertJsonResponse(
            response,
            {"message": "Environment group name is required."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

        response = self.client.post(self.group_add_url, {"name": ""})
        self.assertJsonResponse(
            response,
            {"message": "Environment group name is required."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_add_a_new_group(self):
        response = self.client.post(self.group_add_url, {"name": self.new_group_name})

        groups = TCMSEnvGroup.objects.filter(name=self.new_group_name)
        self.assertEqual(1, groups.count())

        new_group = groups[0]

        self.assertEqual(self.tester, new_group.manager)
        self.assertJsonResponse(response, {"env_group_id": new_group.pk})

        # Assert log is created for new group
        env_group_ct = ContentType.objects.get_for_model(TCMSEnvGroup)
        log = TCMSLogModel.objects.filter(content_type=env_group_ct, object_pk=new_group.pk)[0]
        self.assertEqual(f"Initial env group {self.new_group_name}", log.new_value)

    def test_add_existing_group(self):
        self.client.post(self.group_add_url, {"name": self.new_group_name})

        response = self.client.post(self.group_add_url, {"name": self.new_group_name})
        self.assertJsonResponse(
            response,
            {
                "message": f'Environment group name "{self.new_group_name}" '
                f"already exists, please choose another name."
            },
            status_code=HTTPStatus.BAD_REQUEST,
        )


class TestDeleteGroup(AuthMixin, HelperAssertions, TestCase):
    """Test case for deleting a group"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = "management.delete_tcmsenvgroup"

        cls.group_manager = User.objects.create_user(
            username="group-manager", email="manager@example.com", password="password"
        )

        cls.group_nitrate = f.TCMSEnvGroupFactory(name="nitrate", manager=cls.group_manager)
        cls.group_fedora = f.TCMSEnvGroupFactory(name="fedora", manager=cls.group_manager)

    def tearDown(self):
        remove_perm_from_user(self.tester, self.permission)

    def test_manager_is_able_to_delete_without_requiring_permission(self):
        self.client.login(username=self.group_manager.username, password="password")

        url = reverse("management-delete-env-group", args=[self.group_nitrate.pk])
        response = self.client.post(url)

        self.assertJsonResponse(response, {"env_group_id": self.group_nitrate.pk})
        self.assertFalse(TCMSEnvGroup.objects.filter(pk=self.group_nitrate.pk).exists())

    def test_missing_permission_when_delete_by_non_manager(self):
        url = reverse("management-delete-env-group", args=[self.group_nitrate.pk])
        response = self.client.post(url)
        self.assert403(response)

    def test_delete_group_by_non_manager(self):
        user_should_have_perm(self.tester, self.permission)

        url = reverse("management-delete-env-group", args=[self.group_fedora.pk])
        response = self.client.post(url)

        self.assertJsonResponse(response, {"env_group_id": self.group_fedora.pk})
        self.assertFalse(TCMSEnvGroup.objects.filter(pk=self.group_fedora.pk).exists())

    def test_return_404_if_delete_a_nonexisting_group(self):
        url = reverse("management-delete-env-group", args=[9999999999])
        response = self.client.post(url)
        self.assert404(response)


class TestSetGroupStatus(AuthMixin, HelperAssertions, TestCase):
    """Test enable and disable an environment group"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.group_nitrate = f.TCMSEnvGroupFactory(name="nitrate", manager=cls.tester)

        cls.permission = "management.change_tcmsenvgroup"
        cls.set_status_url = reverse("management-set-env-group-status", args=[cls.group_nitrate.pk])

    def tearDown(self):
        remove_perm_from_user(self.tester, self.permission)

    def test_refuse_when_missing_permission(self):
        response = self.client.post(self.set_status_url, {"status": 0})
        self.assert403(response)

    def test_missing_status(self):
        user_should_have_perm(self.tester, self.permission)

        response = self.client.post(self.set_status_url)
        self.assertJsonResponse(
            response,
            {"message": "Environment group status is missing."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_refuse_invalid_status_value(self):
        user_should_have_perm(self.tester, self.permission)

        # Status value is not valid as long as it's not 0 or 1.
        for status in ("true", "false", "yes", "no", "2"):
            response = self.client.post(self.set_status_url, {"status": status})
            self.assertJsonResponse(
                response,
                {"message": f'Environment group status "{status}" is invalid.'},
                status_code=HTTPStatus.BAD_REQUEST,
            )

    def test_404_if_group_pk_not_exist(self):
        user_should_have_perm(self.tester, self.permission)

        url = reverse("management-set-env-group-status", args=[999999999])
        response = self.client.post(url, {"status": 1})
        self.assert404(response)

    def test_disable_a_group(self):
        user_should_have_perm(self.tester, self.permission)

        self.client.post(self.set_status_url, {"status": 0})

        group = TCMSEnvGroup.objects.get(pk=self.group_nitrate.pk)
        self.assertFalse(group.is_active)

    def test_enable_a_group(self):
        user_should_have_perm(self.tester, self.permission)

        self.client.post(self.set_status_url, {"status": 1})

        group = TCMSEnvGroup.objects.get(pk=self.group_nitrate.pk)
        self.assertTrue(group.is_active)


#
#
# class TestVisitEnvironmentGroupPage(HelperAssertions, TestCase):
#     """Test case for visiting environment group page"""
#
#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()
#
#         cls.tester = User.objects.create_user(username='tester',
#                                               email='tester@example.com',
#                                               password='password')
#         user_should_have_perm(cls.tester, 'management.change_tcmsenvgroup')
#
#         cls.group_edit_url = reverse('management-env-group-edit')
#         cls.group_nitrate = f.TCMSEnvGroupFactory(
#             name='nitrate', manager=cls.tester)
#         cls.disabled_group = f.TCMSEnvGroupFactory(
#             name='disabled-group', is_active=False, manager=cls.tester)
#
#     # def test_404_when_missing_group_id(self):
#     #     self.client.login(username=self.tester.username, password='password')
#     #     response = self.client.get(self.group_edit_url)
#     #     self.assert404(response)
#
#     def test_404_if_group_id_not_exist(self):
#         self.client.login(username=self.tester.username, password='password')
#         response = self.client.get(self.group_edit_url, {'id': 9999999})
#         self.assert404(response)
#
#     def test_visit_a_group(self):
#         self.client.login(username=self.tester.username, password='password')
#
#         response = self.client.get(self.group_edit_url, {'id': self.group_nitrate.pk})
#
#         self.assertContains(
#             response,
#             f'<input name="name" value="{self.group_nitrate.name}" type="text">',
#             html=True)
#
#         self.assertContains(
#             response,
#             '<input name="enabled" type="checkbox" checked>',
#             html=True)
#
#     def test_visit_disabled_group(self):
#         self.client.login(username=self.tester.username, password='password')
#
#         response = self.client.get(self.group_edit_url, {'id': self.disabled_group.pk})
#
#         self.assertContains(
#             response,
#             f'<input name="name" value="{self.disabled_group.name}" type="text">',
#             html=True)
#
#         self.assertContains(
#             response,
#             '<input name="enabled" type="checkbox">',
#             html=True)


class TestEditGroup(AuthMixin, TestCase):
    """Test case for editing environment group"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user_should_have_perm(cls.tester, "management.change_tcmsenvgroup")

        cls.group_nitrate = f.TCMSEnvGroupFactory(name="nitrate", manager=cls.tester)
        cls.group_db = f.TCMSEnvGroupFactory(name="db", is_active=False, manager=cls.tester)
        cls.duplicate_group = f.TCMSEnvGroupFactory(name="fedora", manager=cls.tester)

        cls.property_1 = f.TCMSEnvPropertyFactory()
        cls.property_2 = f.TCMSEnvPropertyFactory()
        cls.property_3 = f.TCMSEnvPropertyFactory()

    def test_refuse_if_there_is_duplicate_group_name(self):
        url = reverse("management-env-group-edit", args=[self.group_nitrate.pk])
        response = self.client.post(
            url,
            {
                "name": self.duplicate_group.name,
                "enable": "on",
            },
        )

        self.assertContains(response, "Duplicated name already exists")

    def test_show_edit_page(self):
        url = reverse("management-env-group-edit", args=[self.group_nitrate.pk])
        response = self.client.get(url)

        self.assertContains(
            response,
            f'<input type="text" name="name" value="{self.group_nitrate.name}">',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="checkbox" id="enable-group" name="enabled" checked>',
            html=True,
        )

    def test_edit_group(self):
        new_group_name = "nitrate-dev"
        url = reverse("management-env-group-edit", args=[self.group_nitrate.pk])
        self.client.post(
            url,
            {
                "name": new_group_name,
                "enabled": "on",
                "selected_property_ids": [self.property_1.pk, self.property_2.pk],
            },
        )

        group = TCMSEnvGroup.objects.get(pk=self.group_nitrate.pk)
        self.assertEqual(new_group_name, group.name)
        self.assertTrue(group.is_active)
        self.assertTrue(
            TCMSEnvGroupPropertyMap.objects.filter(
                group_id=self.group_nitrate.pk, property_id=self.property_1.pk
            ).exists()
        )
        self.assertTrue(
            TCMSEnvGroupPropertyMap.objects.filter(
                group_id=self.group_nitrate.pk, property_id=self.property_2.pk
            ).exists()
        )

    def test_disable_group(self):
        url = reverse("management-env-group-edit", args=[self.group_nitrate.pk])
        # For disable, enable is not in the post data
        self.client.post(
            url,
            {
                "name": "new name",
                "selected_property_ids": [self.property_1.pk, self.property_2.pk],
            },
        )

        self.assertFalse(TCMSEnvGroup.objects.get(pk=self.group_nitrate.pk).is_active)

    def test_enable_group(self):
        self.group_db.is_active = False
        self.group_db.save()

        url = reverse("management-env-group-edit", args=[self.group_db.pk])
        self.client.post(
            url,
            {
                "name": "new name",
                "enabled": "on",
            },
        )

        self.assertTrue(TCMSEnvGroup.objects.get(pk=self.group_db.pk).is_active)

    @patch("tcms.management.views.TCMSEnvGroup.log_action")
    def test_do_not_update_name_if_no_change(self, log_action):
        url = reverse("management-env-group-edit", args=[self.group_db.pk])
        self.client.post(
            url,
            {
                "name": self.group_db.name,
                # enabled is not set in order to make log_action is not called for
                # changing is_active
            },
        )

        log_action.assert_not_called()


class TestAddProperty(AuthMixin, HelperAssertions, TestCase):
    """Test case for adding properties to a group"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = "management.add_tcmsenvproperty"
        cls.add_group_property_url = reverse("management-add-env-property")

        cls.group_nitrate = f.TCMSEnvGroupFactory(name="nitrate", manager=cls.tester)
        cls.duplicate_property = f.TCMSEnvPropertyFactory(name="f26")

    def setUp(self):
        super().setUp()
        user_should_have_perm(self.tester, self.permission)

    def test_refuse_if_missing_permission(self):
        remove_perm_from_user(self.tester, self.permission)

        response = self.client.post(self.add_group_property_url, {})
        self.assert403(response)

    def test_refuse_if_missing_property_name(self):
        response = self.client.post(self.add_group_property_url, {})
        self.assertJsonResponse(
            response,
            {"message": "Property name is missing."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

        response = self.client.post(self.add_group_property_url, {"name": ""})
        self.assertJsonResponse(
            response,
            {"message": "Property name is missing."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_refuse_to_create_duplicate_property(self):
        duplicate_name = self.duplicate_property.name
        response = self.client.post(
            self.add_group_property_url,
            {
                "name": duplicate_name,
            },
        )

        self.assertJsonResponse(
            response,
            {
                "message": f"Environment property {duplicate_name} already "
                f"exists, please choose another name."
            },
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_add_new_property(self):
        new_property_name = "f24"
        request_data = {
            "action": "add",
            "name": new_property_name,
        }

        response = self.client.post(self.add_group_property_url, request_data)

        new_property = TCMSEnvProperty.objects.filter(name=new_property_name).first()
        self.assertIsNotNone(new_property)
        self.assertJsonResponse(response, {"id": new_property.pk, "name": new_property.name})


class TestEditProperty(AuthMixin, HelperAssertions, TestCase):
    """Test case for editing a property"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = "management.change_tcmsenvproperty"

        cls.property = f.TCMSEnvPropertyFactory(name="f26")
        cls.property_edit_url = reverse("management-edit-env-property", args=[cls.property.pk])

    def setUp(self):
        super().setUp()
        user_should_have_perm(self.tester, self.permission)

    def test_refuse_if_missing_permission(self):
        remove_perm_from_user(self.tester, self.permission)

        response = self.client.post(self.property_edit_url)
        self.assert403(response)

    def test_refuse_if_property_id_not_exist(self):
        property_id = 999999999
        response = self.client.post(reverse("management-edit-env-property", args=[property_id]))

        self.assertJsonResponse(
            response,
            {"message": f"Environment property with id {property_id} " f"does not exist."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_edit_a_property(self):
        new_property_name = "fedora-24"
        response = self.client.post(self.property_edit_url, {"name": new_property_name})

        env_property = TCMSEnvProperty.objects.get(pk=self.property.pk)
        self.assertEqual(new_property_name, env_property.name)
        self.assertJsonResponse(response, {"id": env_property.pk, "name": env_property.name})


class TestEnableDisableProperty(AuthMixin, HelperAssertions, TestCase):
    """Test enable and disable a property"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = "management.change_tcmsenvproperty"
        cls.set_status_url = reverse("management-set-env-property-status")

        cls.group_nitrate = f.TCMSEnvGroupFactory(name="nitrate")

        cls.property_os = f.TCMSEnvPropertyFactory(name="OS")
        cls.property_lang = f.TCMSEnvPropertyFactory(name="lang")
        cls.disabled_property_1 = f.TCMSEnvPropertyFactory(
            name="disabled-property-1", is_active=False
        )
        cls.disabled_property_2 = f.TCMSEnvPropertyFactory(
            name="disabled-property-2", is_active=False
        )

        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_nitrate, property=cls.property_os)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_nitrate, property=cls.property_lang)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_nitrate, property=cls.disabled_property_1)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_nitrate, property=cls.disabled_property_2)

    def setUp(self):
        super().setUp()
        user_should_have_perm(self.tester, self.permission)

    def test_refuse_if_missing_permission(self):
        remove_perm_from_user(self.tester, self.permission)

        response = self.client.post(self.set_status_url, {"id": self.property_os.pk})
        self.assert403(response)

    def test_refuse_if_status_is_illegal(self):
        for illegal_status in ("yes", "no", "2", "-1"):
            response = self.client.post(
                self.set_status_url,
                {
                    "id": [self.property_os.pk, self.property_lang.pk],
                    "status": illegal_status,
                },
            )

            self.assertJsonResponse(
                response,
                {"message": f"Invalid status {illegal_status}."},
                status_code=HTTPStatus.BAD_REQUEST,
            )

            self.assertTrue(
                TCMSEnvGroupPropertyMap.objects.filter(
                    group=self.group_nitrate, property=self.property_os
                ).exists()
            )

            self.assertTrue(
                TCMSEnvGroupPropertyMap.objects.filter(
                    group=self.group_nitrate, property=self.property_lang
                ).exists()
            )

    def test_enable_a_property(self):
        property_ids = [self.disabled_property_1.pk, self.disabled_property_2.pk]
        response = self.client.post(self.set_status_url, {"id": property_ids, "status": 1})

        self.assertJsonResponse(response, {"property_ids": property_ids})

        self.assertTrue(TCMSEnvProperty.objects.get(pk=self.disabled_property_1.pk).is_active)
        self.assertTrue(TCMSEnvProperty.objects.get(pk=self.disabled_property_2.pk).is_active)

    def test_disable_a_property(self):
        property_ids = [self.property_os.pk, self.property_lang.pk]
        response = self.client.post(self.set_status_url, {"id": property_ids, "status": 0})

        self.assertJsonResponse(response, {"property_ids": property_ids})

        self.assertFalse(TCMSEnvProperty.objects.get(pk=self.property_os.pk).is_active)
        self.assertFalse(TCMSEnvProperty.objects.get(pk=self.property_lang.pk).is_active)

        self.assertFalse(
            TCMSEnvGroupPropertyMap.objects.filter(
                group=self.group_nitrate, property=self.property_os
            ).exists()
        )
        self.assertFalse(
            TCMSEnvGroupPropertyMap.objects.filter(
                group=self.group_nitrate, property=self.property_lang
            ).exists()
        )

    def test_missing_status(self):
        response = self.client.post(self.set_status_url, {"id": [1, 2]})
        self.assertJsonResponse(
            response, {"message": "Missing status."}, status_code=HTTPStatus.BAD_REQUEST
        )

    def test_missing_property_ids(self):
        response = self.client.post(self.set_status_url, {"status": 0})
        self.assertJsonResponse(
            response,
            {"message": "Missing environment property ids. Nothing changed."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_some_property_ids_are_invalid(self):
        for invalid_ids in ([1, 2, "a", "xx"], (1, "x", 3, 4)):
            response = self.client.post(
                self.set_status_url,
                {
                    "id": invalid_ids,
                    "status": 0,
                },
            )
            self.assert400(response)


class TestEnvironmentPropertiesView(HelperAssertions, TestCase):
    """Test environment properties list view"""

    def test_show_properties(self):
        response = self.client.get(reverse("management-env-properties"))
        self.assert200(response)


class TestEnvironmentPropertyValuesListView(HelperAssertions, TestCase):
    """Test environment property values list view"""

    @classmethod
    def setUpTestData(cls):
        cls.property_py = f.TCMSEnvPropertyFactory(name="python")
        cls.py36 = f.TCMSEnvValueFactory(value="3.6", property=cls.property_py)
        cls.py37 = f.TCMSEnvValueFactory(value="3.7", property=cls.property_py)

    def test_404_if_property_id_does_not_exist(self):
        response = self.client.get(reverse("management-env-properties-values", args=[99999]))
        self.assert404(response)

    def test_list_property_values(self):
        response = self.client.get(
            reverse("management-env-properties-values", args=[self.property_py.pk])
        )

        content = (
            f'<input type="checkbox" name="id" '
            f'id="property_value_{self.py36.pk}" value="{self.py36.pk}">',
            f'<input type="checkbox" name="id" '
            f'id="property_value_{self.py37.pk}" value="{self.py37.pk}">',
        )
        for html in content:
            self.assertContains(response, html, html=True)


class TestEnvironmentPropertyValuesAddView(AuthMixin, TestCase):
    """Test add property values"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.property_py = f.TCMSEnvPropertyFactory(name="python")
        cls.property_db = f.TCMSEnvPropertyFactory(name="db")
        f.TCMSEnvValueFactory(value="mysql", property=cls.property_db)

        user_should_have_perm(cls.tester, "management.add_tcmsenvvalue")

    def test_property_id_does_not_exist(self):
        url = reverse("management-add-env-property-values", args=[9999])
        response = self.client.post(url)
        self.assertContains(response, "not exist", status_code=HTTPStatus.NOT_FOUND)

    def test_add_values(self):
        url = reverse("management-add-env-property-values", args=[self.property_py.pk])
        values_to_add = ["3.6", "3.7"]
        response = self.client.post(url, {"value": values_to_add})

        values = self.property_py.value.values_list("value", flat=True)
        self.assertListEqual(values_to_add, sorted(values))

        for item in self.property_py.value.all():
            self.assertContains(
                response,
                f'<input type="checkbox" name="id" '
                f'id="property_value_{item.pk}" value="{item.pk}"/>',
                html=True,
            )

    def test_add_diff_values(self):
        url = reverse("management-add-env-property-values", args=[self.property_db.pk])
        values_to_add = ["mariadb", "mysql", "postgresql"]
        self.client.post(url, {"value": values_to_add})

        values = self.property_db.value.values_list("value", flat=True)
        self.assertListEqual(values_to_add, sorted(values))


class TestEnvironmentPropertyValuesSetStatusView(AuthMixin, HelperAssertions, TestCase):
    """Test set status for environment property values"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, "management.change_tcmsenvvalue")
        cls.set_status_url = reverse("management-set-env-property-values-status")

        cls.property_db = f.TCMSEnvPropertyFactory(name="db")
        cls.value_mysql = f.TCMSEnvValueFactory(
            value="mysql", is_active=False, property=cls.property_db
        )
        cls.value_pgsql = f.TCMSEnvValueFactory(
            value="pgsql", is_active=False, property=cls.property_db
        )
        cls.value_mariadb = f.TCMSEnvValueFactory(value="mariadb", property=cls.property_db)

    def test_missing_value_ids(self):
        response = self.client.post(self.set_status_url)
        self.assertContains(
            response, "Property value id is missing", status_code=HTTPStatus.BAD_REQUEST
        )

    def test_some_value_ids_are_not_valid_number(self):
        response = self.client.post(self.set_status_url, {"id": [1, 2, "x"]})
        self.assertContains(
            response, "Value id x is not an integer", status_code=HTTPStatus.BAD_REQUEST
        )

    def test_missing_status(self):
        response = self.client.post(self.set_status_url, {"id": [1, 2]})
        self.assertContains(response, "Status is missing", status_code=HTTPStatus.BAD_REQUEST)

    def test_invalid_status(self):
        response = self.client.post(self.set_status_url, {"id": [1, 2], "status": "x"})
        self.assertContains(response, "Status x is invalid", status_code=HTTPStatus.BAD_REQUEST)

    def test_enable_values(self):
        response = self.client.post(
            self.set_status_url,
            {
                # Server side will ignore the empty one
                "id": [self.value_mysql.pk, self.value_pgsql.pk, ""],
                "status": 1,
            },
        )

        for v in (self.value_mysql, self.value_pgsql):
            self.assertContains(response, f'<span id="id_value_{v.pk}">{v.value}</span>', html=True)
            self.assertTrue(TCMSEnvValue.objects.get(pk=v.pk).is_active)

    def test_disable_values(self):
        response = self.client.post(
            self.set_status_url, {"id": [self.value_mariadb.pk], "status": 0}
        )

        v = self.value_mariadb
        self.assertContains(
            response,
            f'<span id="id_value_{v.pk}" class="line-through">{v.value}</span>',
            html=True,
        )
        self.assertFalse(TCMSEnvValue.objects.get(pk=v.pk).is_active)


class TestEnvironmentPropertyValueEditView(AuthMixin, TestCase):
    """Test edit environment property value"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, "management.change_tcmsenvvalue")

        cls.property_db = f.TCMSEnvPropertyFactory(name="db")
        cls.property_value = f.TCMSEnvValueFactory(value="mysql", property=cls.property_db)

        cls.edit_url = reverse("management-env-property-value-edit", args=[cls.property_value.pk])

    def test_missing_new_value(self):
        response = self.client.post(self.edit_url)
        self.assertContains(
            response, "Missing new value to update", status_code=HTTPStatus.BAD_REQUEST
        )

    def test_empty_new_value_content(self):
        response = self.client.post(self.edit_url, {"value": ""})
        self.assertContains(response, "The value is empty", status_code=HTTPStatus.BAD_REQUEST)

    def test_property_value_does_not_exist(self):
        url = reverse("management-env-property-value-edit", args=[999])
        response = self.client.post(url, {"value": "pgsql"})
        self.assertContains(
            response,
            "Property value id 999 does not exist",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_change_value(self):
        response = self.client.post(self.edit_url, {"value": "mariadb"})

        value = TCMSEnvValue.objects.get(pk=self.property_value.pk)
        self.assertEqual("mariadb", value.value)

        self.assertContains(
            response, f'<span id="id_value_{value.pk}">{value.value}</span>', html=True
        )


class TestDeleteProduct(HelperAssertions, test.TestCase):
    """Test deleting a product which has plans"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory(username="admin", email="admin@example.com")
        cls.user.set_password("admin")
        cls.user.is_superuser = True
        cls.user.is_staff = True  # enables access to admin panel
        cls.user.save()

        cls.c = Client()
        cls.c.login(username="admin", password="admin")

    def setUp(self):
        super().setUp()
        _listen()

    def tearDown(self):
        _disconnect_signals()
        super().tearDown()

    def test_product_delete_with_test_plan_wo_email_settings(self):
        """
        A test to demonstrate Issue #181.

        Steps to reproduce:
        1) Create a new Product
        2) Create a new Test Plan for Product
        3) DON'T edit the Test Plan
        4) Delete the Product

        Expected results:
        0) No errors
        1) Product is deleted
        2) Test Plan is deleted

        NOTE: we manually connect signals handlers here
        b/c in est mode LISTENING_MODEL_SIGNAL = False
        """
        # setup
        product = f.ProductFactory(name="Something to delete")
        product_version = f.VersionFactory(value="0.1", product=product)
        plan_type = f.TestPlanTypeFactory()

        # create Test Plan via the UI by sending a POST request to the view
        previous_plans_count = TestPlan.objects.count()
        test_plan_name = "Test plan for the new product"
        response = self.c.post(
            reverse("plans-new"),
            {
                "name": test_plan_name,
                "product": product.pk,
                "product_version": product_version.pk,
                "type": plan_type.pk,
            },
            follow=True,
        )
        self.assert200(response)
        # verify test plan was created
        self.assertContains(response, test_plan_name)
        self.assertEqual(previous_plans_count + 1, TestPlan.objects.count())

        the_new_plan = list(TestPlan.objects.order_by("pk"))[-1]

        # now delete the product
        admin_delete_url = "admin:{}_{}_delete".format(
            product._meta.app_label, product._meta.model_name
        )
        location = reverse(admin_delete_url, args=[product.pk])
        response = self.c.get(location)
        self.assert200(response)
        self.assertContains(
            response, 'Are you sure you want to delete the product "%s"' % product.name
        )
        self.assertContains(response, "Yes, I'm sure")

        # confirm that we're sure we want to delete it
        response = self.c.post(location, {"post": "yes"})
        self.assert302(response)
        self.assertIn(
            "/admin/{}/{}/".format(product._meta.app_label, product._meta.model_name),
            response["Location"],
        )

        # verify everything has been deleted
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertFalse(Version.objects.filter(pk=product_version.pk).exists())
        self.assertEqual(previous_plans_count, TestPlan.objects.count())
        from tcms.testplans.models import TestPlanEmailSettings

        self.assertFalse(TestPlanEmailSettings.objects.filter(plan=the_new_plan).exists())


def test_component_admin_changelist(tester, base_data: BaseDataContext, client):
    """Test custom ComponentAdmin.get_queryset works well"""
    admin = User.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )
    admin.set_password("admin")
    admin.save()
    client.login(username="admin", password="admin")
    Component.objects.create(name="db", product=base_data.product, initial_owner=tester)
    Component.objects.create(name="web", product=base_data.product, initial_owner=tester)
    Component.objects.create(name="docs", product=base_data.product, initial_owner=tester)
    response = client.get(reverse("admin:management_component_changelist"))
    assertContains(response, "db")
    assertContains(response, "web")
    assertContains(response, "docs")

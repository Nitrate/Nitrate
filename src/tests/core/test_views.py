# -*- coding: utf-8 -*-

import json
from http import HTTPStatus
from typing import List

import pytest
from django import test
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import ValidationError
from django.urls import reverse
from kobo.django.xmlrpc.models import XmlRpcLog
from pytest_django import asserts

from tcms.core.forms import DurationField, ModelChoiceField, MultipleEmailField, UserField
from tcms.core.templatetags.report_tags import percentage
from tcms.management.models import TCMSEnvGroup, TCMSEnvProperty
from tcms.testcases.forms import CaseAutomatedForm
from tests import BaseCaseRun, BasePlanCase
from tests import factories as f


class TestQuickSearch(BaseCaseRun):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = reverse("nitrate-search")

    def test_goto_plan(self):
        response = self.client.get(
            self.search_url, {"search_type": "plans", "search_content": self.plan.pk}
        )
        self.assertRedirects(
            response,
            reverse("plan-get", args=[self.plan.pk]),
            target_status_code=HTTPStatus.MOVED_PERMANENTLY,
        )

    def test_goto_case(self):
        response = self.client.get(
            self.search_url, {"search_type": "cases", "search_content": self.case_1.pk}
        )

        self.assertRedirects(response, reverse("case-get", args=[self.case_1.pk]))

    def test_goto_run(self):
        response = self.client.get(
            self.search_url, {"search_type": "runs", "search_content": self.test_run.pk}
        )
        self.assertRedirects(response, reverse("run-get", args=[self.test_run.pk]))

    def test_goto_plan_search(self):
        response = self.client.get(
            self.search_url, {"search_type": "plans", "search_content": "keyword"}
        )
        url = "{}?a=search&search=keyword".format(reverse("plans-all"))
        self.assertRedirects(response, url)

    def test_goto_case_search(self):
        response = self.client.get(
            self.search_url, {"search_type": "cases", "search_content": "keyword"}
        )
        url = "{}?a=search&search=keyword".format(reverse("cases-all"))
        self.assertRedirects(response, url)

    def test_goto_run_search(self):
        response = self.client.get(
            self.search_url, {"search_type": "runs", "search_content": "keyword"}
        )
        url = "{}?a=search&search=keyword".format(reverse("runs-all"))
        self.assertRedirects(response, url)

    def test_goto_search_if_no_object_is_found(self):
        non_existing_pk = 9999999
        response = self.client.get(
            self.search_url, {"search_type": "cases", "search_content": non_existing_pk}
        )
        url = "{}?a=search&search={}".format(reverse("cases-all"), non_existing_pk)
        self.assertRedirects(response, url)

    def test_404_if_unknown_search_type(self):
        response = self.client.get(
            self.search_url,
            {"search_type": "unknown type", "search_content": self.plan.pk},
        )
        self.assert404(response)

    def test_404_when_missing_search_content(self):
        response = self.client.get(self.search_url, {"search_type": "plan"})
        self.assert404(response)

    def test_404_when_missing_search_type(self):
        response = self.client.get(self.search_url, {"search_content": "python"})
        self.assert404(response)


class TestGetForm(test.TestCase):
    """Test case for form"""

    def test_get_form(self):
        response = self.client.get(
            reverse("ajax-form"), {"app_form": "testcases.CaseAutomatedForm"}
        )
        form = CaseAutomatedForm()

        resp_content = response.content.decode("utf-8")
        self.assertHTMLEqual(resp_content, form.as_p())


class TestGetObjectInfo(BasePlanCase):
    """Test case for info view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.get_info_url = reverse("ajax-getinfo")

        cls.group_nitrate = f.TCMSEnvGroupFactory(name="nitrate")
        cls.group_new = f.TCMSEnvGroupFactory(name="NewGroup")

        cls.property_os = f.TCMSEnvPropertyFactory(name="os")
        cls.property_python = f.TCMSEnvPropertyFactory(name="python")
        cls.property_django = f.TCMSEnvPropertyFactory(name="django")

        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_nitrate, property=cls.property_os)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_nitrate, property=cls.property_python)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.group_new, property=cls.property_django)

    def test_get_env_properties(self):
        response = self.client.get(self.get_info_url, {"info_type": "env_properties"})

        expected_json = json.loads(
            serializers.serialize("json", TCMSEnvProperty.objects.all(), fields=("name", "value"))
        )
        self.assertEqual(expected_json, json.loads(response.content))

    def test_get_env_properties_by_group(self):
        response = self.client.get(
            self.get_info_url,
            {"info_type": "env_properties", "env_group_id": self.group_new.pk},
        )

        group = TCMSEnvGroup.objects.get(pk=self.group_new.pk)
        expected_json = json.loads(
            serializers.serialize("json", group.property.all(), fields=("name", "value"))
        )
        self.assertEqual(expected_json, json.loads(response.content))


@pytest.mark.parametrize(
    "fraction,population,expected",
    [
        ["3", "10", "30.0%"],
        ["3", "9", "33.3%"],
        ["0", "10", "0.0%"],
        ["10", "0", "0%"],
    ],
)
def test_template_tag_percentage(fraction, population, expected):
    assert expected == percentage(fraction, population)


class TestIndexView(test.TestCase):
    """Test the index view /"""

    @classmethod
    def setUpTestData(cls):
        cls.password = "password"
        cls.user: User = User.objects.create(username="tester", email="tester@localhost")
        cls.user.set_password(cls.password)
        cls.user.save()

    def test_anonymous(self):
        response = self.client.get(reverse("nitrate-index"), follow=True)
        self.assertEqual(reverse("nitrate-login"), response.wsgi_request.get_full_path())

    def test_authenticated_user(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.password))
        response = self.client.get(reverse("nitrate-index"), follow=True)
        self.assertEqual(
            reverse("user-recent", args=[self.user.username]), response.wsgi_request.get_full_path()
        )


@pytest.mark.parametrize(
    "input_str,required,expected",
    [
        ["", False, ""],
        ["user1@example.com", True, ["user1@example.com"]],
        ["user1@example.com,user2@host1.org", True, ["user1@example.com", "user2@host1.org"]],
        ["user1@example.com,,user2@host1.org", True, ["user1@example.com", "user2@host1.org"]],
        # Exceptions
        ["thisisanemailaddress", True, None],
        ["user1@example.com,someone_mail", True, None],
    ],
)
def test_multiple_email_field(input_str: str, required: bool, expected: List[str]):
    field = MultipleEmailField(required=required)
    if expected is None:
        with pytest.raises(ValidationError):
            field.clean(input_str)
    else:
        assert expected == field.clean(input_str)


@pytest.mark.parametrize(
    "input_str,required,expected",
    [
        ["", False, 0],
        ["2h", True, 7200],
        ["3m", True, 180],
        # Exceptions
        ["300", True, None],
        ["2hm", True, None],
    ],
)
def test_duration_field(input_str, required, expected):
    """Test DurationField"""
    field = DurationField(required=required)
    if expected is None:
        with pytest.raises(ValidationError):
            field.clean(input_str)
    else:
        assert expected == field.clean(input_str)


@pytest.mark.parametrize(
    "input_str,required,expected",
    [
        ["", False, None],
        [None, False, None],
        ["user1", False, "user1"],
        ["user1@example.com", False, "user1"],
        ["$user_id", False, "user1"],
        # Exceptions
        [0, True, ValidationError],
        ["0", True, ValidationError],
        ["", True, ValidationError],
        ["another_user", True, ValidationError],
    ],
)
@pytest.mark.django_db()
def test_user_field(input_str, required, expected, django_user_model):
    """Test UserField"""
    user1 = django_user_model.objects.create(
        username="user1", password="pwd", email="user1@example.com"
    )

    field = UserField(required=required)

    if expected == ValidationError:
        with pytest.raises(ValidationError):
            field.clean(input_str)
    else:
        if expected is None or isinstance(expected, int):
            assert expected == field.clean(input_str)
        elif isinstance(expected, str):
            if input_str == "$user_id":
                assert user1 == field.clean(user1.pk)
            else:
                assert user1 == field.clean(input_str)


@pytest.mark.parametrize("to_field_name", [None, "username"])
@pytest.mark.django_db()
def test_custom_model_choice_field(to_field_name, django_user_model):
    """Test custom ModelChoiceField"""
    user = django_user_model.objects.create(username="user1", password="pwd")

    field = ModelChoiceField(
        to_field_name=to_field_name,
        queryset=User.objects.all(),
        error_messages={"invalid_pk_value": "User id %(pk)s does not exist."},
    )

    if to_field_name is None:  # find user by pk
        with pytest.raises(ValidationError, match=r"id \d+ does"):
            field.clean(user.pk + 10)
    else:
        with pytest.raises(ValidationError, match="choice is not one of"):
            field.clean(user.username + "_xxx")


def test_xmlrpc_admin(admin_client, admin_user):
    """Test the customized admin site configuration"""
    XmlRpcLog.objects.create(user=admin_user, method="testcase.create", args="{'name': 'case 1'}")
    # Add this second log to cover the username cache check code
    XmlRpcLog.objects.create(user=admin_user, method="testcase.update", args="{'name': 'case 1'}")
    response = admin_client.get(reverse("admin:xmlrpc_xmlrpclog_changelist"))
    asserts.assertContains(response, "Happened On")
    asserts.assertContains(response, admin_user.username)

# -*- coding: utf-8 -*-

import unittest
import xmlrpc.client
from typing import Any, Callable, Dict
from unittest.mock import Mock

import pytest

from tcms.management.models import Classification, Product, TestBuild
from tcms.xmlrpc.api import build
from tests import BaseDataContext, encode
from tests import factories as f
from tests import user_should_have_perm
from tests.xmlrpc.utils import XmlrpcAPIBaseTest, make_http_request


class TestBuildCreate(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory()
        cls.admin_request = make_http_request(user=cls.admin, user_perm="management.add_testbuild")

        cls.staff = f.UserFactory()
        cls.staff_request = make_http_request(user=cls.staff)

        cls.product = f.ProductFactory(name="Nitrate")

    @unittest.skip("TODO: fix create to make this test pass.")
    def test_build_create_with_no_args(self):
        bad_args = (self.admin_request, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(build.create, self.admin_request, arg)

    def test_build_create_with_no_perms(self):
        self.assertXmlrpcFaultForbidden(build.create, self.staff_request, {})

    def test_build_create_with_no_required_fields(self):
        def _create(data):
            self.assertXmlrpcFaultBadRequest(build.create, self.admin_request, data)

        values = {"description": "Test Build", "is_active": False}
        _create(values)

        values["name"] = "TB"
        _create(values)

        del values["name"]
        values["product"] = self.product.pk
        _create(values)

    @unittest.skip("FIXME: Missing required argument must be handled. 400 is expected.")
    def test_build_create_with_illegal_fields(self):
        values = {"product": self.product.pk, "name": "B7", "milestone": "aaaaaaaa"}
        self.assertXmlrpcFaultBadRequest(build.create, self.admin_request, values)

    def test_build_create_with_non_exist_product(self):
        values = {
            "product": 9999,
            "name": "B7",
            "description": "Test Build",
            "is_active": False,
        }
        self.assertXmlrpcFaultNotFound(build.create, self.admin_request, values)

        values["product"] = "AAAAAAAAAA"
        self.assertXmlrpcFaultNotFound(build.create, self.admin_request, values)

    def test_build_create_with_chinese(self):
        values = {
            "product": self.product.pk,
            "name": "B99",
            "description": "开源中国",
            "is_active": False,
        }
        b = build.create(self.admin_request, values)
        self.assertIsNotNone(b)
        self.assertEqual(b["product_id"], self.product.pk)
        self.assertEqual(b["name"], "B99")
        self.assertEqual(b["description"], "开源中国")
        self.assertEqual(b["is_active"], False)

    def test_build_create(self):
        values = {
            "product": self.product.pk,
            "name": "B7",
            "description": "Test Build",
            "is_active": False,
        }
        b = build.create(self.admin_request, values)
        self.assertIsNotNone(b)
        self.assertEqual(b["product_id"], self.product.pk)
        self.assertEqual(b["name"], "B7")
        self.assertEqual(b["description"], "Test Build")
        self.assertEqual(b["is_active"], False)


class TestBuildUpdate(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.UserFactory()
        cls.admin_request = make_http_request(
            user=cls.admin, user_perm="management.change_testbuild"
        )

        cls.staff = f.UserFactory()
        cls.staff_request = make_http_request(user=cls.staff)

        cls.product = f.ProductFactory()
        cls.another_product = f.ProductFactory()

        cls.build_1 = f.TestBuildFactory(product=cls.product)
        cls.build_2 = f.TestBuildFactory(product=cls.product)
        cls.build_3 = f.TestBuildFactory(product=cls.product)

    @unittest.skip("TODO: fix update to make this test pass.")
    def test_build_update_with_no_args(self):
        bad_args = (None, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(build.update, self.admin_request, arg, {})
            self.assertXmlrpcFaultBadRequest(build.update, self.admin_request, self.build_1.pk, {})

    def test_build_update_with_no_perms(self):
        self.assertXmlrpcFaultForbidden(build.update, self.staff_request, self.build_1.pk, {})

    def test_build_update_with_multi_id(self):
        builds = (self.build_1.pk, self.build_2.pk, self.build_3.pk)
        self.assertXmlrpcFaultBadRequest(build.update, self.admin_request, builds, {})

    @unittest.skip("TODO: fix update to make this test pass.")
    def test_build_update_with_non_integer(self):
        bad_args = (True, False, (1,), dict(a=1), -1, 0.7, "", "AA")
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(build.update, self.admin_request, arg, {})

    def test_build_update_with_non_exist_build(self):
        self.assertXmlrpcFaultNotFound(build.update, self.admin_request, 999, {})

    def test_build_update_with_non_exist_product_id(self):
        self.assertXmlrpcFaultNotFound(
            build.update, self.admin_request, self.build_1.pk, {"product": 9999}
        )

    def test_build_update_with_non_exist_product_name(self):
        self.assertXmlrpcFaultNotFound(
            build.update,
            self.admin_request,
            self.build_1.pk,
            {"product": "AAAAAAAAAAAAAA"},
        )

    def test_build_update(self):
        b = build.update(
            self.admin_request,
            self.build_3.pk,
            {
                "product": self.another_product.pk,
                "name": "Update",
                "description": "Update from unittest.",
            },
        )
        self.assertIsNotNone(b)
        self.assertEqual(b["product_id"], self.another_product.pk)
        self.assertEqual(b["name"], "Update")
        self.assertEqual(b["description"], "Update from unittest.")


@pytest.mark.parametrize("test_api", [build.get, build.lookup_name_by_id])
@pytest.mark.parametrize(
    "build_id,expected",
    [
        [2, 2],
        [100, pytest.raises(xmlrpc.client.Fault)],  # non-existing build id
        ["", pytest.raises(xmlrpc.client.Fault)],
        [None, pytest.raises(xmlrpc.client.Fault)],
    ],
)
def test_get(test_api: Callable, build_id: int, expected, tester, base_data: BaseDataContext):
    request = make_http_request(tester)

    if isinstance(expected, int):
        result: Dict[str, Any] = test_api(request, build_id)
        b: TestBuild = TestBuild.objects.get(pk=build_id)
        assert b.pk == result["build_id"]
        assert b.name == result["name"]
        assert b.product.pk == result["product_id"]
        assert b.description == result["description"]
        assert b.is_active == result["is_active"]
    else:
        with expected:
            test_api(request, build_id)


class TestBuildGetCaseRuns(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.product = f.ProductFactory(name="Nitrate")
        cls.build = f.TestBuildFactory(product=cls.product)
        cls.user = f.UserFactory()
        cls.case_run_1 = f.TestCaseRunFactory(assignee=cls.user, build=cls.build)
        cls.case_run_2 = f.TestCaseRunFactory(assignee=cls.user, build=cls.build)

    @unittest.skip("TODO: fix get_caseruns to make this test pass.")
    def test_build_get_with_no_args(self):
        bad_args = (None, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(build.get_caseruns, None, arg)

    @unittest.skip("TODO: fix get_caseruns to make this test pass.")
    def test_build_get_with_non_integer(self):
        bad_args = (True, False, (1,), dict(a=1), -1, 0.7, "", "AA")
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(build.get_caseruns, None, arg)

    def test_build_get_with_non_exist_id(self):
        self.assertXmlrpcFaultNotFound(build.get_caseruns, None, 9999)

    def test_build_get_with_id(self):
        b = build.get_caseruns(None, self.build.pk)
        self.assertIsNotNone(b)
        self.assertEqual(2, len(b))
        self.assertEqual(b[0]["case"], encode(self.case_run_1.case.summary))


class TestBuildGetRuns(XmlrpcAPIBaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.product = f.ProductFactory()
        cls.version = f.VersionFactory(value="0.1", product=cls.product)
        cls.build = f.TestBuildFactory(product=cls.product)
        cls.user = f.UserFactory()
        cls.test_run = f.TestRunFactory(manager=cls.user, default_tester=None, build=cls.build)

    @unittest.skip("TODO: fix get_runs to make this test pass.")
    def test_build_get_with_no_args(self):
        bad_args = (None, [], (), {})
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(build.get_runs, None, arg)

    @unittest.skip("TODO: fix get_runs to make this test pass.")
    def test_build_get_with_non_integer(self):
        bad_args = (True, False, (1,), dict(a=1), -1, 0.7, "", "AA")
        for arg in bad_args:
            self.assertXmlrpcFaultBadRequest(build.get_runs, None, arg)

    def test_build_get_with_non_exist_id(self):
        self.assertXmlrpcFaultNotFound(build.get_runs, None, 9999)

    def test_build_get_with_id(self):
        b = build.get_runs(None, self.build.pk)
        self.assertIsNotNone(b)
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["summary"], self.test_run.summary)


@pytest.mark.parametrize("test_api", [build.check_build, build.lookup_id_by_name])
@pytest.mark.parametrize(
    "name,product,expected",
    [
        ["", "nitrate", pytest.raises(xmlrpc.client.Fault)],
        [None, "nitrate", pytest.raises(xmlrpc.client.Fault)],
        ["dev_build", "", pytest.raises(xmlrpc.client.Fault)],
        ["dev_build", None, pytest.raises(xmlrpc.client.Fault)],
        ["xxx", "nitrate", pytest.raises(xmlrpc.client.Fault)],
        ["dev_build", "xxx", pytest.raises(xmlrpc.client.Fault)],
        ["alpha_build", "xxx", pytest.raises(xmlrpc.client.Fault)],
        ["dev_build", "nitrate", "dev_build"],
    ],
)
def test_check_build(
    test_api: Callable, name, product, expected, tester, base_data: BaseDataContext
):
    request = make_http_request(tester)

    if isinstance(expected, str):
        result: Dict[str, Any] = test_api(request, name, product)

        b: TestBuild = TestBuild.objects.get(name=name, product__name=product)
        assert b.pk == result["build_id"]
        assert b.name == result["name"]
        assert b.product.pk == result["product_id"]
        assert b.description == result["description"]
        assert b.is_active == result["is_active"]
    else:
        with expected:
            test_api(request, name, product)


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"product": "coolapp"},
        {"name": "devbuild"},
        {"description": "a long description"},
        {"is_active": True},
        {"is_active": False},
        {"name": "alpha-build", "description": "desc", "is_active": False},
    ],
)
@pytest.mark.django_db()
def test_update(values: Dict[str, Any], django_user_model):
    user = django_user_model.objects.create(username="tester", email="tester@localhost")
    user_should_have_perm(user, "management.change_testbuild")

    classification = Classification.objects.create(name="webapp")
    Product.objects.create(pk=1, name="coolapp", classification=classification)
    tb = TestBuild.objects.create(
        name="coming-release",
        product=Product.objects.create(pk=2, name="nitrate", classification=classification),
    )

    request = Mock(user=user)
    if values:
        updated_build = build.update(request, tb.pk, values)
        for field_name, new_value in values.items():
            assert new_value == updated_build[field_name]
    else:
        assert tb.serialize() == build.update(request, tb.pk, values)

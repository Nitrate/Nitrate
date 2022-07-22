# -*- coding: utf-8 -*-

import json
import unittest.mock

from django import test
from django.urls import reverse

from tcms.linkreference.forms import TargetCharField
from tcms.linkreference.models import LinkReference, create_link
from tests import AuthMixin, HelperAssertions
from tests import factories as f
from tests import user_should_have_perm


class TestTargetCharField(unittest.TestCase):
    class PseudoClass:
        pass

    def setUp(self):
        test_targets = {"TestCaseRun": self.__class__.PseudoClass}
        self.field = TargetCharField(targets=test_targets)

    def test_type(self):
        from django.forms import Field

        self.assertIsInstance(self.field, Field)

    def test_clean(self):
        url_argu_value = "TestCaseRun"
        self.assertEqual(self.field.clean(url_argu_value), self.__class__.PseudoClass)

        from django.forms import ValidationError

        url_argu_value = "TestCase"
        self.assertRaises(ValidationError, self.field.clean, url_argu_value)


class LinkReferenceModel(test.TestCase):
    """Test model LinkReference"""

    @classmethod
    def setUpTestData(cls):
        from tests import factories as f

        cls.case_run = f.TestCaseRunFactory()

    def test_add_links_and_get_them(self):
        create_link("name1", "link1", self.case_run)
        create_link("name2", "link2", self.case_run)

        link_refs = LinkReference.get_from(self.case_run).order_by("pk")

        self.assertEqual("name1", str(link_refs[0]))
        self.assertEqual("link1", link_refs[0].url)
        self.assertEqual("name2", link_refs[1].name)
        self.assertEqual("link2", link_refs[1].url)

    def test_unlink(self):
        link_ref = create_link("name1", "link1", self.case_run)
        LinkReference.unlink(link_ref.pk)
        self.assertFalse(LinkReference.objects.filter(pk=link_ref.pk).exists())


class TestAddLinkReference(HelperAssertions, AuthMixin, test.TestCase):
    """Test add link reference"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.case = f.TestCaseFactory()
        cls.case_run = f.TestCaseRunFactory()
        cls.url = reverse("add-link-reference")
        user_should_have_perm(cls.tester, "testruns.change_testcaserun")

    def test_add_to_a_case_run(self):
        resp = self.client.post(
            self.url,
            data={
                "target": "TestCaseRun",
                "target_id": self.case_run.pk,
                "name": "A cool site",
                "url": "https://coolsite.com/",
            },
        )

        self.assertJsonResponse(resp, {"name": "A cool site", "url": "https://coolsite.com/"})

        self.assertTrue(
            LinkReference.objects.filter(name="A cool site", url="https://coolsite.com/").exists()
        )

    def test_wrong_target_type(self):
        resp = self.client.post(
            self.url,
            data={
                "target": "TestCase",
                "target_id": self.case.pk,
                "name": "A cool site",
                "url": "https://coolsite.com/",
            },
        )

        self.assert400(resp)


class TestGetLinkReferencesFromSpecificTarget(HelperAssertions, test.TestCase):
    """Test view of getting link references of a target"""

    @classmethod
    def setUpTestData(cls):
        cls.case_run = f.TestCaseRunFactory()
        create_link("name1", "link1", cls.case_run)
        create_link("name2", "link2", cls.case_run)

        cls.url = reverse("get-link-references")

    def test_get_the_links(self):
        resp = self.client.get(
            self.url,
            data={
                "target": "TestCaseRun",
                "target_id": self.case_run.pk,
            },
        )

        data = sorted(json.loads(resp.content), key=lambda item: item["name"])
        expected = [
            {"name": "name1", "url": "link1"},
            {"name": "name2", "url": "link2"},
        ]

        self.assertListEqual(expected, data)

    def test_target_id_does_not_exist(self):
        resp = self.client.get(
            self.url,
            data={
                "target": "TestCaseRun",
                "target_id": self.case_run.pk + 1,
            },
        )

        self.assert400(resp)

    def test_wrong_target_type(self):
        resp = self.client.get(
            self.url,
            data={
                "target": "TestCase",
                "target_id": self.case_run.pk,
            },
        )

        self.assert400(resp)


class TestRemoveLinkReference(HelperAssertions, AuthMixin, test.TestCase):
    """Test remove view"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.case_run = f.TestCaseRunFactory()
        cls.link1 = create_link("name1", "link1", cls.case_run)
        cls.link2 = create_link("name2", "link2", cls.case_run)
        user_should_have_perm(cls.tester, "testruns.change_testcaserun")

    def test_remove(self):
        url = reverse("remove-link-reference", args=[self.link2.pk])
        self.client.post(url)
        self.assertFalse(LinkReference.objects.filter(pk=self.link2.pk).exists())

    @unittest.mock.patch("tcms.linkreference.models.LinkReference.unlink")
    def test_fail_to_unlink(self, unlink):
        unlink.side_effect = Exception
        url = reverse("remove-link-reference", args=[self.link2.pk])
        resp = self.client.post(url)
        self.assert400(resp)

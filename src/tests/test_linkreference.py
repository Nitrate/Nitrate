# -*- coding: utf-8 -*-

import unittest
from django import test
from tcms.linkreference.models import create_link, LinkReference
from tcms.linkreference.forms import TargetCharField


class TestTargetCharField(unittest.TestCase):
    class PseudoClass:
        pass

    def setUp(self):
        test_targets = {'TestCaseRun': self.__class__.PseudoClass}
        self.field = TargetCharField(targets=test_targets)

    def test_type(self):
        from django.forms import Field

        self.assertIsInstance(self.field, Field)

    def test_clean(self):
        url_argu_value = 'TestCaseRun'
        self.assertEqual(self.field.clean(url_argu_value),
                         self.__class__.PseudoClass)

        from django.forms import ValidationError

        url_argu_value = 'TestCase'
        self.assertRaises(ValidationError, self.field.clean, url_argu_value)


class LinkReferenceModel(test.TestCase):
    """Test model LinkReference"""

    @classmethod
    def setUpTestData(cls):
        from tests import factories as f
        cls.case_run = f.TestCaseRunFactory()

    def test_add_links_and_get_them(self):
        create_link('name1', 'link1', self.case_run)
        create_link('name2', 'link2', self.case_run)

        link_refs = LinkReference.get_from(self.case_run).order_by('pk')

        self.assertEqual('name1', str(link_refs[0]))
        self.assertEqual('link1', link_refs[0].url)
        self.assertEqual('name2', link_refs[1].name)
        self.assertEqual('link2', link_refs[1].url)

    def test_unlink(self):
        link_ref = create_link('name1', 'link1', self.case_run)
        LinkReference.unlink(link_ref.pk)
        self.assertFalse(LinkReference.objects.filter(pk=link_ref.pk).exists())

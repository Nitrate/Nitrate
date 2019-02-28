# -*- coding: utf-8 -*-

import unittest

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


class LinkReferenceModel(unittest.TestCase):
    pass

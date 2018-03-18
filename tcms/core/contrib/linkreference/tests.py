# -*- coding: utf-8 -*-

from __future__ import absolute_import

import unittest

from .forms import TargetCharField


class TestTargetCharField(unittest.TestCase):
    class PseudoClass(object):
        pass

    def setUp(self):
        test_targets = {'TestCaseRun': self.__class__.PseudoClass}
        self.field = TargetCharField(targets=test_targets)

    def test_type(self):
        from django.forms import Field

        self.assert_(isinstance(self.field, Field))

    def test_clean(self):
        url_argu_value = 'TestCaseRun'
        self.assertEqual(self.field.clean(url_argu_value),
                         self.__class__.PseudoClass)

        from django.forms import ValidationError

        url_argu_value = 'TestCase'
        self.assertRaises(ValidationError, self.field.clean, url_argu_value)


class LinkReferenceModel(unittest.TestCase):
    pass

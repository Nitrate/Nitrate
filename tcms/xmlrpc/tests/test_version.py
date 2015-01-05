# -*- coding: utf-8 -*-
from django.test import TestCase


class TestVersion(TestCase):

    def test_get_version(self):
        from tcms.xmlrpc import get_version
        from tcms.xmlrpc.api import version

        response = version.get(None)
        self.assertEqual(response, get_version())

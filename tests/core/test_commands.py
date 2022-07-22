# -*- coding: utf-8 -*-

from unittest.mock import patch

from django import test
from django.contrib.auth.models import Group
from django.core.management import call_command

from tcms.core.management.commands import setdefaultperms


class TestSetDefaultPerms(test.TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.group = Group.objects.create(name="KeyTesters")

    def test_set_perms(self):
        perms = {
            "KeyTesters": {
                "user": {"add": 0, "change": 1, "delete": 0},
                "testplan": {"add": 1, "change": 1, "delete": 1},
            }
        }

        with patch.dict(setdefaultperms.DEFAULT_PERMS, values=perms, clear=True):
            call_command("setdefaultperms")

        g = Group.objects.get(name="KeyTesters")
        added_codenames = [p.codename for p in g.permissions.all()]

        for codename in [
            "change_user",
            "add_testplan",
            "change_testplan",
            "delete_testplan",
        ]:
            self.assertIn(codename, added_codenames)

        for codename in ["add_user", "delete_user"]:
            self.assertNotIn(codename, added_codenames)

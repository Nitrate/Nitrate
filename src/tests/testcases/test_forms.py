# -*- coding: utf-8 -*-
from django import test

from tcms.testcases.forms import QuickSearchCaseForm


class TestQuickSearchCaseForm(test.TestCase):
    """Test QuickSearchCaseForm"""

    def test_valid_input(self):
        form = QuickSearchCaseForm({"case_id_set": "1,2, 3"})
        self.assertTrue(form.is_valid())
        self.assertEqual([1, 2, 3], sorted(form.cleaned_data["case_id_set"]))

    def test_empty_string_for_case_id_set(self):
        form = QuickSearchCaseForm({"case_id_set": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("Please input valid case id(s)", form.errors["case_id_set"][0])

    def test_non_integer_in_case_id_set(self):
        for value in ("1,2,a,4", "1,2,,3"):
            form = QuickSearchCaseForm({"case_id_set": value})
            self.assertFalse(form.is_valid())
            self.assertIn("Please input valid case id(s)", form.errors["case_id_set"][0])

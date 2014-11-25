# -*- coding: utf-8 -*-
from django.db.models import ObjectDoesNotExist
from django_nose import FastFixtureTestCase

from tcms.xmlrpc import utils


class TestXMLRPCUtils(FastFixtureTestCase):
    fixtures = ['unittest.json']

    def test_parse_bool_value_with_rejected_args(self):
        rejected_args = (3, -1, "", "True", "False", "yes", "no", "33",
                         "-11", [], (), {}, None)
        for arg in rejected_args:
            try:
                utils.parse_bool_value(arg)
            except ValueError as e:
                self.assertEqual(str(e), 'Unacceptable bool value.')
            except Exception:
                self.fail("Unexcept error occurs.")
            else:
                self.fail("Missing validations for %s" % arg)

    def test_parse_bool_value(self):
        false_values = (0, "0", False)
        for arg in false_values:
            try:
                value = utils.parse_bool_value(arg)
            except Exception:
                self.fail("Unexcept error occurs.")
            else:
                self.assertFalse(value)

        true_values = (1, "1", True)
        for arg in true_values:
            try:
                value = utils.parse_bool_value(arg)
            except Exception:
                self.fail("Unexcept error occurs.")
            else:
                self.assertTrue(value)

    def test_pre_check_product_with_dict(self):
        try:
            product = utils.pre_check_product({
                "product": 4
            })
        except ObjectDoesNotExist:
            self.fail("Unexcept error occurs.")
        else:
            self.assertEqual(product.name, "World Of Warcraft")

        try:
            product = utils.pre_check_product({
                "product": "World Of Warcraft"
            })
        except ObjectDoesNotExist:
            self.fail("Unexcept error occurs.")
        else:
            self.assertEqual(product.name, "World Of Warcraft")

    def test_pre_check_product_with_no_key(self):
        try:
            product = utils.pre_check_product({})
        except ObjectDoesNotExist:
            self.fail("Unexcept error occurs.")
        else:
            self.assertIsNone(product)

    def test_pre_check_product_with_illegal_types(self):
        types = ((), [], True, False, self,)
        for arg in types:
            try:
                utils.pre_check_product(arg)
            except ValueError as e:
                self.assertEqual(str(e), 'The type of product is not '
                                         'recognizable.')
            else:
                self.fail("Missing validations for %s" % arg)

    def test_pre_check_product_with_number(self):
        types = (4, "4")
        for arg in types:
            try:
                product = utils.pre_check_product(arg)
            except ValueError:
                self.fail("Unexcept error occurs.")
            else:
                self.assertEqual(product.name, "World Of Warcraft")

    def test_pre_check_product_with_name(self):
        try:
            product = utils.pre_check_product("World Of Warcraft")
        except ValueError:
            self.fail("Unexcept error occurs.")
        else:
            self.assertEqual(product.name, "World Of Warcraft")

    def test_pre_check_product_with_no_exist(self):
        try:
            utils.pre_check_product(9999)
        except ObjectDoesNotExist:
            pass
        else:
            self.fail("Unexcept error occurs.")

        try:
            utils.pre_check_product("AAAAAAA")
        except ObjectDoesNotExist:
            pass
        else:
            self.fail("Unexcept error occurs.")

    def test_pre_process_ids_with_list(self):
        ids = utils.pre_process_ids(["1", "2", "3"])
        self.assertEqual(ids, [1, 2, 3])

    def test_pre_process_ids_with_str(self):
        ids = utils.pre_process_ids("1")
        self.assertEqual(ids, [1])

        ids = utils.pre_process_ids("1,2,3,4")
        self.assertEqual(ids, [1, 2, 3, 4])

    def test_pre_process_ids_with_int(self):
        ids = utils.pre_process_ids(1)
        self.assertEqual(ids, [1])

    def test_pre_process_ids_with_others(self):
        try:
            utils.pre_process_ids((1,))
        except TypeError as e:
            self.assertEqual(str(e), 'Unrecognizable type of ids')
        else:
            self.fail("Missing validations.")

        try:
            utils.pre_process_ids(dict(a=1))
        except TypeError as e:
            self.assertEqual(str(e), 'Unrecognizable type of ids')
        else:
            self.fail("Missing validations.")

    def test_pre_process_ids_with_string(self):
        try:
            utils.pre_process_ids(["a", "b"])
        except ValueError as e:
            pass
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.fail("Missing validations.")

        try:
            utils.pre_process_ids("1@2@3@4")
        except ValueError as e:
            pass
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.fail("Missing validations.")

    def test_pre_process_estimated_time(self):
        bad_args = ([], (), {}, True, False, 0, 1, -1)
        for arg in bad_args:
            try:
                utils.pre_process_estimated_time(arg)
            except ValueError as e:
                self.assertEqual(str(e), 'Invaild estimated_time format.')
            except Exception:
                self.fail("Unexcept error occurs.")
            else:
                self.fail("Missing validations.")

    def test_pre_process_estimated_time_with_empty(self):
        try:
            utils.pre_process_estimated_time("")
        except ValueError as e:
            self.assertEqual(str(e), 'Invaild estimated_time format.')
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.fail("Missing validations.")

    def test_pre_process_estimated_time_with_bad_form(self):
        try:
            utils.pre_process_estimated_time("aaaaaa")
        except ValueError as e:
            self.assertEqual(str(e), 'Invaild estimated_time format.')
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.fail("Missing validations.")

    def test_pre_process_estimated_time_with_time_string(self):
        try:
            time = utils.pre_process_estimated_time("13:22:54")
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.assertEqual(time, "13h22m54s")

        try:
            time = utils.pre_process_estimated_time("1d13h22m54s")
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.assertEqual(time, "1d13h22m54s")

    def test_pre_process_estimated_time_with_upper_string(self):
        try:
            utils.pre_process_estimated_time("1D13H22M54S")
        except ValueError as e:
            self.assertEqual(str(e), 'Invaild estimated_time format.')
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.fail("Missing validations.")

    def test_pre_process_estimated_time_with_string(self):
        try:
            utils.pre_process_estimated_time("aa:bb:cc")
        except ValueError as e:
            self.assertEqual(str(e), 'Invaild estimated_time format.')
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.fail("Missing validations.")

    def test_pre_process_estimated_time_with_mhs(self):
        try:
            utils.pre_process_estimated_time("ambhcs")
        except ValueError as e:
            self.assertEqual(str(e), 'Invaild estimated_time format.')
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.fail("Missing validations.")

    def test_pre_process_estimated_time_with_symbols(self):
        try:
            utils.pre_process_estimated_time("aa@bb@cc")
        except ValueError as e:
            self.assertEqual(str(e), 'Invaild estimated_time format.')
        except Exception:
            self.fail("Unexcept error occurs.")
        else:
            self.fail("Missing validations.")
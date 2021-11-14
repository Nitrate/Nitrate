# -*- coding: utf-8 -*-
import logging
import smtplib
import sys
import unittest
from datetime import timedelta
from typing import Dict, Union
from unittest.mock import Mock, patch

import pytest
from django import test
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.http import QueryDict

from tcms.core import responses
from tcms.core.db import CaseRunStatusGroupByResult, GroupByResult
from tcms.core.mailto import mail_notify, mailto
from tcms.core.task import AsyncTask, Task
from tcms.core.utils import (
    calc_percent,
    clean_request,
    format_timedelta,
    get_string_combinations,
    request_host_link,
    string_to_list,
    timedelta2int,
)
from tcms.management.models import Classification
from tests import HelperAssertions
from tests.factories import TestPlanFactory

PY37 = sys.version_info[:2] == (3, 7)


@pytest.mark.parametrize(
    "s,sep,expected",
    [
        ["", None, []],
        [None, None, []],
        ["python", None, ["python"]],
        ["python,rust", None, ["python", "rust"]],
        [",python,,rust,", None, ["python", "rust"]],
        ["python,,rust,", None, ["python", "rust"]],
        ["python, rust ", None, ["python", "rust"]],
        ["python rust ", " ", ["python", "rust"]],
        [" python   rust ", " ", ["python", "rust"]],
        [["python", "rust"], None, ["python", "rust"]],
        [["python", "rust"], ",", ["python", "rust"]],
        [["\tpython", "rust\n"], None, ["python", "rust"]],
    ],
)
def test_string_to_list(s, sep, expected):
    assert expected == string_to_list(s, sep)


@pytest.mark.parametrize(
    "s,expected",
    [
        ["", ("", "", "", "")],
        [None, (None, None, None, None)],
        ["word", ("word", "word", "WORD", "Word")],
        ["Word", ("Word", "word", "WORD", "Word")],
        ["WORD", ("WORD", "word", "WORD", "Word")],
    ],
)
def test_get_string_combinations(s, expected):
    assert expected == get_string_combinations(s)


@pytest.mark.parametrize(
    "x,y,expected",
    [
        [0, 0, 0.0],
        [0, 1, 0.0],
        [1, 0, 0.0],
        [1, 0, 0.0],
        [2, 10, 20.0],
        [3, 9, 3.0 / 9 * 100],
    ],
)
def test_calc_percent(x, y, expected):
    assert expected == calc_percent(x, y)


@pytest.mark.parametrize(
    "scheme,host,domain,expected",
    [
        ["https", "localhost", None, "https://localhost"],
        ["https", "localhost", "host1.site", "https://host1.site"],
        ["http", "localhost", None, "http://localhost"],
        ["http", "localhost", "host1.site", "http://host1.site"],
    ],
)
def test_request_host_link(scheme, host, domain, expected):
    request = Mock()
    request.scheme = scheme
    request.get_host.return_value = host
    assert expected == request_host_link(request, domain)


@pytest.mark.parametrize(
    "query_args,keys,expected",
    [
        ["", None, {}],
        # order_by is removed
        ["lang=py&order_by=ver", None, {"lang": "py"}],
        ["lang=py&order_by=ver", {}, {"lang": "py"}],
        # from_plan is removed
        ["lang=py&from_plan=1", None, {"lang": "py"}],
        ["lang__in=py,rust,go&product=1", None, {"lang__in": ["py", "rust", "go"], "product": "1"}],
        # clean by argument keys
        [
            "lang=py&order_by=ver&product=1",
            ["lang", "product", "page"],
            {"lang": "py", "product": "1"},
        ],
    ],
)
def test_clean_request(query_args, keys, expected):
    request = Mock()
    request.GET = QueryDict(query_args)
    assert expected == clean_request(request, keys)


@pytest.mark.parametrize(
    "timedelta,expected",
    [
        ["1m", 60],
        ["25m", 1500],
        ["2h", 7200],
        ["1h30m", 5400],
        ["20h30m", 73800],
        ["2d", 172800],
        ["2d12h", 216000],
        ["2d12h6m", 216360],
        ["2d012h6m", 216360],
        # Exception input timedeltas
        ["", 0],
        [None, 0],
        ["5.5m", ValueError],
        ["6m2d012h", ValueError],
        ["6s12h", ValueError],
        ["6m12d", ValueError],
        ["6s12m", ValueError],
        ["1d1.5h", ValueError],
        ["30", ValueError],
        ["d012h6m30s", ValueError],
        ["2dh6m30s", ValueError],
        ["2d8hm30s", ValueError],
        ["2d8h10ms", ValueError],
        ["2d8g10m", ValueError],
        ["2d8h m30s", ValueError],
        ["-20h30m", ValueError],
    ],
)
def test_timedelta2int(timedelta, expected: Union[int, Exception]):
    if isinstance(expected, int):
        assert expected == timedelta2int(timedelta)
    else:
        with pytest.raises(expected):
            timedelta2int(timedelta)


@pytest.mark.parametrize(
    "seconds,expected",
    [
        [0, "0m"],
        [10, "10s"],
        [75, "1m15s"],
        [7335, "2h2m15s"],
        [201600, "2d8h"],
    ],
)
def test_format_timedelta(seconds, expected):
    assert expected == format_timedelta(timedelta(seconds=seconds))


class GroupByResultDictLikeTest(unittest.TestCase):
    """Test dict like behaviors"""

    def setUp(self):
        self.groupby_result = GroupByResult({"total": 100})

    def test_in(self):
        self.assertNotIn("a", self.groupby_result)
        self.assertIn("total", self.groupby_result)

    def test_key(self):
        self.assertTrue(self.groupby_result.keys(), ["total"])

    def test_setdefault(self):
        ret_val = self.groupby_result.setdefault("count", {})
        self.assertEqual(ret_val, {})

        ret_val = self.groupby_result.setdefault("total", 200)
        self.assertEqual(ret_val, 100)

    def test_setitem(self):
        self.groupby_result["count"] = 200
        self.assertEqual(self.groupby_result["count"], 200)

        self.groupby_result["total"] = 999
        self.assertEqual(self.groupby_result["total"], 999)

    def test_get(self):
        ret_val = self.groupby_result.get("total")
        self.assertEqual(ret_val, 100)

        ret_val = self.groupby_result.get("count", 999)
        self.assertEqual(ret_val, 999)

        ret_val = self.groupby_result.get("xxx")
        self.assertEqual(ret_val, None)

    def test_len(self):
        self.assertEqual(len(self.groupby_result), 1)

    def test_del(self):
        self.groupby_result["count"] = 200
        del self.groupby_result["total"]
        self.assertNotIn("total", self.groupby_result)
        del self.groupby_result["count"]
        self.assertNotIn("count", self.groupby_result)
        self.assertEqual(len(self.groupby_result), 0)

    def test_raise_key_error(self):
        with self.assertRaises(KeyError):
            self.groupby_result["unknown_key"]

    def test___str__(self):
        gbr = GroupByResult({"idle": 100})
        self.assertEqual(str(gbr._data), str(gbr))

    def test___repr__(self):
        gbr = GroupByResult({"idle": 100})
        self.assertEqual(repr(gbr._data), repr(gbr))


class GroupByResultCalculationTest(unittest.TestCase):
    """Test calculation of GroupByResult"""

    def test_get_total_after_add_data_based_on_empty_initial_data(self):
        result = GroupByResult()
        result["RUNNING"] = 100
        result["PASSED"] = 100
        self.assertEqual(200, result.total)

    def test_get_total_after_add_data_based_on_initial_data(self):
        result = GroupByResult({"FAILED": 20})
        result["RUNNING"] = 100
        result["PASSED"] = 100
        self.assertEqual(220, result.total)

    def test_total_is_updated_after_del_item(self):
        result = GroupByResult({"FAILED": 20, "RUNNING": 20, "PASSED": 10})
        del result["RUNNING"]
        self.assertEqual(30, result.total)

    def test_total_is_updated_after_del_item_several_times(self):
        result = GroupByResult({"FAILED": 20, "RUNNING": 20, "PASSED": 10})
        del result["RUNNING"]
        del result["FAILED"]
        self.assertEqual(10, result.total)

    def test_arithmetic_operation(self):
        result = GroupByResult({"IDLE": 1, "RUNNING": 1, "FAILED": 2})
        result["IDLE"] += 1
        result["RUNNING"] += 100
        result["FAILED"] -= 2
        self.assertEqual(2, result["IDLE"])
        self.assertEqual(101, result["RUNNING"])
        self.assertEqual(0, result["FAILED"])


@pytest.mark.parametrize(
    "initial_data,total_name,expected",
    [
        [None, None, 0],
        [{}, None, 0],
        [{"python": 10}, None, 10],
        [{"python": 10, "rust": 20}, None, 30],
        [{"python": 10, "rust": 20, "total_count": 30}, "total_count", 30],
        # side-effect: the given total count is not same as the actual total
        [{"python": 10, "rust": 20, "total_count": 50}, "total_count", 50],
        # Nested groupby results
        [
            {
                1: GroupByResult({"python": 10, "rust": 20}),
                2: GroupByResult({"go": 6, "perl": 9, "julia": 100}),
                3: GroupByResult({"fedora": 34}),
            },
            None,
            179,
        ],
        # side-effect: no information about if mixed int and GroupByResult
        # values are by design or not.
        [
            {
                "lang": GroupByResult({"python": 10, "rust": 20}),
                "os": GroupByResult({"fedora": 34}),
                "linux": 3,
            },
            None,
            67,
        ],
        # Incorrect value type
        [
            {
                "lang": GroupByResult({"python": 10, "rust": 20}),
                "os": GroupByResult({"fedora": 34}),
                "count": "300",
            },
            None,
            TypeError,
        ],
    ],
)
def test_groupbyresult_total_property(
    initial_data: Dict[str, int], total_name: Union[str, None], expected: int
):
    if isinstance(expected, int):
        assert expected == GroupByResult(initial_data, total_name=total_name).total
    else:
        with pytest.raises(TypeError):
            GroupByResult(initial_data, total_name=total_name)


@pytest.mark.parametrize(
    "initial_data,total_name,expected",
    [
        [None, None, 0.0],
        [{}, None, 0.0],
        [{"rust": 10}, None, 0.0],
        [{"python": 10}, None, 100.0],
        [{"python": 0, "rust": 0}, None, 0.0],
        [{"python": 10, "rust": 40}, None, 20.0],
        [{"python": 10, "rust": 20}, None, 33.3],
        [{"Python": 10, "rust": 20}, None, 0.0],
        [{"python": 10, "rust": 30, "total_polls": 40}, "total_polls", 25.0],
        # inconsistent total_name is passed
        [{"python": 10, "rust": 30, "total_polls": 40}, "total", KeyError],
        # side-effect: total is not correct, but still calculate
        [{"python": 10, "rust": 30, "total_polls": 100}, "total_polls", 10.0],
    ],
)
def test_groupbyresult_percent_property(
    initial_data: Dict[str, int], total_name: Union[str, None], expected: Union[float, KeyError]
):
    if isinstance(expected, float):
        assert expected == GroupByResult(initial_data, total_name=total_name).python_percent
    else:
        with pytest.raises(expected, match="Unknown key total"):
            GroupByResult(initial_data, total_name=total_name).python_percent


class GroupByResultLevelTest(unittest.TestCase):
    def setUp(self):
        self.levels_groupby_result = GroupByResult(
            {
                "build_1": GroupByResult(
                    {
                        "plan_1": GroupByResult(
                            {
                                "run_1": GroupByResult(
                                    {
                                        "passed": 1,
                                        "failed": 2,
                                        "error": 3,
                                    }
                                ),
                                "run_2": GroupByResult(
                                    {
                                        "passed": 1,
                                        "failed": 2,
                                        "error": 3,
                                    }
                                ),
                                "run_3": GroupByResult(
                                    {
                                        "passed": 1,
                                        "failed": 2,
                                        "error": 3,
                                    }
                                ),
                            }
                        ),
                        "plan_2": GroupByResult(
                            {
                                "run_1": GroupByResult(
                                    {
                                        "passed": 1,
                                        "failed": 2,
                                        "error": 3,
                                    }
                                ),
                                "run_2": GroupByResult(
                                    {
                                        "passed": 1,
                                        "failed": 2,
                                        "error": 3,
                                    }
                                ),
                            }
                        ),
                    }
                ),
                "build_2": GroupByResult(
                    {
                        "plan_1": GroupByResult(
                            {
                                "run_1": GroupByResult(
                                    {
                                        "passed": 1,
                                        "failed": 2,
                                        "error": 3,
                                    }
                                ),
                                "run_4": GroupByResult(
                                    {
                                        "paused": 2,
                                        "failed": 2,
                                        "waived": 6,
                                    }
                                ),
                                "run_5": GroupByResult(
                                    {
                                        "paused": 1,
                                        "failed": 2,
                                        "waived": 3,
                                    }
                                ),
                            }
                        ),
                        "plan_2": GroupByResult(
                            {
                                "run_1": GroupByResult(
                                    {
                                        "passed": 1,
                                        "failed": 2,
                                        "error": 3,
                                    }
                                ),
                                "run_4": GroupByResult(
                                    {
                                        "paused": 2,
                                        "failed": 2,
                                        "waived": 6,
                                    }
                                ),
                                "run_5": GroupByResult(
                                    {
                                        "paused": 1,
                                        "failed": 2,
                                        "waived": 3,
                                    }
                                ),
                            }
                        ),
                    }
                ),
            }
        )

    def test_value_leaf_count(self):
        value_leaf_count = self.levels_groupby_result.leaf_values_count()
        self.assertEqual(value_leaf_count, 33)

        value_leaf_count = self.levels_groupby_result["build_1"].leaf_values_count()
        self.assertEqual(value_leaf_count, 15)

        level_node = self.levels_groupby_result["build_2"]["plan_2"]
        value_leaf_count = level_node.leaf_values_count()
        self.assertEqual(value_leaf_count, 9)

    def test_value_leaf_in_row_count(self):
        value_leaf_count = self.levels_groupby_result.leaf_values_count(value_in_row=True)
        self.assertEqual(value_leaf_count, 11)

        level_node = self.levels_groupby_result["build_2"]
        value_leaf_count = level_node.leaf_values_count(value_in_row=True)
        self.assertEqual(value_leaf_count, 6)

        level_node = self.levels_groupby_result["build_1"]["plan_2"]
        value_leaf_count = level_node.leaf_values_count(value_in_row=True)
        self.assertEqual(value_leaf_count, 2)


class VariousResponsesTest(HelperAssertions, unittest.TestCase):
    """Test HttpJSONResponse"""

    def test_json_response_badrequest(self):
        response = responses.JsonResponseBadRequest({})

        self.assert400(response)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_json_response_servererror(self):
        response = responses.JsonResponseServerError({})
        self.assert500(response)
        self.assertEqual(response["Content-Type"], "application/json")


class TestUrlMixin(test.TestCase):
    """Test UrlMixin"""

    @classmethod
    def setUpTestData(cls):
        cls.plan = TestPlanFactory()

        site = Site.objects.get_current()
        site.domain = "localhost"
        site.save()

    def test_get_full_url(self):
        url = self.plan.get_full_url()
        expected_url = "http://localhost/{}".format(self.plan.get_absolute_url())
        self.assertEqual(expected_url, url)

    @patch.object(settings, "SITE_HTTP_SCHEME", new="", create=True)
    def test_use_default_http_if_option_is_empty(self):
        url = self.plan.get_full_url()
        expected_url = "http://localhost/{}".format(self.plan.get_absolute_url())
        self.assertEqual(expected_url, url)

    @patch.object(settings, "SITE_HTTP_SCHEME", new="https", create=True)
    def test_use_correct_configured_scheme(self):
        url = self.plan.get_full_url()
        expected_url = "https://localhost/{}".format(self.plan.get_absolute_url())
        self.assertEqual(expected_url, url)


class TestAsyncTask(unittest.TestCase):
    """Test async task class Task"""

    def test_disabled(self):
        with patch.object(settings, "ASYNC_TASK", new=AsyncTask.DISABLED.value):
            func = Mock()
            task = Task(func)
            task(1, a=2)
            func.assert_called_once_with(1, a=2)

    @patch("threading.Thread")
    def test_uses_threading(self, Thread):
        with patch.object(settings, "ASYNC_TASK", new=AsyncTask.THREADING.value):
            func = Mock()
            task = Task(func)
            task(1, a=2)
            func.assert_not_called()

            Thread.assert_called_once_with(target=func, args=(1,), kwargs={"a": 2})
            thread = Thread.return_value
            self.assertTrue(thread.daemon)
            thread.start.assert_called_once()

    @patch("celery.shared_task")
    def test_uses_celery(self, shared_task):
        with patch.object(settings, "ASYNC_TASK", new=AsyncTask.CELERY.value):
            func = Mock()
            task = Task(func)
            task(1, a=2)
            func.assert_not_called()

            shared_task.assert_called_once_with(func)
            self.assertEqual(shared_task.return_value, task.target)
            shared_task.return_value.delay.assert_called_once_with(1, a=2)

    def test_celery_module_is_not_installed(self):
        with patch.object(settings, "ASYNC_TASK", new=AsyncTask.CELERY.value):
            # Patch sys.modules in order to make it failure to import the celery module
            with patch.dict(sys.modules, values={"celery": None}):
                self.assertRaises(ImportError, Task, Mock())

    @patch("tcms.core.task.logger")
    def test_unknown_async_task_setting(self, logger):
        with patch.object(settings, "ASYNC_TASK", new="SOME_OTHER_ASYNC"):
            t = Task(Mock())
            t(1)
            logger.warning.assert_called_once()


class TestMailTo(test.SimpleTestCase):
    """Test mailto"""

    def setUp(self) -> None:
        self.get_template_p = patch("tcms.core.mailto.loader.get_template")
        self.mock_get_template = self.get_template_p.start()
        self.mock_get_template.return_value.render.return_value = "Good news."

    def tearDown(self) -> None:
        self.get_template_p.stop()

    def test_send_mail(self):
        mailto("mail_template", "Start Test", ["tester@localhost"])
        self.assertEqual("Start Test", mail.outbox[0].subject)

    def test_also_send_mail_to_addresses_for_debug(self):
        with patch.object(settings, "DEBUG", new=True):
            with patch.object(settings, "EMAILS_FOR_DEBUG", new=["cotester@localhost"]):
                mailto("mail_template", "Start Test", ["tester@localhost"])

        self.assertListEqual(
            ["cotester@localhost", "tester@localhost"],
            sorted(mail.outbox[0].recipients()),
        )

    def test_recipients_accept_non_sequence_value(self):
        mailto("mail_template", "Start Test", "tester@localhost")
        self.assertEqual("tester@localhost", mail.outbox[0].recipients()[0])

    @patch("tcms.core.mailto.EmailMessage")
    @patch("tcms.core.mailto.logger")
    def test_log_traceback_when_error_is_raised_from_send(self, logger, EmailMessage):
        EmailMessage.return_value.send.side_effect = smtplib.SMTPException
        mailto("mail_template", "Start Test", ["tester@localhost"])
        logger.exception.assert_called_once()


class TestModelLogAction(test.TestCase):
    """Test TCMSModel.log_action"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = User.objects.create_user(username="tester", email="tester@localhost")
        cls.classification = Classification.objects.create(name="webapp")

    def test_log_action(self):
        # who, new_value, field, original_value
        test_cases = (
            (self.tester, "new value", None, None),
            (self.tester, "new value", "", None),
            (self.tester, "new value", "", ""),
            (self.tester, "new value", None, ""),
            (self.tester, "new value", "field", None),
            (self.tester, "new value", "field", "old value"),
        )

        for log_args in test_cases:
            log = self.classification.log_action(*log_args)

            who, new_value, field, original_value = log_args
            self.assertEqual(who, log.who)
            self.assertEqual(new_value, log.new_value)
            self.assertEqual(field or "", log.field)
            self.assertEqual(original_value or "", log.original_value)


class TestCaseRunStatusGroupbyResult(test.TestCase):
    """Test CaseRunStatusGroupByResult"""

    def setUp(self):
        self.result = CaseRunStatusGroupByResult(
            {"PASSED": 20, "ERROR": 0, "FAILED": 10, "IDLE": 50}
        )
        self.empty_result = CaseRunStatusGroupByResult()

    def test_complete_count(self):
        r = self.result
        self.assertEqual(r["PASSED"] + r["ERROR"] + r["FAILED"], r.complete_count)
        self.assertEqual(0, self.empty_result.complete_count)

    def test_failure_count(self):
        r = self.result
        self.assertEqual(r["ERROR"] + r["FAILED"], r.failure_count)
        self.assertEqual(0, self.empty_result.failure_count)

    def test_complete_percent(self):
        r = self.result
        self.assertEqual(
            (r["PASSED"] + r["ERROR"] + r["FAILED"]) * 1.0 / r.total * 100,
            self.result.complete_percent,
        )
        self.assertEqual(0.0, self.empty_result.complete_percent)

    def test_failure_percent_in_complete(self):
        r = self.result
        # It is not stable to compare the equality of two float numbers.
        self.assertEqual(
            round((r["ERROR"] + r["FAILED"]) * 1.0 / r.complete_count * 100, 1),
            round(self.result.failure_percent_in_complete, 1),
        )
        self.assertEqual(0.0, self.empty_result.failure_percent_in_complete)

    def test_failure_percent_in_total(self):
        r = self.result
        self.assertEqual(
            (r["ERROR"] + r["FAILED"]) * 1.0 / r.total * 100,
            self.result.failure_percent_in_total,
        )
        self.assertEqual(0.0, self.empty_result.failure_percent_in_total)


@pytest.mark.parametrize("recipients", [[], ["user@example.com"]])
@pytest.mark.parametrize("cc", [[], ["admin@example.com"]])
@patch("tcms.core.mailto.mailto")
def test_mail_notify(mailto, cc, recipients, caplog):
    caplog.set_level(logging.INFO)
    instance = Mock()
    instance.get_notification_recipients.return_value = recipients
    mail_notify(instance, "mail.templ", "subject", {}, cc=cc)

    if not recipients:
        assert "No recipient is found." in caplog.text
        mailto.assert_not_called()
    else:
        if cc:
            assert "Also cc ['admin@example.com']." in caplog.text
        mailto.assert_called_once_with("mail.templ", "subject", recipients, {}, cc=cc)

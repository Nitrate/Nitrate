# -*- coding: utf-8 -*-
import smtplib
import sys
import unittest
from unittest.mock import patch, Mock

from django import test
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail

from tcms.core import responses
from tcms.core.db import GroupByResult, CaseRunStatusGroupByResult
from tcms.core.utils import string_to_list
from tcms.core.mailto import mailto
from tcms.core.task import AsyncTask
from tcms.core.task import Task
from tcms.management.models import Classification
from tests import HelperAssertions
from tests.factories import TestPlanFactory


PY37 = sys.version_info[:2] == (3, 7)


class TestUtilsFunctions(unittest.TestCase):

    def test_string_to_list(self):
        strings = 'Python,Go,,Perl,Ruby'
        strings_list = ['Python', 'Go', 'Perl', 'Ruby']
        strings_list.sort()
        expected_strings = ['Python', 'Go', 'Perl', 'Ruby']
        expected_strings.sort()

        result = string_to_list(strings_list)
        result.sort()
        self.assertEqual(expected_strings, result)

        result = string_to_list(strings)
        result.sort()
        self.assertEqual(expected_strings, result)

        another_strings = strings.replace(',', '#')
        result = string_to_list(another_strings, '#')
        result.sort()
        self.assertEqual(expected_strings, result)

        strings = 1
        self.assertRaises(AttributeError, string_to_list, strings)

        strings = ()
        self.assertRaises(AttributeError, string_to_list, strings)

        strings = 'abcdefg'
        result = string_to_list(strings)
        self.assertEqual([strings], result)

        strings = 'abcdefg'
        result = string_to_list(strings)
        self.assertEqual([strings], result)

        strings = 'abcdefg'
        result = string_to_list(strings, ':')
        self.assertEqual([strings], result)


class GroupByResultDictLikeTest(unittest.TestCase):
    """Test dict like behaviors"""

    def setUp(self):
        self.groupby_result = GroupByResult({'total': 100})

    def test_in(self):
        self.assertNotIn('a', self.groupby_result)
        self.assertIn('total', self.groupby_result)

    def test_key(self):
        self.assertTrue(self.groupby_result.keys(), ['total'])

    def test_setdefault(self):
        ret_val = self.groupby_result.setdefault('count', {})
        self.assertEqual(ret_val, {})

        ret_val = self.groupby_result.setdefault('total', 200)
        self.assertEqual(ret_val, 100)

    def test_setitem(self):
        self.groupby_result['count'] = 200
        self.assertEqual(self.groupby_result['count'], 200)

        self.groupby_result['total'] = 999
        self.assertEqual(self.groupby_result['total'], 999)

    def test_get(self):
        ret_val = self.groupby_result.get('total')
        self.assertEqual(ret_val, 100)

        ret_val = self.groupby_result.get('count', 999)
        self.assertEqual(ret_val, 999)

        ret_val = self.groupby_result.get('xxx')
        self.assertEqual(ret_val, None)

    def test_len(self):
        self.assertEqual(len(self.groupby_result), 1)

    def test_del(self):
        self.groupby_result['count'] = 200
        del self.groupby_result['total']
        self.assertNotIn('total', self.groupby_result)
        del self.groupby_result['count']
        self.assertNotIn('count', self.groupby_result)
        self.assertEqual(len(self.groupby_result), 0)

    def test_raise_key_error(self):
        with self.assertRaises(KeyError):
            self.groupby_result['unknown_key']


class GroupByResultCalculationTest(unittest.TestCase):
    """Test calculation of GroupByResult"""

    def setUp(self):
        self.groupby_result = GroupByResult({
            1: 100,
            2: 300,
            4: 400,
        })

        self.nested_groupby_result = GroupByResult({
            1: GroupByResult({'a': 1,
                              'b': 2,
                              'c': 3}),
            2: GroupByResult({1: 1,
                              2: 2}),
            3: GroupByResult({'PASSED': 10,
                              'WAIVED': 20,
                              'FAILED': 30,
                              'PAUSED': 40}),
        })

    def _sample_total(self):
        return sum(count for key, count in self.groupby_result.iteritems())

    def _sample_nested_total(self):
        total = 0
        for key, nested_result in self.nested_groupby_result.iteritems():
            for n, count in nested_result.iteritems():
                total += count
        return total

    def test_total(self):
        total = self.groupby_result.total
        self.assertEqual(total, self._sample_total())

    def test_nested_total(self):
        total = self.nested_groupby_result.total
        self.assertEqual(total, self._sample_nested_total())

    def test_get_total_after_add_data_based_on_empty_initial_data(self):
        result = GroupByResult()
        result['RUNNING'] = 100
        result['PASSED'] = 100
        self.assertEqual(200, result.total)

    def test_get_total_after_add_data_based_on_initial_data(self):
        result = GroupByResult({'FAILED': 20})
        result['RUNNING'] = 100
        result['PASSED'] = 100
        self.assertEqual(220, result.total)

    def test_total_is_updated_after_del_item(self):
        result = GroupByResult({'FAILED': 20, 'RUNNING': 20, 'PASSED': 10})
        del result['RUNNING']
        self.assertEqual(30, result.total)

    def test_total_is_updated_after_del_item_several_times(self):
        result = GroupByResult({'FAILED': 20, 'RUNNING': 20, 'PASSED': 10})
        del result['RUNNING']
        del result['FAILED']
        self.assertEqual(10, result.total)

    def test_percentage(self):
        result = GroupByResult({
            'IDLE': 20,
            'PASSED': 20,
            'RUNNING': 10,
        })
        self.assertEqual(40.0, result.PASSED_percent)

    def test_zero_percentage(self):
        result = GroupByResult({})
        self.assertEqual(.0, result.PASSED_percent)

    def test_arithmetic_operation(self):
        result = GroupByResult({'IDLE': 1, 'RUNNING': 1, 'FAILED': 2})
        result['IDLE'] += 1
        result['RUNNING'] += 100
        result['FAILED'] -= 2
        self.assertEqual(2, result['IDLE'])
        self.assertEqual(101, result['RUNNING'])
        self.assertEqual(0, result['FAILED'])


class GroupByResultLevelTest(unittest.TestCase):
    def setUp(self):
        self.levels_groupby_result = GroupByResult({
            'build_1': GroupByResult({
                'plan_1': GroupByResult({
                    'run_1': GroupByResult(
                        {'passed': 1, 'failed': 2, 'error': 3, }),
                    'run_2': GroupByResult(
                        {'passed': 1, 'failed': 2, 'error': 3, }),
                    'run_3': GroupByResult(
                        {'passed': 1, 'failed': 2, 'error': 3, }),
                }),
                'plan_2': GroupByResult({
                    'run_1': GroupByResult(
                        {'passed': 1, 'failed': 2, 'error': 3, }),
                    'run_2': GroupByResult(
                        {'passed': 1, 'failed': 2, 'error': 3, }),
                }),
            }),
            'build_2': GroupByResult({
                'plan_1': GroupByResult({
                    'run_1': GroupByResult(
                        {'passed': 1, 'failed': 2, 'error': 3, }),
                    'run_4': GroupByResult(
                        {'paused': 2, 'failed': 2, 'waived': 6, }),
                    'run_5': GroupByResult(
                        {'paused': 1, 'failed': 2, 'waived': 3, }),
                }),
                'plan_2': GroupByResult({
                    'run_1': GroupByResult(
                        {'passed': 1, 'failed': 2, 'error': 3, }),
                    'run_4': GroupByResult(
                        {'paused': 2, 'failed': 2, 'waived': 6, }),
                    'run_5': GroupByResult(
                        {'paused': 1, 'failed': 2, 'waived': 3, }),
                }),
            }),
        })

    def test_value_leaf_count(self):
        value_leaf_count = self.levels_groupby_result.leaf_values_count()
        self.assertEqual(value_leaf_count, 33)

        value_leaf_count = self.levels_groupby_result[
            'build_1'].leaf_values_count()
        self.assertEqual(value_leaf_count, 15)

        level_node = self.levels_groupby_result['build_2']['plan_2']
        value_leaf_count = level_node.leaf_values_count()
        self.assertEqual(value_leaf_count, 9)

    def test_value_leaf_in_row_count(self):
        value_leaf_count = self.levels_groupby_result.leaf_values_count(
            value_in_row=True)
        self.assertEqual(value_leaf_count, 11)

        level_node = self.levels_groupby_result['build_2']
        value_leaf_count = level_node.leaf_values_count(value_in_row=True)
        self.assertEqual(value_leaf_count, 6)

        level_node = self.levels_groupby_result['build_1']['plan_2']
        value_leaf_count = level_node.leaf_values_count(value_in_row=True)
        self.assertEqual(value_leaf_count, 2)


class VariousResponsesTest(HelperAssertions, unittest.TestCase):
    """Test HttpJSONResponse"""

    def test_json_response_badrequest(self):
        response = responses.JsonResponseBadRequest({})

        self.assert400(response)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_json_response_servererror(self):
        response = responses.JsonResponseServerError({})
        self.assert500(response)
        self.assertEqual(response['Content-Type'], 'application/json')


class TestUrlMixin(test.TestCase):
    """Test UrlMixin"""

    @classmethod
    def setUpTestData(cls):
        cls.plan = TestPlanFactory()

        site = Site.objects.get_current()
        site.domain = 'localhost'
        site.save()

    def test_get_full_url(self):
        url = self.plan.get_full_url()
        expected_url = 'http://localhost/{}'.format(
            self.plan.get_absolute_url())
        self.assertEqual(expected_url, url)

    @patch.object(settings, 'SITE_HTTP_SCHEME', new='', create=True)
    def test_use_default_http_if_option_is_empty(self):
        url = self.plan.get_full_url()
        expected_url = 'http://localhost/{}'.format(
            self.plan.get_absolute_url())
        self.assertEqual(expected_url, url)

    @patch.object(settings, 'SITE_HTTP_SCHEME', new='https', create=True)
    def test_use_correct_configured_scheme(self):
        url = self.plan.get_full_url()
        expected_url = 'https://localhost/{}'.format(
            self.plan.get_absolute_url())
        self.assertEqual(expected_url, url)


class TestAsyncTask(unittest.TestCase):
    """Test async task class Task"""

    def test_disabled(self):
        with patch.object(settings, 'ASYNC_TASK', new=AsyncTask.DISABLED.value):
            func = Mock()
            task = Task(func)
            task(1, a=2)
            func.assert_called_once_with(1, a=2)

    @patch('threading.Thread')
    def test_uses_threading(self, Thread):
        with patch.object(settings, 'ASYNC_TASK', new=AsyncTask.THREADING.value):
            func = Mock()
            task = Task(func)
            task(1, a=2)
            func.assert_not_called()

            Thread.assert_called_once_with(target=func, args=(1,), kwargs={'a': 2})
            thread = Thread.return_value
            self.assertTrue(thread.daemon)
            thread.start.assert_called_once()

    @patch('celery.shared_task')
    def test_uses_celery(self, shared_task):
        with patch.object(settings, 'ASYNC_TASK', new=AsyncTask.CELERY.value):
            func = Mock()
            task = Task(func)
            task(1, a=2)
            func.assert_not_called()

            shared_task.assert_called_once_with(func)
            self.assertEqual(shared_task.return_value, task.target)
            shared_task.return_value.delay.assert_called_once_with(1, a=2)


class TestMailTo(test.SimpleTestCase):
    """Test mailto"""

    def setUp(self) -> None:
        self.get_template_p = patch('tcms.core.mailto.loader.get_template')
        self.mock_get_template = self.get_template_p.start()
        self.mock_get_template.return_value.render.return_value = 'Good news.'

    def tearDown(self) -> None:
        self.get_template_p.stop()

    def test_send_mail(self):
        mailto('mail_template', 'Start Test', ['tester@localhost'])
        self.assertEqual('Start Test', mail.outbox[0].subject)

    def test_also_send_mail_to_addresses_for_debug(self):
        with patch.object(settings, 'DEBUG', new=True):
            with patch.object(settings, 'EMAILS_FOR_DEBUG', new=['cotester@localhost']):
                mailto('mail_template', 'Start Test', ['tester@localhost'])

        self.assertListEqual(
            ['cotester@localhost', 'tester@localhost'],
            sorted(mail.outbox[0].recipients()))

    def test_recipients_accept_non_sequence_value(self):
        mailto('mail_template', 'Start Test', 'tester@localhost')
        self.assertEqual('tester@localhost', mail.outbox[0].recipients()[0])

    @patch('tcms.core.mailto.EmailMessage')
    @patch('tcms.core.mailto.logger')
    def test_log_traceback_when_error_is_raised_from_send(self, logger, EmailMessage):
        EmailMessage.return_value.send.side_effect = smtplib.SMTPException
        mailto('mail_template', 'Start Test', ['tester@localhost'])
        logger.exception.assert_called_once()


class TestModelLogAction(test.TestCase):
    """Test TCMSModel.log_action"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = User.objects.create_user(
            username='tester', email='tester@localhost'
        )
        cls.classification = Classification.objects.create(name='webapp')

    def test_log_action(self):
        # who, new_value, field, original_value
        test_cases = (
            (self.tester, 'new value', None, None),
            (self.tester, 'new value', '', None),
            (self.tester, 'new value', '', ''),
            (self.tester, 'new value', None, ''),
            (self.tester, 'new value', 'field', None),
            (self.tester, 'new value', 'field', 'old value'),
        )

        for log_args in test_cases:
            log = self.classification.log_action(*log_args)

            who, new_value, field, original_value = log_args
            self.assertEqual(who, log.who)
            self.assertEqual(new_value, log.new_value)
            self.assertEqual(field or '', log.field)
            self.assertEqual(original_value or '', log.original_value)


class TestCaseRunStatusGroupbyResult(test.TestCase):
    """Test CaseRunStatusGroupByResult"""

    def setUp(self):
        self.result = CaseRunStatusGroupByResult({
            'PASSED': 20, 'ERROR': 0, 'FAILED': 10, 'IDLE': 50
        })
        self.empty_result = CaseRunStatusGroupByResult()

    def test_complete_count(self):
        r = self.result
        self.assertEqual(r['PASSED'] + r['ERROR'] + r['FAILED'],
                         r.complete_count)
        self.assertEqual(0, self.empty_result.complete_count)

    def test_failure_count(self):
        r = self.result
        self.assertEqual(r['ERROR'] + r['FAILED'], r.failure_count)
        self.assertEqual(0, self.empty_result.failure_count)

    def test_complete_percent(self):
        r = self.result
        self.assertEqual(
            (r['PASSED'] + r['ERROR'] + r['FAILED']) * 1.0 / r.total * 100,
            self.result.complete_percent
        )
        self.assertEqual(.0, self.empty_result.complete_percent)

    def test_failure_percent_in_complete(self):
        r = self.result
        # It is not stable to compare the equality of two float numbers.
        self.assertEqual(
            round((r['ERROR'] + r['FAILED']) * 1.0 / r.complete_count * 100, 1),
            round(self.result.failure_percent_in_complete, 1)
        )
        self.assertEqual(.0, self.empty_result.failure_percent_in_complete)

    def test_failure_percent_in_total(self):
        r = self.result
        self.assertEqual(
            (r['ERROR'] + r['FAILED']) * 1.0 / r.total * 100,
            self.result.failure_percent_in_total
        )
        self.assertEqual(.0, self.empty_result.failure_percent_in_total)

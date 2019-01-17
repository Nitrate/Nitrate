# -*- coding: utf-8 -*-

from itertools import chain
from django.urls import reverse
from six.moves.html_parser import HTMLParser

from tcms.management.models import Priority
from tcms.tests import BaseCaseRun
from tcms.tests.factories import TestPlanFactory, ProductFactory, VersionFactory, TestCaseFactory, TestCaseRunFactory


class SearchResultTableParser(HTMLParser):

    def __init__(self, table_id, td_idx, func=None):
        super(SearchResultTableParser, self).__init__()
        self.table_id = table_id
        self.td_idx = td_idx
        self.func = func

        self.in_table = False
        self.td_cnt = 0
        self.in_td = False
        self.collected_data = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        lower_tag = tag.lower()
        if lower_tag == 'table' and attrs.get('id') == self.table_id:
            self.in_table = True
        elif lower_tag == 'td':
            self.td_cnt += 1
            if self.td_cnt == self.td_idx:
                self.in_td = True

    def handle_endtag(self, tag):
        lower_tag = tag.lower()
        if lower_tag == 'table':
            self.in_table = False
        elif lower_tag == 'td':
            self.in_td = False
        elif lower_tag == 'tr':
            self.td_cnt = 0

    def handle_data(self, data):
        func = self.func if self.func else lambda v: v
        if self.in_table and self.in_td:
            self.collected_data.append(func(data.strip()))


class TestAdvancedSearch(BaseCaseRun):

    @classmethod
    def setUpTestData(cls):
        super(TestAdvancedSearch, cls).setUpTestData()

        cls.cool_product = ProductFactory(name='CoolProduct')
        cls.cool_version = VersionFactory(value='0.1', product=cls.cool_product)

        cls.plan_02 = TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version)

        cls.case_001 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_02])
        cls.case_002 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_02])

        cls.plan_03 = TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.cool_product,
            product_version=cls.cool_version)
        cls.case_003 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_03])
        cls.case_004 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_03])

        # Data for testing combination search
        # Create cases with priority P2 and associate them to cls.test_run
        priority_p2 = Priority.objects.get(value='P2')
        priority_p3 = Priority.objects.get(value='P3')

        cls.case_p2_01 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_03],
            priority=priority_p2)
        TestCaseRunFactory(
            assignee=cls.tester,
            tested_by=cls.tester,
            run=cls.test_run,
            build=cls.build,
            case_run_status=cls.case_run_status_idle,
            case=cls.case_p2_01,
            sortkey=1000)

        # A new case to cls.plan, whose priority is P3.
        cls.case_005 = TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan],
            priority=priority_p3)

        cls.url = reverse('advance_search')

    def test_open_advanced_search_page(self):
        self.client.get(self.url)

    def test_basic_search_plans(self):
        # Note that, asc is not passed, which means to sort by desc order.
        resp = self.client.get(self.url, {
            'pl_product': self.product.pk,
            'order_by': 'name',
            'target': 'plan',
        })

        for plan in [self.plan, self.plan_02]:
            self.assertContains(resp, '<a href="{}">{}</a>'.format(
                plan.get_absolute_url(), plan.pk))

        self.assertNotContains(resp, '<a href="{}">{}</a>'.format(
            self.plan_03.get_absolute_url(), self.plan_03.pk))

        # Summary is in the third column.
        parser = SearchResultTableParser('testplans_table', 3)
        parser.feed(resp.content.decode('utf-8'))

        self.assertListEqual(
            sorted([self.plan_02.name, self.plan.name], reverse=True),
            parser.collected_data)

    def test_basic_search_cases(self):
        resp = self.client.get(self.url, {
            'pl_product': self.product.pk,
            'order_by': 'case_id',
            'asc': True,
            'target': 'case',
        })

        for case in chain(self.plan.case.all(), self.plan_02.case.all()):
            self.assertContains(resp, '<a href="{}">{}</a>'.format(
                case.get_absolute_url(), case.pk))

        for case in self.plan_03.case.all():
            self.assertNotContains(resp, '<a href="{}">{}</a>'.format(
                case.get_absolute_url(), case.pk))

        # Summary is in the third column.
        parser = SearchResultTableParser('testcases_table', 3, int)
        parser.feed(resp.content.decode('utf-8'))

        self.assertListEqual(
            sorted(chain([case.pk for case in self.plan.case.all()],
                         [case.pk for case in self.plan_02.case.all()])),
            parser.collected_data)

    def test_basic_search_runs(self):
        resp = self.client.get(self.url, {
            'pl_product': self.product.pk,
            'order_by': 'run_id',
            'asc': True,
            'target': 'run',
        })

        for run in [self.test_run, self.test_run_1]:
            self.assertContains(resp, '<a href="{}">{}</a>'.format(
                run.get_absolute_url(), run.pk))

        # Summary is in the third column.
        parser = SearchResultTableParser('testruns_table', 2, int)
        parser.feed(resp.content.decode('utf-8'))

        self.assertListEqual([self.test_run.pk, self.test_run_1.pk],
                             parser.collected_data)

    def test_combination_search_runs_and_cases(self):
        """Test search runs whose cases' priority is P2"""

        resp = self.client.get(self.url, {
            'pl_product': self.product.pk,
            'cs_priority': '2',
            'target': 'run',
        })

        self.assertContains(resp, '<a href="{}">{}</a>'.format(
            self.test_run.get_absolute_url(), self.test_run.pk))

        self.assertNotContains(resp, '<a href="{}">{}</a>'.format(
            self.test_run_1.get_absolute_url(), self.test_run_1.pk))

    def test_combination_search_plans_and_cases(self):
        """Test search plans whose cases' priority is P3"""

        resp = self.client.get(self.url, {
            'pl_product': self.product.pk,
            'cs_priority': '3',
            'target': 'plan',
        })

        self.assertContains(resp, '<a href="{}">{}</a>'.format(
            self.plan.get_absolute_url(), self.plan.pk))

        self.assertNotContains(resp, '<a href="{}">{}</a>'.format(
            self.plan_03.get_absolute_url(), self.plan_03.pk))

    def test_error(self):
        resp = self.client.get(self.url, {
            'pl_product': self.product.pk,
            # wrong priority value, which is not in valid range.
            'cs_priority': '100',
            'target': 'case',
        })

        self.assertContains(resp, '<li>Errors -</li>')
        self.assertContains(
            resp, '<li>Case Priority: Select a valid choice. 100 is not one of'
                  ' the available choices.</li>')

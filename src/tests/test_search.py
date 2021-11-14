# -*- coding: utf-8 -*-

from itertools import chain

from bs4 import BeautifulSoup
from django.urls import reverse

from tcms.management.models import Priority
from tests import BaseCaseRun
from tests import factories as f


class TestAdvancedSearch(BaseCaseRun):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.cool_product = f.ProductFactory(name="CoolProduct")
        cls.cool_version = f.VersionFactory(value="0.1", product=cls.cool_product)

        cls.env_group_db = f.TCMSEnvGroupFactory(name="db")

        cls.plan_02 = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product,
            product_version=cls.version,
            env_group=[cls.env_group_db],
        )

        cls.case_001 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_02],
        )
        cls.case_002 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_02],
        )

        cls.plan_03 = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.cool_product,
            product_version=cls.cool_version,
        )
        cls.case_003 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_03],
        )
        cls.case_004 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_03],
        )

        # Data for testing combination search
        # Create cases with priority P2 and associate them to cls.test_run
        priority_p2 = Priority.objects.get(value="P2")
        priority_p3 = Priority.objects.get(value="P3")

        cls.case_p2_01 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan_03],
            priority=priority_p2,
        )
        f.TestCaseRunFactory(
            assignee=cls.tester,
            tested_by=cls.tester,
            run=cls.test_run,
            build=cls.build,
            case_run_status=cls.case_run_status_idle,
            case=cls.case_p2_01,
            sortkey=1000,
        )

        # A new case to cls.plan, whose priority is P3.
        cls.case_005 = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan],
            priority=priority_p3,
        )

        # Test run for asserting env_group column
        cls.test_run_with_env_group = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan_02,
            build=cls.build,
            manager=cls.tester,
            default_tester=cls.tester,
        )

        cls.url = reverse("advanced-search")

    def test_open_advanced_search_page(self):
        self.client.get(self.url)

    def test_basic_search_plans(self):
        # Note that, asc is not passed, which means to sort by pk in desc order.
        resp = self.client.get(
            self.url,
            {
                "pl_product": self.product.pk,
                "target": "plan",
            },
        )

        for plan in [self.plan, self.plan_02]:
            self.assertContains(
                resp, '<a href="{}">{}</a>'.format(plan.get_absolute_url(), plan.pk)
            )

        self.assertNotContains(
            resp,
            '<a href="{}">{}</a>'.format(self.plan_03.get_absolute_url(), self.plan_03.pk),
        )

        plan_names = []
        bs = BeautifulSoup(resp.content.decode("utf-8"), "html.parser")
        # Skip first header row
        for tr in bs.find(id="testplans_table").find_all("tr")[1:]:
            # The 3rd td contains name
            plan_names.append(tr.find_all("td")[2].a.text.strip())

        self.assertListEqual([self.plan_02.name, self.plan.name], plan_names)

    def test_basic_search_cases(self):
        resp = self.client.get(
            self.url,
            {
                "pl_product": self.product.pk,
                "order_by": "case_id",
                "asc": True,
                "target": "case",
            },
        )

        for case in chain(self.plan.case.all(), self.plan_02.case.all()):
            self.assertContains(
                resp, '<a href="{}">{}</a>'.format(case.get_absolute_url(), case.pk)
            )

        for case in self.plan_03.case.all():
            self.assertNotContains(
                resp, '<a href="{}">{}</a>'.format(case.get_absolute_url(), case.pk)
            )

        case_ids = []
        bs = BeautifulSoup(resp.content.decode("utf-8"), "html.parser")
        for tr in bs.find(id="testcases_table").find_all("tr")[1:]:
            if "case_content" in tr["class"]:
                # Ignore the hidden row (td), which is used to show case details.
                continue
            case_ids.append(int(tr.find_all("td")[2].a.text.strip()))

        self.assertListEqual(
            sorted(
                chain(
                    [case.pk for case in self.plan.case.all()],
                    [case.pk for case in self.plan_02.case.all()],
                ),
                reverse=True,
            ),
            case_ids,
        )

    def test_basic_search_runs(self):
        resp = self.client.get(
            self.url,
            {
                "pl_product": self.product.pk,
                "order_by": "run_id",
                "asc": True,
                "target": "run",
            },
        )
        bs = BeautifulSoup(resp.content.decode("utf-8"), "html.parser")

        for run in [self.test_run, self.test_run_1]:
            self.assertContains(resp, '<a href="{}">{}</a>'.format(run.get_absolute_url(), run.pk))

        run_ids = []
        for tr in bs.find(id="testruns_table").find_all("tr")[1:]:
            run_ids.append(int(tr.find_all("td")[1].a.text.strip()))

        expected_run_ids = sorted(
            [self.test_run.pk, self.test_run_1.pk, self.test_run_with_env_group.pk],
            reverse=True,
        )
        self.assertListEqual(expected_run_ids, run_ids)

        # Collect data from env_group (Environment) column
        env_group_names = []
        for tr in bs.find(id="testruns_table").find_all("tr")[1:]:
            env_group_names.append(tr.find_all("td")[7].text.strip())

        self.assertListEqual(["db", "None", "None"], env_group_names)

    def test_combination_search_runs_and_cases(self):
        """Test search runs whose cases' priority is P2"""

        resp = self.client.get(
            self.url,
            {
                "pl_product": self.product.pk,
                "cs_priority": "2",
                "target": "run",
            },
        )

        self.assertContains(
            resp,
            '<a href="{}">{}</a>'.format(self.test_run.get_absolute_url(), self.test_run.pk),
        )

        self.assertNotContains(
            resp,
            '<a href="{}">{}</a>'.format(self.test_run_1.get_absolute_url(), self.test_run_1.pk),
        )

    def test_combination_search_plans_and_cases(self):
        """Test search plans whose cases' priority is P3"""

        resp = self.client.get(
            self.url,
            {
                "pl_product": self.product.pk,
                "cs_priority": "3",
                "target": "plan",
            },
        )

        self.assertContains(
            resp,
            '<a href="{}">{}</a>'.format(self.plan.get_absolute_url(), self.plan.pk),
        )

        self.assertNotContains(
            resp,
            '<a href="{}">{}</a>'.format(self.plan_03.get_absolute_url(), self.plan_03.pk),
        )

    def test_error(self):
        resp = self.client.get(
            self.url,
            {
                "pl_product": self.product.pk,
                # wrong priority value, which is not in valid range.
                "cs_priority": "100",
                "target": "case",
            },
        )

        self.assertContains(resp, "<li>Errors -</li>")
        self.assertContains(
            resp,
            "<li>Case Priority: Select a valid choice. 100 is not one of"
            " the available choices.</li>",
        )

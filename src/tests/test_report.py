# -*- coding: utf-8 -*-

from datetime import datetime

from django.db.models import Max
from django.urls import reverse

from tcms.management.models import Product, TestBuild
from tcms.testcases.models import TestCase
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestCaseRunStatus, TestRun
from tests import BaseCaseRun
from tests import factories as f


class TestReportOverall(BaseCaseRun):
    """Test /report/overall/"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product_a = f.ProductFactory(name="producta")
        cls.product_b = f.ProductFactory(name="productb")

    def test_overall(self):
        response = self.client.get(reverse("report-overall"))

        content = [
            '<td><a href="{}">{}</a></td><td>{}</td><td>{}</td><td>{}</td>'.format(
                reverse("report-overview", args=[self.product.pk]),
                self.product.name,
                TestPlan.objects.filter(product=self.product).count(),
                TestRun.objects.filter(plan__product=self.product).count(),
                TestCase.objects.filter(plan__product=self.product).count(),
            ),
            "<td>producta</td><td>0</td><td>0</td><td>0</td>",
            "<td>productb</td><td>0</td><td>0</td><td>0</td>",
        ]

        for item in content:
            self.assertContains(response, item, html=True)


class TestProductOverview(BaseCaseRun):
    """Test /report/product/$id/overview/"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        tcrs_get = TestCaseRunStatus.objects.get
        cls.status_idle = tcrs_get(name="IDLE")
        cls.status_running = tcrs_get(name="RUNNING")
        cls.status_passed = tcrs_get(name="PASSED")
        cls.status_failed = tcrs_get(name="FAILED")

        # Test data:
        # Runs: total(2), running(1), finished(1)
        # Case Runs: total(6), idle(2), running(1), passed(2), failed(1)

        cls.test_run_1.stop_date = datetime.now()
        cls.test_run_1.save()

        cls.case_run_1.case_run_status = cls.status_running
        cls.case_run_4.case_run_status = cls.status_passed
        cls.case_run_5.case_run_status = cls.status_passed
        cls.case_run_6.case_run_status = cls.status_failed

        cls.case_run_1.save()
        cls.case_run_4.save()
        cls.case_run_5.save()
        cls.case_run_6.save()

        cls.product_overview_url = reverse("report-overview", args=[cls.product.pk])

    def test_404_if_specified_product_does_not_exist(self):
        qs = Product.objects.aggregate(max_pk=Max("pk"))
        url = reverse("report-overview", args=[qs["max_pk"] + 1])
        self.assert404(self.client.get(url))

    def test_show_overview(self):
        resp = self.client.get(self.product_overview_url)

        case_runs_subtotal = (
            # Runs
            ("Finished", 1, 50.0),
            ("Running", 1, 50.0),
            # Case runs
            ("PASSED", 2, 33.3),
            ("FAILED", 1, 16.7),
            ("IDLE", 2, 33.3),
            ("ERROR", 0, 0),
            ("PAUSED", 0, 0),
            ("BLOCKED", 0, 0),
            ("RUNNING", 1, 16.7),
            ("WAIVED", 0, 0),
        )

        for item_name, subtotal_count, percent in case_runs_subtotal:
            self.assertContains(
                resp,
                "<tr><td>{}</td><td>{}</td><td>{}%</td></tr>".format(
                    item_name, subtotal_count, percent
                ),
                html=True,
            )


class TestOverallProductByBuilds(BaseCaseRun):
    """Test /report/product/$id/build/"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.url = reverse("report-overall-product-build", args=[cls.product.pk])

        # Test data:
        #
        # Product(1), associated TestBuild(2): cls.build and cls.product.build
        # Runs(2): cls.build has 2, cls.product.build has 0
        #   Both of runs are in running
        #   Case runs: 6
        #   FAILED case runs: 2
        #   RUNNING case runs: 1
        #   PASSED case runs: 1
        #   Rest 2 case runs: IDLE

        tcrs_get = TestCaseRunStatus.objects.get
        cls.status_running = tcrs_get(name="RUNNING")
        cls.status_passed = tcrs_get(name="PASSED")
        cls.status_failed = tcrs_get(name="FAILED")

        for case_run, status in (
            (cls.case_run_1, cls.status_failed),
            (cls.case_run_2, cls.status_failed),
            (cls.case_run_4, cls.status_running),
            (cls.case_run_6, cls.status_passed),
        ):
            case_run.case_run_status = status
            case_run.save()

    def test_404_if_specified_product_does_not_exist(self):
        qs = Product.objects.aggregate(max_pk=Max("pk"))
        url = reverse("report-overall-product-build", args=[qs["max_pk"] + 1])
        self.assert404(self.client.get(url))

    def test_404_if_query_nonexisting_build_for_details(self):
        qs = TestBuild.objects.aggregate(max_pk=Max("pk"))
        self.assert404(self.client.get(self.url, data={"build_id": qs["max_pk"] + 1}))

    def test_by_builds(self):
        resp = self.client.get(self.url)

        stats = (
            (
                f'<a href="?build_id={self.build.pk}">{self.build.name}</a>',
                "<p>0/2</p>",
                "50.0",
                '<div class="strong emphasize">2 Failed</div>',
            ),
            (
                '<a href="?build_id={}">{}</a>'.format(
                    self.product.build.get(name="unspecified").pk, "unspecified"
                ),
                "<p>0/0</p>",
                "0",
                "",
            ),
        )

        for col_build, col_runs, col_case_runs, col_failed_case_runs in stats:
            self.assertContains(
                resp,
                """\
<tr>
    <td class="variety_0">{0}</td>
    <td class="variety_1">{1}</td>
    <td class="variety_4">
        <div class="progress-bar">
            <div class="progress-inner" style="width:{2}%">
                <div class="percent">{2}%</div>
            </div>
        </div>
    </td>
    <td>{3}</td>
</tr>
""".format(
                    col_build, col_runs, col_case_runs, col_failed_case_runs
                ),
                html=True,
            )

    def test_show_case_runs_subtotal_by_one_build(self):
        resp = self.client.get(self.url, data={"build_id": self.build.pk})

        data = (
            ("BLOCKED", 0, 0),
            ("ERROR", 0, 0),
            ("FAILED", 2, 33.3),
            ("IDLE", 2, 33.3),
            ("PASSED", 1, 16.7),
            ("PAUSED", 0, 0),
            ("RUNNING", 1, 16.7),
            ("WAIVED", 0, 0),
        )

        for status_name, count, percent in data:
            self.assertContains(
                resp,
                '<tr class="variety_{}">'
                "<td>{}</td><td>{}</td><td>{}%</td></tr>".format(
                    status_name.lower(), status_name, count, percent
                ),
                html=True,
            )

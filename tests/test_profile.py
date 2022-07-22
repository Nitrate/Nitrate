# -*- coding: utf-8 -*-

from functools import partial
from textwrap import dedent

from django.urls import reverse

from tcms.testruns.models import TestCaseRunStatus
from tests import BaseCaseRun
from tests import factories as f


class TestRecentPage(BaseCaseRun):
    """Test recent page"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        create_case = partial(
            f.TestCaseFactory,
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_confirmed,
            plan=[cls.plan],
        )

        cls.case_7 = create_case()
        cls.case_8 = create_case()

        create_run_case = partial(
            f.TestCaseRunFactory,
            assignee=cls.tester,
            tested_by=cls.tester,
            build=cls.build,
            case_run_status=cls.case_run_status_idle,
            sortkey=100,
        )
        cls.case_run_7 = create_run_case(case=cls.case_7, run=cls.test_run)
        cls.case_run_8 = create_run_case(case=cls.case_8, run=cls.test_run_1)

        # Create another test plan
        cls.product_foo = f.ProductFactory(name="foo")
        cls.foo_version = f.VersionFactory(value="0.1", product=cls.product_foo)

        cls.plan_1 = f.TestPlanFactory(
            author=cls.tester,
            owner=cls.tester,
            product=cls.product_foo,
            product_version=cls.foo_version,
        )

        # So far, the data have
        # Test plans: 1, test cases: 9, test runs: 2, test case runs: 8
        # Test run 1 with 3 case runs associated with case 1, 2, 3, 7
        # Test run 1 with 3 case runs associated with case 4, 5, 6, 8
        # A new test plan without associated cases and runs

        # Now, set data for testing data

        status_error = TestCaseRunStatus.objects.get(name="ERROR")
        status_failed = TestCaseRunStatus.objects.get(name="FAILED")
        status_idle = TestCaseRunStatus.objects.get(name="IDLE")
        status_passed = TestCaseRunStatus.objects.get(name="PASSED")
        status_waived = TestCaseRunStatus.objects.get(name="WAIVED")

        # Set case runs' status for the first test run
        # All in complete statuses
        cls.case_run_1.case_run_status = status_waived
        cls.case_run_1.save()
        cls.case_run_2.case_run_status = status_failed
        cls.case_run_2.save()
        cls.case_run_3.case_run_status = status_error
        cls.case_run_3.save()
        cls.case_run_7.case_run_status = status_passed
        cls.case_run_7.save()

        # Set case runs' status for the second test run
        cls.case_run_4.case_run_status = status_passed
        cls.case_run_4.save()
        cls.case_run_5.case_run_status = status_error
        cls.case_run_5.save()
        cls.case_run_6.case_run_status = status_failed
        cls.case_run_6.save()
        cls.case_run_8.case_run_status = status_idle
        cls.case_run_8.save()

    def test_open_recent(self):
        url = reverse("user-recent", args=[self.tester.username])
        resp = self.client.get(url)
        self.assert_test_runs_list(resp)
        self.assert_test_plans_list(resp)

    def assert_test_runs_list(self, response):
        expected_runs = (
            # test run 1
            (
                dedent(
                    """
                <div class="progress-bar" style="float:none">
                    <div class="percent">100.0%</div>
                    <div class="progress-inner" style="width:100.0%;">
                        <div class="progress-failed" style="width:25.0%;">
                        </div>
                    </div>
                </div>
                """
                ),
                '<a class="link" href="{}">{}</a>'.format(
                    reverse("run-get", args=[self.test_run.pk]), self.test_run.summary
                ),
            ),
            # test run 2
            (
                dedent(
                    """
                <div class="progress-bar" style="float:none">
                    <div class="percent">75.0%</div>
                    <div class="progress-inner" style="width:75.0%;">
                        <div class="progress-failed" style="width:25.0%;">
                        </div>
                    </div>
                </div>
                """
                ),
                '<a class="link" href="{}">{}</a>'.format(
                    reverse("run-get", args=[self.test_run_1.pk]),
                    self.test_run_1.summary,
                ),
            ),
        )

        for expected_progress, expected_summary in expected_runs:
            self.assertContains(response, expected_progress, html=True)
            self.assertContains(response, expected_summary, html=True)

        self.assertContains(response, "2 test run(s) related to you need to be run")

    def assert_test_plans_list(self, response):
        self.assertContains(response, "You manage 2 test plan(s), 0 test plan(s) disabled")

        for plan, expected_runs_count in ((self.plan_1, 0), (self.plan, 2)):
            plan_url = plan.get_absolute_url()
            self.assertContains(
                response,
                f'<td height="27"><a class="link" href="{plan_url}">{plan.name}</a></td>',
                html=True,
            )
            self.assertContains(response, f"<td>{plan.product.name}</td>", html=True)
            self.assertContains(response, f"<td>{plan.type}</td>", html=True)
            self.assertContains(
                response,
                f'<td><a href="/runs/?plan={plan.pk}">{expected_runs_count}</a></td>',
                html=True,
            )

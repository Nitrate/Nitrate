# -*- coding: utf-8 -*-

import csv
import json
import os
import tempfile
from datetime import datetime, timedelta
from http import HTTPStatus
from operator import attrgetter
from typing import List, Union
from unittest.mock import patch
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max, QuerySet
from django.urls import reverse
from django.utils import formats
from django_comments.models import Comment

from tcms.issuetracker.models import Issue
from tcms.linkreference.models import create_link
from tcms.testruns.models import TCMSEnvRunValueMap, TestCaseRun, TestCaseRunStatus, TestRun
from tests import BaseCaseRun, BasePlanCase
from tests import factories as f
from tests import user_should_have_perm


class TestOrderCases(BaseCaseRun):
    """Test view method order_case"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_404_if_run_does_not_exist(self):
        nonexisting_run_pk = TestRun.objects.count() + 1
        url = reverse("run-order-case", args=[nonexisting_run_pk])
        response = self.client.post(url)
        self.assert404(response)

    def test_prompt_if_no_case_run_is_passed(self):
        url = reverse("run-order-case", args=[self.test_run.pk])
        response = self.client.post(url)
        self.assertIn(b"At least one case is required by re-oder in run", response.content)

    def test_order_case_runs(self):
        url = reverse("run-order-case", args=[self.test_run.pk])
        response = self.client.post(
            url,
            {"case_run": [self.case_run_1.pk, self.case_run_2.pk, self.case_run_3.pk]},
        )

        redirect_to = reverse("run-get", args=[self.test_run.pk])
        self.assertRedirects(response, redirect_to)

        test_sortkeys = [
            TestCaseRun.objects.get(pk=self.case_run_1.pk).sortkey,
            TestCaseRun.objects.get(pk=self.case_run_2.pk).sortkey,
            TestCaseRun.objects.get(pk=self.case_run_3.pk).sortkey,
        ]
        self.assertEqual([10, 20, 30], test_sortkeys)


class TestGetRun(BaseCaseRun):
    """Test get view method"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_404_if_non_existing_pk(self):
        url = reverse("run-get", args=[99999999])
        response = self.client.get(url)
        self.assert404(response)

    def test_get_a_run(self):
        url = reverse("run-get", args=[self.test_run.pk])
        response = self.client.get(url)

        self.assert200(response)

        for i, case_run in enumerate((self.case_run_1, self.case_run_2, self.case_run_3), 1):
            self.assertContains(
                response,
                '<a href="#caserun_{0}">#{0}</a>'.format(case_run.pk),
                html=True,
            )
            self.assertContains(
                response,
                '<a id="link_{}" href="#caserun_{}" title="Expand test case">{}</a>'.format(
                    i, case_run.pk, case_run.case.summary
                ),
                html=True,
            )


class TestCreateNewRun(BasePlanCase):
    """Test creating new run"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = "testruns.add_testrun"
        user_should_have_perm(cls.tester, cls.permission)

        cls.url = reverse("run-new")
        cls.build_fast = f.TestBuildFactory(name="fast", product=cls.product)

    def test_refuse_if_missing_plan_pk(self):
        response = self.client.post(self.url, {})
        self.assertRedirects(response, reverse("plans-all"))

    def test_refuse_if_missing_cases_pks(self):
        response = self.client.post(self.url, {"from_plan": self.plan.pk})
        self.assertContains(response, "At least one case is required by a run.")

    def test_show_create_new_run_page(self):
        response = self.client.post(
            self.url,
            {
                "from_plan": self.plan.pk,
                "case": [self.case_1.pk, self.case_2.pk, self.case_3.pk],
            },
        )

        # Assert listed cases
        for i, case in enumerate((self.case_1, self.case_2, self.case_3), 1):
            self.assertContains(response, '<a href="/case/{0}/">{0}</a>'.format(case.pk), html=True)
            self.assertContains(
                response,
                '<a id="link_{0}" class="blind_title_link js-case-summary" '
                'data-param="{0}">{1}</a>'.format(i, case.summary),
                html=True,
            )

    def test_create_a_new_run(self):
        clone_data = {
            "summary": self.plan.name,
            "from_plan": self.plan.pk,
            "product": self.product.pk,
            "product_version": self.version.pk,
            "build": self.build_fast.pk,
            "manager": self.tester.email,
            "default_tester": self.tester.email,
            "estimated_time": "0m",
            "notes": "Clone new run",
            "case": [self.case_1.pk, self.case_2.pk],
            "do": "clone_run",
            "POSTING_TO_CREATE": "YES",
        }

        url = reverse("run-new")
        response = self.client.post(url, clone_data)

        new_run = TestRun.objects.last()

        self.assertRedirects(response, reverse("run-get", args=[new_run.pk]))

        self.assertEqual(self.plan.name, new_run.summary)
        self.assertEqual(self.plan, new_run.plan)
        self.assertEqual(self.version, new_run.product_version)
        self.assertEqual(None, new_run.stop_date)
        self.assertEqual("Clone new run", new_run.notes)
        self.assertEqual(0, new_run.plan_text_version)
        self.assertEqual(timedelta(0), new_run.estimated_time)
        self.assertEqual(self.build_fast, new_run.build)
        self.assertEqual(self.tester, new_run.manager)
        self.assertEqual(self.tester, new_run.default_tester)

        for case, case_run in zip((self.case_1, self.case_2), new_run.case_run.order_by("pk")):
            self.assertEqual(case, case_run.case)
            self.assertEqual(None, case_run.tested_by)
            self.assertEqual(self.tester, case_run.assignee)
            self.assertEqual(TestCaseRunStatus.objects.get(name="IDLE"), case_run.case_run_status)
            self.assertEqual(0, case_run.case_text_version)
            self.assertEqual(new_run.build, case_run.build)
            self.assertEqual(new_run.environment_id, case_run.environment_id)
            self.assertEqual(None, case_run.running_date)
            self.assertEqual(None, case_run.close_date)


class CloneRunBaseTest(BaseCaseRun):
    def assert_one_run_clone_page(self, response):
        """Verify clone page for cloning one test run"""

        self.assertContains(
            response,
            '<input id="id_summary" maxlength="255" name="summary" '
            'required type="text" value="{}" />'.format(self.test_run.summary),
            html=True,
        )

        for forloop_counter, case_run in enumerate((self.case_run_1, self.case_run_2), 1):
            self.assertContains(
                response,
                '<a href="/case/{0}/">{0}</a>'.format(case_run.case.pk),
                html=True,
            )
            self.assertContains(response, f"<td>{case_run.case.summary}</td>", html=True)


class TestStartCloneRunFromRunPage(CloneRunBaseTest):
    """Test case for cloning run from a run page"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.permission = "testruns.add_testrun"
        user_should_have_perm(cls.tester, cls.permission)

    def test_refuse_without_selecting_case_runs(self):
        url = reverse("run-clone", args=[self.test_run.pk])

        response = self.client.post(url, {})

        self.assertContains(response, "At least one case is required by a run")

    def test_open_clone_page_by_selecting_case_runs(self):
        url = reverse("run-clone", args=[self.test_run.pk])

        response = self.client.post(url, {"case_run": [self.case_run_1.pk, self.case_run_2.pk]})

        self.assert_one_run_clone_page(response)

    def assert_clone_a_run(self, reserve_status=False, reserve_assignee=True):
        new_summary = "Clone {} - {}".format(self.test_run.pk, self.test_run.summary)

        clone_data = {
            "summary": new_summary,
            "from_plan": self.plan.pk,
            "product_id": self.test_run.plan.product_id,
            "do": "clone_run",
            "orig_run_id": self.test_run.pk,
            "POSTING_TO_CREATE": "YES",
            "product": self.test_run.plan.product_id,
            "product_version": self.test_run.product_version.pk,
            "build": self.test_run.build.pk,
            "manager": self.test_run.manager.email,
            "default_tester": self.test_run.default_tester.email,
            "estimated_time": "0m",
            "notes": "",
            "case": [self.case_run_1.case.pk, self.case_run_2.case.pk],
            "case_run_id": [self.case_run_1.pk, self.case_run_2.pk],
        }

        # Set clone settings

        if reserve_status:
            clone_data["keep_status"] = "on"
        if reserve_assignee:
            clone_data["keep_assignee"] = "on"

        url = reverse("run-new")
        response = self.client.post(url, clone_data)

        cloned_run = TestRun.objects.get(summary=new_summary)

        self.assertRedirects(response, reverse("run-get", args=[cloned_run.pk]))

        self.assert_cloned_run(
            self.test_run,
            cloned_run,
            reserve_status=reserve_status,
            reserve_assignee=reserve_assignee,
        )

    def assert_cloned_run(
        self, origin_run, cloned_run, reserve_status=False, reserve_assignee=True
    ):
        # Assert clone settings result
        for origin_case_run, cloned_case_run in zip(
            (self.case_run_1, self.case_run_2), cloned_run.case_run.order_by("pk")
        ):
            if not reserve_status and not reserve_assignee:
                self.assertEqual(
                    TestCaseRunStatus.objects.get(name="IDLE"),
                    cloned_case_run.case_run_status,
                )
                self.assertEqual(origin_case_run.assignee, cloned_case_run.assignee)
                continue

            if reserve_status and reserve_assignee:
                self.assertEqual(origin_case_run.case_run_status, cloned_case_run.case_run_status)
                self.assertEqual(origin_case_run.assignee, cloned_case_run.assignee)
                continue

            if reserve_status and not reserve_assignee:
                self.assertEqual(origin_case_run.case_run_status, cloned_case_run.case_run_status)

                if origin_case_run.case.default_tester is not None:
                    expected_assignee = origin_case_run.case.default_tester
                else:
                    expected_assignee = self.test_run.default_tester

                self.assertEqual(expected_assignee, cloned_case_run.assignee)

                continue

            if not reserve_status and reserve_assignee:
                self.assertEqual(
                    TestCaseRunStatus.objects.get(name="IDLE"),
                    cloned_case_run.case_run_status,
                )
                self.assertEqual(origin_case_run.assignee, cloned_case_run.assignee)

    def test_clone_a_run_with_default_clone_settings(self):
        self.assert_clone_a_run()

    def test_clone_a_run_by_reserving_status(self):
        self.assert_clone_a_run(reserve_status=True, reserve_assignee=False)

    def test_clone_a_run_by_reserving_both_status_assignee(self):
        self.assert_clone_a_run(reserve_status=True, reserve_assignee=True)

    def test_clone_a_run_by_not_reserve_both_status_assignee(self):
        self.assert_clone_a_run(reserve_status=False, reserve_assignee=False)


class TestStartCloneRunFromRunsSearchPage(CloneRunBaseTest):
    """Test case for cloning runs from runs search result page"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.clone_url = reverse("runs-clone")
        cls.permission = "testruns.add_testrun"

        cls.origin_run = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            build=cls.build,
            manager=cls.tester,
            default_tester=cls.tester,
        )

        for tag_name in ("python", "nitrate", "django"):
            cls.origin_run.add_tag(f.TestTagFactory(name=tag_name))

        for cc in (
            User.objects.create_user(username="run_tester1", email="run_tester1@example.com"),
            User.objects.create_user(username="run_tester2", email="run_tester2@example.com"),
            User.objects.create_user(username="run_tester3", email="run_tester3@example.com"),
        ):
            cls.origin_run.add_cc(cc)

        cls.property = f.TCMSEnvPropertyFactory(name="lang")
        for value in ("python", "perl", "ruby"):
            cls.origin_run.add_env_value(f.TCMSEnvValueFactory(value=value, property=cls.property))

        cls.case_2.add_text(action="action", effect="effect", setup="setup", breakdown="breakdown")
        cls.case_2.add_text(
            action="action2", effect="effect2", setup="setup2", breakdown="breakdown2"
        )

        for case in (cls.case_1, cls.case_2):
            f.TestCaseRunFactory(
                assignee=cls.tester,
                tested_by=cls.tester,
                build=cls.build,
                sortkey=10,
                case_run_status=cls.case_run_status_idle,
                run=cls.origin_run,
                case=case,
            )

    def test_refuse_clone_without_selecting_runs(self):
        response = self.client.get(self.clone_url, {})

        self.assertContains(response, "At least one run is required")

    def test_open_clone_page_by_selecting_only_one_run(self):
        response = self.client.get(self.clone_url, {"run": self.test_run.pk})

        self.assert_one_run_clone_page(response)

    def test_open_clone_page_by_selecting_multiple_runs(self):
        runs = [self.test_run_1, self.test_run]
        response = self.client.get(self.clone_url, {"run": [item.pk for item in runs]})

        runs_li = [
            "<li>"
            '<label for="id_run_{}">'
            '<input checked id="id_run_{}" name="run" value="{}" '
            'type="checkbox">'
            "{}"
            "</label>"
            "</li>".format(i, i, item.pk, item.summary)
            for i, item in enumerate(runs)
        ]
        runs_ul = '<ul id="id_run">{}</ul>'.format("".join(runs_li))

        self.assertContains(response, runs_ul, html=True)

        # Assert clone settings
        clone_settings_controls = [
            '<li><input checked id="id_update_case_text" name="update_case_text" '
            'type="checkbox">Use newest case text(setup/actions/effects/breakdown)</li>',
            '<li><input checked id="id_clone_cc" name="clone_cc" type="checkbox">' "Clone cc</li>",
            '<li><input checked id="id_clone_tag" name="clone_tag" type="checkbox">'
            "Clone tag</li>",
        ]
        for html_control in clone_settings_controls:
            self.assertContains(response, html_control, html=True)

    def test_clone_one_selected_run_with_default_clone_settings(self):
        self.assert_clone_runs([self.origin_run])

    def test_clone_one_selected_run_without_cloning_cc(self):
        self.assert_clone_runs([self.origin_run], clone_cc=False)

    def test_clone_one_selected_run_without_cloning_tag(self):
        self.assert_clone_runs([self.origin_run], clone_tag=False)

    def test_clone_one_selected_run_not_use_newest_case_text(self):
        self.assert_clone_runs([self.origin_run], update_case_text=False)

    def test_clone_all_selected_runs_with_default_clone_settings(self):
        self.assert_clone_runs([self.test_run, self.origin_run])

    def test_clone_all_selected_runs_without_cloning_cc(self):
        self.assert_clone_runs([self.test_run, self.origin_run], clone_cc=False)

    def test_clone_all_selected_runs_without_cloning_tag(self):
        self.assert_clone_runs([self.test_run, self.origin_run], clone_tag=False)

    def test_clone_one_selected_runs_not_use_newest_case_text(self):
        self.assert_clone_runs([self.test_run, self.origin_run], update_case_text=False)

    def assert_clone_runs(
        self, runs_to_clone, clone_cc=True, clone_tag=True, update_case_text=True
    ):
        """Test only clone the selected one run from runs/clone/"""
        original_runs_count = TestRun.objects.count()

        post_data = {
            "run": [run.pk for run in runs_to_clone],
            "product": self.origin_run.plan.product.pk,
            "product_version": self.origin_run.product_version.pk,
            "build": self.origin_run.build.pk,
            "manager": self.tester.username,
            "default_tester": self.tester.username,
            "submit": "Clone",
            # Clone settings
            # Do not update manager
            "update_default_tester": "on",
        }

        if clone_cc:
            post_data["clone_cc"] = "on"
        if clone_tag:
            post_data["clone_tag"] = "on"
        if update_case_text:
            post_data["update_case_text"] = "on"

        response = self.client.post(self.clone_url, post_data)

        self.assertEqual(len(runs_to_clone), TestRun.objects.count() - original_runs_count)

        cloned_runs = list(TestRun.objects.order_by("pk"))[-len(runs_to_clone) :]

        if len(cloned_runs) == 1:
            # Finally, redirect to the new cloned test run
            self.assertRedirects(response, reverse("run-get", args=[cloned_runs[0].pk]))
        else:
            self.assert302(response)

        # Currently, runs are not cloned by the order of passed-in runs id. So,
        # ordering by summary to assert equality.
        for origin_run, cloned_run in zip(
            sorted(runs_to_clone, key=attrgetter("summary")),
            sorted(cloned_runs, key=attrgetter("summary")),
        ):
            self.assert_cloned_run(
                origin_run,
                cloned_run,
                clone_cc=clone_cc,
                clone_tag=clone_tag,
                use_newest_case_text=update_case_text,
            )

    def assert_cloned_run(
        self,
        origin_run,
        cloned_run,
        clone_cc=True,
        clone_tag=True,
        use_newest_case_text=True,
    ):
        self.assertEqual(origin_run.product_version, cloned_run.product_version)
        self.assertEqual(origin_run.plan_text_version, cloned_run.plan_text_version)
        self.assertEqual(origin_run.summary, cloned_run.summary)
        self.assertEqual(origin_run.notes, cloned_run.notes)
        self.assertEqual(origin_run.estimated_time, cloned_run.estimated_time)
        self.assertEqual(origin_run.plan, cloned_run.plan)
        self.assertEqual(origin_run.build, cloned_run.build)
        self.assertEqual(origin_run.manager, cloned_run.manager)
        self.assertEqual(self.tester, cloned_run.default_tester)

        for origin_case_run, cloned_case_run in zip(
            origin_run.case_run.all(), cloned_run.case_run.all()
        ):
            self.assertEqual(origin_case_run.case, cloned_case_run.case)
            self.assertEqual(origin_case_run.assignee, cloned_case_run.assignee)
            self.assertEqual(origin_case_run.build, cloned_case_run.build)
            self.assertEqual(origin_case_run.notes, cloned_case_run.notes)
            self.assertEqual(origin_case_run.sortkey, cloned_case_run.sortkey)

            if use_newest_case_text:
                if origin_case_run.case.text.count() == 0:
                    self.assertEqual(
                        origin_case_run.case_text_version,
                        cloned_case_run.case_text_version,
                    )
                else:
                    # Should use newest case text
                    self.assertEqual(
                        list(origin_case_run.get_text_versions())[-1],
                        cloned_case_run.case_text_version,
                    )
            else:
                self.assertEqual(
                    origin_case_run.case_text_version, cloned_case_run.case_text_version
                )

        if clone_cc:
            self.assertEqual(
                list(origin_run.cc_list.values_list("user")),
                list(cloned_run.cc_list.values_list("user")),
            )
        else:
            self.assertEqual([], list(cloned_run.cc_list.all()))

        if clone_tag:
            self.assertEqual(
                list(origin_run.tags.values_list("tag")),
                list(cloned_run.tags.values_list("tag")),
            )
        else:
            self.assertEqual([], list(cloned_run.tags.all()))


class TestSearchRuns(BaseCaseRun):
    """Test search runs view"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.search_url = reverse("runs-all")

        # Add more test runs for testing different search criterias

        cls.run_tester = f.UserFactory(username="run_tester", email="runtester@example.com")

        cls.product_issuetracker = f.ProductFactory(name="issuetracker")
        cls.version_issuetracker_0_1 = f.VersionFactory(
            value="0.1", product=cls.product_issuetracker
        )
        cls.version_issuetracker_1_2 = f.VersionFactory(
            value="1.2", product=cls.product_issuetracker
        )

        cls.env_group_db = f.TCMSEnvGroupFactory(name="db")
        cls.plan_issuetracker = f.TestPlanFactory(
            name="Test issue tracker releases",
            author=cls.tester,
            owner=cls.tester,
            product=cls.product_issuetracker,
            product_version=cls.version_issuetracker_0_1,
            env_group=[cls.env_group_db],
        )

        # Probably need more cases as well in order to create case runs to
        # test statistics in search result

        cls.build_issuetracker_fast = f.TestBuildFactory(product=cls.product_issuetracker)

        cls.run_hotfix = f.TestRunFactory(
            summary="Fast verify hotfix",
            product_version=cls.version_issuetracker_0_1,
            plan=cls.plan_issuetracker,
            build=cls.build_issuetracker_fast,
            manager=cls.tester,
            default_tester=cls.run_tester,
            tag=[f.TestTagFactory(name="fedora"), f.TestTagFactory(name="rhel")],
        )

        cls.run_release = f.TestRunFactory(
            summary="Smoke test before release",
            product_version=cls.version_issuetracker_1_2,
            plan=cls.plan_issuetracker,
            build=cls.build_issuetracker_fast,
            manager=cls.tester,
            default_tester=cls.run_tester,
        )

        cls.run_daily = f.TestRunFactory(
            summary="Daily test during sprint",
            product_version=cls.version_issuetracker_0_1,
            plan=cls.plan_issuetracker,
            build=cls.build_issuetracker_fast,
            manager=cls.tester,
            default_tester=cls.run_tester,
            tag=[f.TestTagFactory(name="rhel")],
        )

        cls.search_data = {
            # 'action': 'search',
            # Add criteria for searching runs in each test
            # DataTable properties: pagination and sorting
            "sEcho": 1,
            "iDisplayStart": 0,
            # Make enough length to display all searched runs in one page
            "iDisplayLength": TestRun.objects.count() + 1,
            "iSortCol_0": 1,
            "sSortDir_0": "asc",
            "iSortingCols": 1,
            # In the view, first column is not sortable.
            "bSortable_0": "false",
            "bSortable_1": "true",
            "bSortable_2": "true",
            "bSortable_3": "true",
            "bSortable_4": "true",
            "bSortable_5": "true",
            "bSortable_6": "true",
            "bSortable_7": "true",
            "bSortable_8": "true",
            "bSortable_9": "true",
            "bSortable_10": "true",
            "bSortable_11": "true",
        }

    def assert_found_runs_in_first_page(self, found_runs: Union[QuerySet, List], response):
        bs = BeautifulSoup(response.content.decode("utf-8"), "html.parser")
        run_ids = list(map(int, (tr.td.input.get("value") for tr in bs.table.tbody.find_all("tr"))))
        expected_run_ids = [run.pk for run in found_runs]
        self.assertListEqual(expected_run_ids, run_ids)

    def test_switch_to_another_page(self):
        search_data = self.search_data.copy()
        page_size = 2
        search_data["iDisplayStart"] = 2  # Switch to the second page
        search_data["iDisplayLength"] = page_size
        search_data["sSortDir_0"] = "desc"

        response = self.client.get(self.search_url, data=search_data)
        table_data = json.loads(response.content)

        total_count = TestRun.objects.count()

        self.assertEqual(total_count, table_data["iTotalRecords"])
        self.assertEqual(total_count, table_data["iTotalDisplayRecords"])
        self.assertEqual(page_size, len(table_data["aaData"]))

        runs = TestRun.objects.order_by("-pk")[2:4]  # Get runs for the second page

        for run, row in zip(runs, table_data["aaData"]):
            self.assertEqual(run.pk, int(BeautifulSoup(row[0], "html.parser").input.get("value")))

            run_url = reverse("run-get", args=[run.pk])
            self.assertEqual(f"<a href='{run_url}'>{run.pk}</a>", row[1])
            self.assertEqual(f"<a href='{run_url}'>{run.summary}</a>", row[2])

            # Verify env_groups
            env_groups = list(run.plan.env_group.values_list("name", flat=True))
            self.assertEqual(env_groups[0] if env_groups else "None", row[7])

    def test_search_for_the_first_page(self):
        response = self.client.get(self.search_url)
        self.assert_found_runs_in_first_page(TestRun.objects.order_by("-pk")[0:20], response)

    def test_empty_search_result(self):
        response = self.client.get(self.search_url, {"build": 9999})
        self.assert_no_run_found(response)

    def test_search_by_summary(self):
        response = self.client.get(self.search_url, {"summary": "run"})
        self.assert_found_runs_in_first_page([self.test_run_1, self.test_run], response)

    def test_search_by_product(self):
        response = self.client.get(self.search_url, {"product": self.product_issuetracker.pk})

        self.assert_found_runs_in_first_page(
            [self.run_daily, self.run_release, self.run_hotfix], response
        )

    def test_search_by_product_and_version(self):
        query_criteria = {
            "product": self.product_issuetracker.pk,
            "product_version": self.version_issuetracker_1_2.pk,
        }
        response = self.client.get(self.search_url, query_criteria)

        self.assert_found_runs_in_first_page([self.run_release], response)

    def test_search_by_product_and_build(self):
        query_criteria = {
            "product": self.product_issuetracker.pk,
            "build": self.build_issuetracker_fast.pk,
        }
        response = self.client.get(self.search_url, query_criteria)

        self.assert_found_runs_in_first_page(
            [self.run_daily, self.run_release, self.run_hotfix], response
        )

    def test_search_by_product_and_other_product_build(self):
        query_criteria = {
            "product": self.product_issuetracker.pk,
            "build": self.build.pk,
        }
        response = self.client.get(self.search_url, query_criteria)
        self.assert_no_run_found(response)

    def test_search_by_plan_name(self):
        response = self.client.get(self.search_url, {"plan": "Issue"})

        self.assert_found_runs_in_first_page(
            [self.run_daily, self.run_release, self.run_hotfix], response
        )

    def test_search_by_empty_plan_name(self):
        response = self.client.get(self.search_url, {"plan": ""})
        self.assert_found_runs_in_first_page(TestRun.objects.order_by("-pk"), response)

    def test_search_by_plan_id(self):
        response = self.client.get(self.search_url, {"plan": self.plan.pk})
        self.assert_found_runs_in_first_page([self.test_run_1, self.test_run], response)

    def test_search_by_manager_or_default_tester(self):
        response = self.client.get(
            self.search_url, {"people_type": "people", "people": self.run_tester}
        )
        self.assert_found_runs_in_first_page(
            [self.run_daily, self.run_release, self.run_hotfix], response
        )

        response = self.client.get(
            self.search_url, {"people_type": "people", "people": self.tester}
        )
        self.assert_found_runs_in_first_page(TestRun.objects.order_by("-pk"), response)

    def test_search_by_manager(self):
        response = self.client.get(
            self.search_url, {"people_type": "manager", "people": self.tester.username}
        )
        self.assert_found_runs_in_first_page(TestRun.objects.order_by("-pk"), response)

    def test_search_by_non_existing_manager(self):
        response = self.client.get(
            self.search_url, {"people_type": "manager", "people": "nonexisting-manager"}
        )
        self.assert_no_run_found(response)

    def test_search_by_default_tester(self):
        response = self.client.get(
            self.search_url,
            {"people_type": "default_tester", "people": self.run_tester.username},
        )
        self.assert_found_runs_in_first_page(
            [self.run_daily, self.run_release, self.run_hotfix], response
        )

    def test_search_by_non_existing_default_tester(self):
        response = self.client.get(
            self.search_url,
            {"people_type": "default_tester", "people": "nonexisting-default-tester"},
        )
        self.assert_no_run_found(response)

    def test_search_running_runs(self):
        response = self.client.get(self.search_url, {"status": "running"})
        self.assert_found_runs_in_first_page(TestRun.objects.order_by("-pk"), response)

    def assert_no_run_found(self, response):
        bs = BeautifulSoup(response.content.decode("utf-8"), "html.parser")
        # The DataTable does not run during the response.
        self.assertEqual("", bs.table.tbody.text.strip())

    def test_search_finished_runs(self):
        response = self.client.get(self.search_url, {"status": "finished"})
        self.assert_no_run_found(response)

    def test_search_by_tag(self):
        response = self.client.get(self.search_url, {"tag__name__in": "rhel"})
        self.assert_found_runs_in_first_page([self.run_daily, self.run_hotfix], response)


class TestAddRemoveRunCC(BaseCaseRun):
    """Test view tcms.testruns.views.cc"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.cc_url = reverse("run-cc", args=[cls.test_run.pk])

        cls.cc_user_1 = f.UserFactory(username="cc-user-1", email="cc-user-1@example.com")
        cls.cc_user_2 = f.UserFactory(username="cc-user-2", email="cc-user-2@example.com")
        cls.cc_user_3 = f.UserFactory(username="cc-user-3", email="cc-user-3@example.com")

        cls.test_run.add_cc(cls.cc_user_2)
        cls.test_run.add_cc(cls.cc_user_3)

    def test_404_if_run_not_exist(self):
        cc_url = reverse("run-cc", args=[999999])
        response = self.client.get(cc_url)
        self.assert404(response)

    def assert_cc(self, response, expected_cc):
        self.assertEqual(len(expected_cc), self.test_run.cc.count())

        for cc in expected_cc:
            self.assertContains(
                response, '<a href="mailto:{0}">{0}</a>'.format(cc.email), html=True
            )

    def test_refuse_if_missing_action(self):
        response = self.client.get(self.cc_url, {"user": self.cc_user_1.username})
        self.assert_cc(response, [self.cc_user_2, self.cc_user_3])

    def test_add_cc(self):
        response = self.client.get(self.cc_url, {"do": "add", "user": self.cc_user_1.username})

        self.assert_cc(response, [self.cc_user_2, self.cc_user_3, self.cc_user_1])

    def test_remove_cc(self):
        response = self.client.get(self.cc_url, {"do": "remove", "user": self.cc_user_2.username})

        self.assert_cc(response, [self.cc_user_3])

    def test_refuse_to_remove_if_missing_user(self):
        response = self.client.get(self.cc_url, {"do": "remove"})

        self.assertContains(response, "User name or email is required by this operation")

        self.assert_cc(response, [self.cc_user_2, self.cc_user_3])

    def test_refuse_to_add_if_missing_user(self):
        response = self.client.get(self.cc_url, {"do": "add"})

        self.assertContains(response, "User name or email is required by this operation")

        self.assert_cc(response, [self.cc_user_2, self.cc_user_3])

    def test_refuse_if_user_not_exist(self):
        response = self.client.get(self.cc_url, {"do": "add", "user": "not exist"})

        self.assertContains(response, "The user you typed does not exist in database")

        self.assert_cc(response, [self.cc_user_2, self.cc_user_3])


class TestEnvValue(BaseCaseRun):
    """Test env_value view method"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.property_os = f.TCMSEnvPropertyFactory(name="os")
        cls.value_linux = f.TCMSEnvValueFactory(value="Linux", property=cls.property_os)
        cls.value_bsd = f.TCMSEnvValueFactory(value="BSD", property=cls.property_os)
        cls.value_mac = f.TCMSEnvValueFactory(value="Mac", property=cls.property_os)

        cls.test_run.add_env_value(cls.value_linux)
        cls.test_run_1.add_env_value(cls.value_linux)

        user_should_have_perm(cls.tester, "testruns.add_tcmsenvrunvaluemap")
        user_should_have_perm(cls.tester, "testruns.delete_tcmsenvrunvaluemap")

    def test_add_env_value(self):
        self.client.post(
            reverse("runs-add-env-value"),
            {"env_value": self.value_bsd.pk, "runs": self.test_run.pk},
        )

        self.assertTrue(
            TCMSEnvRunValueMap.objects.filter(run=self.test_run, value=self.value_bsd).exists()
        )

    def test_add_env_value_to_runs(self):
        self.client.post(
            reverse("runs-add-env-value"),
            {
                "env_value": self.value_bsd.pk,
                "runs": [self.test_run.pk, self.test_run_1.pk],
            },
        )

        self.assertTrue(
            TCMSEnvRunValueMap.objects.filter(run=self.test_run, value=self.value_bsd).exists()
        )

        self.assertTrue(
            TCMSEnvRunValueMap.objects.filter(run=self.test_run_1, value=self.value_bsd).exists()
        )

    def test_anonymouse_is_not_allowed_to_delete(self):
        self.client.logout()

        resp = self.client.post(
            reverse("runs-add-env-value"),
            {
                "env_value": self.value_linux.pk,
                "runs": self.test_run.pk,
            },
        )
        self.assert403(resp)

    def test_delete_env_value(self):
        self.client.post(
            reverse("runs-add-env-value"),
            {
                "env_value": self.value_linux.pk,
                "runs": self.test_run.pk,
            },
        )

        self.assertTrue(
            TCMSEnvRunValueMap.objects.filter(run=self.test_run, value=self.value_linux).exists()
        )

    def test_delete_env_value_from_runs(self):
        self.client.post(
            reverse("runs-add-env-value"),
            {
                "env_value": self.value_linux.pk,
                "runs": [self.test_run.pk, self.test_run_1.pk],
            },
        )

        self.assertTrue(
            TCMSEnvRunValueMap.objects.filter(run=self.test_run, value=self.value_linux).exists()
        )

        self.assertTrue(
            TCMSEnvRunValueMap.objects.filter(run=self.test_run_1, value=self.value_linux).exists()
        )


class TestExportTestRunCases(BaseCaseRun):
    """Test export view method to export test case runs"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.export_url = reverse("run-export", args=[cls.test_run.pk])
        cls.log_link1 = "https://somewhere/log1.txt"
        cls.log_link2 = "https://somewhere/log2.txt"
        create_link("Log1", cls.log_link1, link_to=cls.case_run_1)
        create_link("一份很长的日志", cls.log_link2, link_to=cls.case_run_2)

    @patch("tcms.testruns.views.time.strftime", return_value="2017-06-17")
    def test_export_to_xml_file(self, strftime):
        response = self.client.get(self.export_url, {"format": "xml"})
        self.assertEqual(
            "attachment; filename=tcms-testcase-runs-2017-06-17.xml",
            response["Content-Disposition"],
        )

    @patch("tcms.testruns.views.time.strftime", return_value="2017-06-17")
    def test_export_to_csv_file(self, strftime):
        response = self.client.get(self.export_url, {"format": "csv"})
        self.assertEqual(
            "attachment; filename=tcms-testcase-runs-2017-06-17.csv",
            response["Content-Disposition"],
        )

    def test_export_all_case_runs_to_csv_by_default(self):
        response = self.client.get(self.export_url, {"format": "csv"})

        actual_rows_count = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_file = os.path.join(tmpdir, "file.csv")
            with open(csv_file, "w") as f:
                f.write(response.content.decode())

            with open(csv_file, "r", newline="") as f:
                reader = csv.reader(f)
                next(reader)  # Skip the header line
                for row in reader:
                    actual_rows_count += 1
                    if row[0] == self.case_run_1.pk:
                        self.assertEqual(self.log_link1, row[-2])
                    elif row[0] == self.case_run_2.pk:
                        self.assertEqual(self.log_link2, row[-2])

        self.assertEqual(
            self.test_run.case_run.count(),
            actual_rows_count,
            msg="Not all case runs are exported.",
        )

    def test_export_all_case_runs_to_xml_by_default(self):
        response = self.client.get(self.export_url, {"format": "xml"})
        xmldoc = ElementTree.fromstring(response.content)
        case_run_nodes = xmldoc.findall("testcaserun")
        self.assertEqual(self.test_run.case_run.count(), len(case_run_nodes))


class TestIssueActions(BaseCaseRun):
    """Test issue view method"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user_should_have_perm(cls.tester, "testruns.change_testrun")
        user_should_have_perm(cls.tester, "issuetracker.add_issue")
        user_should_have_perm(cls.tester, "issuetracker.delete_issue")

        cls.bz_tracker_product = f.IssueTrackerProductFactory(name="BZ")
        cls.bugzilla = f.IssueTrackerFactory(
            name="simplebz",
            service_url="http://localhost/",
            tracker_product=cls.bz_tracker_product,
            validate_regex=r"^\d+$",
            issue_report_endpoint="/enter_bug.cgi",
        )
        f.ProductIssueTrackerRelationshipFactory(product=cls.product, issue_tracker=cls.bugzilla)

        cls.mybz = f.IssueTrackerFactory(
            name="mybz",
            service_url="http://mybz.localhost/",
            tracker_product=cls.bz_tracker_product,
            validate_regex=r"^\d+$",
            issue_report_endpoint="/enter_bug.cgi",
        )

        cls.disabled_old_bz = f.IssueTrackerFactory(
            enabled=False,
            name="disabled_old_bz",
            service_url="http://old-bz.localhost/",
            tracker_product=cls.bz_tracker_product,
            validate_regex=r"^\d+$",
            issue_report_endpoint="/enter_bug.cgi",
        )
        f.ProductIssueTrackerRelationshipFactory(
            product=cls.product, issue_tracker=cls.disabled_old_bz
        )

        cls.jira_tracker_product = f.IssueTrackerProductFactory(name="ORGJIRA")
        cls.orgjira = f.IssueTrackerFactory(
            name="orgjira",
            service_url="http://localhost/",
            tracker_product=cls.jira_tracker_product,
            validate_regex=r"^[A-Z]+-\d+$",
            issue_report_endpoint="/createissue",
        )
        f.ProductIssueTrackerRelationshipFactory(product=cls.product, issue_tracker=cls.orgjira)

        cls.run_issues_url = reverse("run-issues", args=[cls.test_run.pk])

        cls.bug_12345 = "12345"
        cls.jira_nitrate_100 = "NITRATE-100"
        cls.case_run_1.add_issue(cls.bug_12345, cls.bugzilla)
        cls.case_run_1.add_issue(cls.jira_nitrate_100, cls.orgjira)

    def test_404_if_case_run_id_not_exist(self):
        self.run_issues_url = reverse("run-issues", args=[999])

        response = self.client.get(self.run_issues_url, {})
        self.assert404(response)

    def test_refuse_if_action_is_unknown(self):
        post_data = {
            "a": "unknown action",
            "case_run": [self.case_run_1.pk],
            "case": self.case_run_1.case.pk,
            "tracker": self.bz_tracker_product.pk,
            "issue_key": "123456",
        }

        response = self.client.get(self.run_issues_url, post_data)
        self.assertJsonResponse(
            response,
            {"message": "Unrecognizable actions"},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_remove_issue_from_case_run(self):
        post_data = {
            "a": "remove",
            "case_run": [self.case_run_1.pk],
            "issue_key": [self.bug_12345],
        }

        response = self.client.get(self.run_issues_url, post_data)

        issue_exists = Issue.objects.filter(
            issue_key=self.bug_12345,
            case=self.case_run_1.case,
            case_run=self.case_run_1,
        ).exists()
        self.assertFalse(issue_exists)

        self.assertJsonResponse(
            response,
            {
                "run_issues_count": 1,
                "caserun_issues_count": {str(self.case_run_1.pk): 1},
            },
        )

    def test_add_issue_to_case_run(self):
        issue_key = "12000"
        resp = self.client.get(
            self.run_issues_url,
            data={
                "a": "add",
                "case_run": [self.case_run_1.pk],
                "issue_key": [issue_key],
                "tracker": self.bugzilla.pk,
            },
        )

        self.assert200(resp)
        self.assertTrue(self.case_run_1.get_issues().filter(issue_key=issue_key).exists())

    def test_refuse_adding_issue_if_tracker_is_not_relative(self):
        resp = self.client.get(
            self.run_issues_url,
            data={
                "a": "add",
                "case_run": [self.case_run_1.pk],
                "issue_key": ["12000"],
                "tracker": self.mybz.pk,
            },
        )

        self.assertJsonResponse(
            resp,
            {
                "message": [
                    f'Issue tracker "{self.mybz.name}" is not relative to the '
                    f'case run via product "{self.product.name}".'
                ]
            },
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_refuse_adding_issue_if_tracker_is_disabled(self):
        resp = self.client.get(
            self.run_issues_url,
            data={
                "a": "add",
                "case_run": [self.case_run_1.pk],
                "issue_key": ["12000"],
                "tracker": self.disabled_old_bz.pk,
            },
        )

        self.assertJsonResponse(
            resp,
            {"message": [f'Issue tracker "{self.disabled_old_bz.name}" is not enabled.']},
            status_code=HTTPStatus.BAD_REQUEST,
        )


class TestRemoveCaseRuns(BaseCaseRun):
    """Test remove_case_run view method"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, "testruns.delete_testcaserun")
        cls.remove_case_run_url = reverse("run-remove-caserun", args=[cls.test_run.pk])

    def test_nothing_change_if_no_case_run_passed(self):
        response = self.client.post(self.remove_case_run_url, {})

        self.assertRedirects(response, reverse("run-get", args=[self.test_run.pk]))

    def test_ignore_non_integer_case_run_ids(self):
        expected_rest_case_runs_count = self.test_run.case_run.count() - 2

        self.client.post(
            self.remove_case_run_url,
            {
                "case_run": [self.case_run_1.pk, "a1000", self.case_run_2.pk],
            },
        )

        self.assertEqual(expected_rest_case_runs_count, self.test_run.case_run.count())

    def test_remove_case_runs(self):
        expected_rest_case_runs_count = self.test_run.case_run.count() - 1

        self.client.post(self.remove_case_run_url, {"case_run": [self.case_run_1.pk]})

        self.assertEqual(expected_rest_case_runs_count, self.test_run.case_run.count())

    def test_redirect_to_run_if_still_case_runs_exist_after_removal(self):
        response = self.client.post(self.remove_case_run_url, {"case_run": [self.case_run_1.pk]})

        self.assertRedirects(response, reverse("run-get", args=[self.test_run.pk]))

    def test_redirect_to_add_case_runs_if_all_case_runs_are_removed(self):
        response = self.client.post(
            self.remove_case_run_url,
            {"case_run": [case_run.pk for case_run in self.test_run.case_run.all()]},
        )

        self.assertRedirects(
            response,
            reverse("add-cases-to-run", args=[self.test_run.pk]),
            fetch_redirect_response=False,
        )


class TestUpdateCaseRunText(BaseCaseRun):
    """Test update_case_run_text view method"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.update_url = reverse("run-update", args=[cls.test_run.pk])

        # To increase case text version
        cls.case_run_1.case.add_text(
            action="action", effect="effect", setup="setup", breakdown="breakdown"
        )
        cls.case_run_1.case.add_text(
            action="action_1",
            effect="effect_1",
            setup="setup_1",
            breakdown="breakdown_1",
        )

    def test_update_selected_case_runs(self):
        response = self.client.post(self.update_url, {"case_run": [self.case_run_1.pk]})

        self.assertContains(response, "1 case run(s) succeed to update")

        self.assertEqual(
            self.case_run_1.case.latest_text_version(),
            self.case_run_1.latest_text().case_text_version,
        )


class TestEditRun(BaseCaseRun):
    """Test edit view method"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user_should_have_perm(cls.tester, "testruns.change_testrun")
        cls.edit_url = reverse("run-edit", args=[cls.test_run.pk])

        cls.new_product = f.ProductFactory(name="Nitrate Dev")
        cls.new_build = f.TestBuildFactory(name="FastTest", product=cls.new_product)
        cls.new_version = f.VersionFactory(value="dev0.1", product=cls.new_product)
        cls.intern = f.UserFactory(username="intern", email="intern@example.com")

    def test_404_if_edit_non_existing_run(self):
        url = reverse("run-edit", args=[9999])
        response = self.client.get(url)

        self.assert404(response)

    def test_edit_run(self):
        post_data = {
            "summary": "New run summary",
            "product": self.new_product.pk,
            "product_version": self.new_version.pk,
            "build": self.new_build.pk,
            "manager": self.test_run.manager.email,
            "default_tester": self.intern.email,
            "estimated_time": "3m",
            "notes": "easytest",
        }

        response = self.client.post(self.edit_url, post_data)

        run = TestRun.objects.get(pk=self.test_run.pk)
        self.assertEqual("New run summary", run.summary)
        self.assertEqual(self.new_version, run.product_version)
        self.assertEqual(self.new_build, run.build)

        self.assertRedirects(response, reverse("run-get", args=[run.pk]))


class TestAddCasesToRun(BaseCaseRun):
    """Test AddCasesToRunView"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.proposed_case = f.TestCaseFactory(
            author=cls.tester,
            default_tester=None,
            reviewer=cls.tester,
            case_status=cls.case_status_proposed,
            plan=[cls.plan],
        )

        user_should_have_perm(cls.tester, "testruns.add_testcaserun")

    def test_show_add_cases_to_run(self):
        url = reverse("add-cases-to-run", args=[self.test_run.pk])
        response = self.client.get(url)

        self.assertNotContains(
            response,
            '<a href="{}">{}</a>'.format(
                reverse("case-get", args=[self.proposed_case.pk]), self.proposed_case.pk
            ),
            html=True,
        )

        confirmed_cases = [self.case, self.case_1, self.case_2, self.case_3]

        # Check selected and unselected case id checkboxes
        # cls.case is not added to cls.test_run, so it should not be checked.
        self.assertContains(
            response,
            '<td align="left">'
            '<input type="checkbox" name="case" value="{}">'
            "</td>".format(self.case.pk),
            html=True,
        )

        # other cases are added to cls.test_run, so must be checked.
        for case in confirmed_cases[1:]:
            self.assertContains(
                response,
                '<td align="left">'
                '<input type="checkbox" name="case" value="{}" '
                "disabled checked>"
                "</td>".format(case.pk),
                html=True,
            )

        # Check listed case properties
        for loop_counter, case in enumerate(confirmed_cases, 1):
            html_pieces = [
                '<a href="{}">{}</a>'.format(reverse("case-get", args=[case.pk]), case.pk),
                '<td class="js-case-summary" data-param="{0}">'
                '<a id="link_{0}" class="blind_title_link" '
                'href="javascript:void(0);">{1}</a></td>'.format(loop_counter, case.summary),
                f"<td>{case.author.username}</td>",
                "<td>{}</td>".format(formats.date_format(case.create_date, "DATETIME_FORMAT")),
                f"<td>{case.category.name}</td>",
                f"<td>{case.priority.value}</td>",
            ]
            for html in html_pieces:
                self.assertContains(response, html, html=True)


class TestRunReportView(BaseCaseRun):
    """Test TestRunReportView"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.bz_tracker = cls.create_bz_tracker()
        cls.case_run_1.add_issue("1", cls.bz_tracker)
        cls.case_run_1.add_issue("2", cls.bz_tracker)
        cls.case_run_2.add_issue("3", cls.bz_tracker)

        cls.report_url = reverse("run-report", args=[cls.case_run_1.run.pk])

    def test_show_report(self):
        response = self.client.get(self.report_url)

        # TODO: assert more.

        # Ensure each case run's issues are available
        for issue_key in [1, 2, 3]:
            self.assertContains(
                response,
                '<a href="http://bugs.example.com/?id={0}">{0}</a>'.format(issue_key),
                html=True,
            )

        # Ensure all issues display url is available in the Issues section
        self.assertContains(response, f"View all issues ({self.bz_tracker.name})")

        issues_display_url = "http://bugs.example.com/?bug_id=1,2,3"
        self.assertContains(
            response,
            '<a href="{0}" target="_blank">{0}</a>'.format(issues_display_url),
            html=True,
        )


class TestChangeRunStatus(BaseCaseRun):
    """Test view to change a test run status"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.url = reverse("run-change-status", args=[cls.test_run_1.pk])
        user_should_have_perm(cls.tester, "testruns.change_testrun")

    def test_run_id_does_not_exist(self):
        result = TestRun.objects.aggregate(max_pk=Max("pk"))
        max_pk = result["max_pk"]

        url = reverse("run-change-status", args=[max_pk + 1])
        resp = self.client.get(url, data={"finished": "0"})
        self.assert404(resp)

    def test_set_finish(self):
        resp = self.client.get(self.url, data={"finished": "1"})

        self.assertRedirects(
            resp,
            reverse("run-get", args=[self.test_run_1.pk]),
            fetch_redirect_response=False,
        )

        self.test_run_1.refresh_from_db()
        self.assertIsNotNone(self.test_run_1.stop_date)

    def test_set_running(self):
        self.test_run_1.stop_date = datetime.now()
        self.test_run_1.save()

        resp = self.client.get(self.url, data={"finished": "0"})

        self.assertRedirects(
            resp,
            reverse("run-get", args=[self.test_run_1.pk]),
            fetch_redirect_response=False,
        )

        self.test_run_1.refresh_from_db()
        self.assertIsNone(self.test_run_1.stop_date)


class TestRunStatisticsView(BaseCaseRun):
    """Test the statistics in a test run page"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        status_passed = TestCaseRunStatus.objects.get(name="PASSED")
        status_failed = TestCaseRunStatus.objects.get(name="FAILED")
        status_error = TestCaseRunStatus.objects.get(name="ERROR")
        cls.case_run_1.case_run_status = status_passed
        cls.case_run_2.case_run_status = status_error
        cls.case_run_3.case_run_status = status_failed

        cls.case_run_1.save()
        cls.case_run_2.save()
        cls.case_run_3.save()

    def test_get_the_statistics(self):
        response = self.client.get(reverse("run-statistics", args=[self.test_run.pk]))

        run_report_url = reverse("run-report", args=[self.test_run.pk])
        attrs = 'href="javascript:void(0)" class="js-status-subtotal"'
        content = [
            '<span id="total_run_issues_count">No Issues</span>',
            f'<a href="{run_report_url}" title="report of test caserun">Report</a>',
            '<span id="BLOCKED">[<a>0</a>]</span>',
            f'<span id="ERROR">[<a {attrs} data-status-name="ERROR">1</a>]</span>',
            f'<span id="FAILED">[<a {attrs} data-status-name="FAILED">1</a>]</span>',
            '<span id="IDLE">[<a>0</a>]</span>',
            f'<span id="PASSED">[<a {attrs} data-status-name="PASSED">1</a>]</span>',
            '<span id="PAUSED">[<a>0</a>]</span>',
            '<span id="RUNNING">[<a>0</a>]</span>',
            '<span id="WAIVED">[<a>0</a>]</span>',
            '<a href="javascript:void(0)" class="js-caserun-total" data-status-name="">3</a>',
        ]

        for item in content:
            self.assertContains(response, item, html=True)


class TestCommentCaseRuns(BaseCaseRun):
    """Test case for ajax.comment_case_runs"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.many_comments_url = reverse("caserun-comment-caseruns")

    def test_refuse_if_missing_comment(self):
        response = self.client.post(
            self.many_comments_url, {"run": [self.case_run_1.pk, self.case_run_2.pk]}
        )
        self.assertJsonResponse(
            response, {"message": ["Comment is needed."]}, status_code=HTTPStatus.BAD_REQUEST
        )

    def test_refuse_if_missing_no_case_run_pk(self):
        response = self.client.post(self.many_comments_url, {"comment": "new comment", "run": []})
        self.assertJsonResponse(
            response,
            {"message": ["No test case run id is passed to comment out."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

        response = self.client.post(self.many_comments_url, {"comment": "new comment"})
        self.assertJsonResponse(
            response,
            {"message": ["No test case run id is passed to comment out."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_refuse_if_passed_case_run_pks_not_exist(self):
        response = self.client.post(
            self.many_comments_url,
            {"comment": "new comment", "run": [99999998]},
        )
        self.assertJsonResponse(
            response,
            {"message": ["Test case run 99999998 does not exist."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_add_comment_to_case_runs(self):
        new_comment = "new comment"
        response = self.client.post(
            self.many_comments_url,
            {"comment": new_comment, "run": [self.case_run_1.pk, self.case_run_2.pk]},
        )
        self.assertJsonResponse(response, {})

        # Assert comments are added
        case_run_ct = ContentType.objects.get_for_model(TestCaseRun)

        for case_run_pk in (self.case_run_1.pk, self.case_run_2.pk):
            comments = Comment.objects.filter(object_pk=case_run_pk, content_type=case_run_ct)
            self.assertEqual(new_comment, comments[0].comment)
            self.assertEqual(self.tester, comments[0].user)

# -*- coding: utf-8 -*-
import json
from collections.abc import Iterable
from http import HTTPStatus
from operator import itemgetter
from textwrap import dedent
from typing import Any, Dict, List, Optional, Union
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django import test
from django.contrib.auth.models import User
from django.core import mail, serializers
from django.core.mail import EmailMessage
from django.db.models import Max
from django.http import QueryDict
from django.urls import reverse

from tcms.core.ajax import SORT_KEY_MAX, SORT_KEY_RANGE, strip_parameters
from tcms.logs.models import TCMSLogModel
from tcms.management.models import (
    Component,
    Priority,
    TCMSEnvGroup,
    TCMSEnvProperty,
    TCMSEnvValue,
    TestBuild,
    TestEnvironment,
    TestTag,
    Version,
)
from tcms.testcases.models import TestCase, TestCaseCategory, TestCasePlan, TestCaseStatus
from tcms.testruns.models import TestCaseRun, TestCaseRunStatus
from tests import AuthMixin, BaseCaseRun, BaseDataContext, BasePlanCase, HelperAssertions
from tests import factories as f
from tests import remove_perm_from_user, user_should_have_perm


@pytest.mark.parametrize(
    "data,skip_params,expected",
    [
        [{}, ["type"], {}],
        [QueryDict(""), ["type"], {}],
        [{"name": "abc"}, [], {"name": "abc"}],
        [{"name": "abc"}, ["type"], {"name": "abc"}],
        [{"name": "abc", "type": ""}, ["type"], {"name": "abc"}],
        [{"name": "", "type": ""}, ["type"], {}],
        [QueryDict("lang=py&ver=3.9&info="), ["ver"], {"lang": "py"}],
        [QueryDict("lang=py&ver=3.9&info="), ("ver",), {"lang": "py"}],
    ],
)
def test_strip_parameters(
    data: Union[QueryDict, Dict[str, Any]], skip_params: Iterable, expected: Dict[str, Any]
):
    assert expected == strip_parameters(data, skip_params)


class TestChangeCaseRunAssignee(BaseCaseRun):
    """Test AJAX request to change case runs' assignee"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, "testruns.change_testcaserun")
        cls.assignee = f.UserFactory(username="expert-tester")
        cls.case_run_3.assignee = None
        cls.case_run_3.save(update_fields=["assignee"])
        cls.url = reverse("patch-case-runs")

    def test_given_assignee_does_not_exist(self):
        result = User.objects.aggregate(max_pk=Max("pk"))
        user_id = result["max_pk"] + 1
        resp = self.client.patch(
            self.url,
            data={
                "case_run": [self.case_run_1.pk],
                "target_field": "assignee",
                "new_value": user_id,
            },
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {"message": [f"No user with id {user_id} exists."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_specified_case_runs_do_not_exist(self):
        result = TestCaseRun.objects.aggregate(max_pk=Max("pk"))
        case_run_id = result["max_pk"] + 1
        resp = self.client.patch(
            self.url,
            data={
                "case_run": [case_run_id],
                "target_field": "assignee",
                "new_value": self.assignee.pk,
            },
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {"message": [f"Test case run {case_run_id} does not exist."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_change_assignee(self):
        mail.outbox = []
        update_targets = [self.case_run_1, self.case_run_3]

        case_run: TestCaseRun

        resp = self.client.patch(
            self.url,
            data={
                "case_run": [case_run.pk for case_run in update_targets],
                "target_field": "assignee",
                "new_value": self.assignee.pk,
            },
            content_type="application/json",
        )
        self.assertEqual(200, resp.status_code)

        original_assignees = {
            self.case_run_1.pk: self.case_run_1.assignee.username,
            self.case_run_3.pk: "None",
        }

        for case_run in update_targets:
            self.assertEqual(self.assignee, TestCaseRun.objects.get(pk=case_run.pk).assignee)
            self.assertTrue(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="assignee",
                    original_value=original_assignees[case_run.pk],
                    new_value=self.assignee.username,
                    object_pk=case_run.pk,
                ).exists()
            )

        self._assert_sent_mail()

    def _assert_sent_mail(self):
        out_mail = mail.outbox[0]
        self.assertEqual(f"Assignee of run {self.test_run.pk} has been changed", out_mail.subject)
        self.assertSetEqual(
            set(self.test_run.get_notification_recipients()), set(out_mail.recipients())
        )

        expected_body = dedent(
            f"""\
            ### Links ###
            Test run: {self.test_run.get_full_url()}

            ### Info ###
            The assignee of case run in test run {self.test_run.pk}: {self.test_run.summary}
            has been changed: Following is the new status:

            ### Test case runs information ###

            * {self.case_run_1.pk}: {self.case_run_1.case.summary} - {self.assignee.username}
            * {self.case_run_3.pk}: {self.case_run_3.case.summary} - {self.assignee.username}"""
        )

        self.assertEqual(expected_body, out_mail.body)


class TestSendMailNotifyOnTestCaseReviewerIsChanged(BasePlanCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, "testcases.change_testcase")
        cls.reviewer = f.UserFactory(username="case-reviewer")

    def test_ensure_mail_notify_is_sent(self):
        mail.outbox = []

        self.login_tester()
        resp = self.client.patch(
            reverse("patch-cases"),
            data={
                "from_plan": self.plan.pk,
                "case": [self.case.pk, self.case_2.pk],
                "target_field": "reviewer",
                "new_value": self.reviewer.username,
            },
            content_type="application/json",
        )
        self.assertEqual(200, resp.status_code)

        case = TestCase.objects.get(pk=self.case.pk)
        self.assertEqual(self.reviewer.username, case.reviewer.username)
        case = TestCase.objects.get(pk=self.case_2.pk)
        self.assertEqual(self.reviewer.username, case.reviewer.username)

        out_mail: EmailMessage = mail.outbox[0]

        self.assertEqual("You have been the reviewer of cases", out_mail.subject)
        self.assertListEqual([self.reviewer.email], out_mail.recipients())

        assigned_by = self.tester.username
        expected_body = dedent(
            f"""\
            You have been assigned as the reviewer of the following Test Cases by {assigned_by}.


            ### Test cases information ###
            [{self.case.pk}] {self.case.summary} - {self.case.get_full_url()}
            [{self.case_2.pk}] {self.case_2.summary} - {self.case_2.get_full_url()}
        """
        )

        self.assertEqual(expected_body, out_mail.body)


class TestChangeCaseRunStatus(BaseCaseRun):
    """Test the AJAX request to change one or more case run status"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse("patch-case-runs")
        cls.perm = "testruns.change_testcaserun"
        user_should_have_perm(cls.tester, cls.perm)
        cls.running_status = TestCaseRunStatus.objects.get(name="RUNNING")
        cls.request_data = {
            "case_run": [cls.case_run_1.pk, cls.case_run_3.pk],
            "target_field": "case_run_status",
            "new_value": cls.running_status.pk,
        }

        cls.me = f.UserFactory(username="me")
        cls.case_run_6.tested_by = cls.me
        cls.case_run_6.save()

    def test_failure_when_no_permission(self):
        remove_perm_from_user(self.tester, self.perm)
        resp = self.client.patch(self.url, data=self.request_data, content_type="application/json")
        self.assert403(resp)

    def test_change_status(self):
        resp = self.client.patch(self.url, data=self.request_data, content_type="application/json")

        self.assertEqual(200, resp.status_code)

        case_run: TestCaseRun
        for case_run in [self.case_run_1, self.case_run_3]:
            self.assertEqual(
                self.running_status, TestCaseRun.objects.get(pk=case_run.pk).case_run_status
            )

            original_status = case_run.case_run_status.name
            self.assertTrue(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="case_run_status",
                    original_value=original_status,
                    new_value=self.running_status.name,
                    object_pk=case_run.pk,
                ).exists()
            )

    def test_no_case_runs_to_update(self):
        data = self.request_data.copy()
        result = TestCaseRun.objects.aggregate(max_pk=Max("pk"))
        nonexisting_pk = result["max_pk"] + 1
        data["case_run"] = [nonexisting_pk]
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assertJsonResponse(
            resp,
            {"message": [f"Test case run {nonexisting_pk} does not exist."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_log_action_for_tested_by_changed(self):
        """Test log action when case run's tested_by is changed"""
        data = self.request_data.copy()
        # case run 6's tested_by will be updated to the request.user
        data["case_run"] = [self.case_run_1.pk, self.case_run_6.pk]
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assert200(resp)
        self.assertEqual(self.tester, TestCaseRun.objects.get(pk=self.case_run_6.pk).tested_by)
        self.assertTrue(
            TCMSLogModel.objects.filter(
                who=self.tester,
                field="tested_by",
                original_value=self.me.username,
                new_value=self.tester.username,
                object_pk=self.case_run_6.pk,
            ).exists()
        )

    def test_avoid_updating_duplicate_status(self):
        data = self.request_data.copy()
        idle_status = TestCaseRunStatus.objects.get(name="IDLE")
        # Both of the case runs' status should not be updated duplicately.
        data["new_value"] = idle_status.pk
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assert200(resp)
        for case_run_pk in data["case_run"]:
            self.assertFalse(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="case_run_status",
                    original_value=str(self.running_status),
                    new_value=str(idle_status),
                    object_pk=case_run_pk,
                ).exists()
            )


class TestUpdateCaseRunsSortkey(BaseCaseRun):
    """Test AJAX request /ajax/update/case-run-sortkey/"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        user_should_have_perm(cls.tester, "testruns.change_testcaserun")
        cls.original_sort_key = 0
        TestCaseRun.objects.all().update(sortkey=cls.original_sort_key)
        cls.url = reverse("patch-case-runs")

    def test_update_nonexisting_case_run(self):
        result = TestCaseRun.objects.aggregate(max_pk=Max("pk"))
        nonexisting_pk = result["max_pk"] + 1
        resp = self.client.patch(
            self.url,
            data={
                "case_run": [nonexisting_pk],
                "target_field": "sortkey",
                "new_value": 2,
            },
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {"message": [f"Test case run {nonexisting_pk} does not exist."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_sort_key_is_not_integer(self):
        resp = self.client.patch(
            self.url,
            data={
                "case_run": [self.case_run_4.pk],
                "target_field": "sortkey",
                "new_value": "sortkey100",
            },
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {"message": ["Sort key must be a positive integer."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_new_sort_key_is_not_in_range(self):
        resp = self.client.patch(
            self.url,
            data={
                "case_run": [self.case_run_4.pk],
                "target_field": "sortkey",
                "new_value": SORT_KEY_MAX + 1,
            },
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp,
            {"message": [f"New sortkey is out of range {SORT_KEY_RANGE}."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_update_sort_key(self):
        new_sort_key = 2
        update_targets: List[TestCaseRun] = [self.case_run_2, self.case_run_4]

        case_run: TestCaseRun
        update_targets_pks: List[int] = [case_run.pk for case_run in update_targets]

        resp = self.client.patch(
            self.url,
            data={
                "case_run": update_targets_pks,
                "target_field": "sortkey",
                "new_value": new_sort_key,
            },
            content_type="application/json",
        )
        self.assert200(resp)

        for case_run in update_targets:
            self.assertEqual(new_sort_key, TestCaseRun.objects.get(pk=case_run.pk).sortkey)
            self.assertTrue(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="sortkey",
                    original_value=str(self.original_sort_key),
                    new_value=str(new_sort_key),
                    object_pk=case_run.pk,
                ).exists()
            )

        # Other case runs' sortkey should not be changed.
        sort_keys: List[int] = TestCaseRun.objects.exclude(pk__in=update_targets_pks).values_list(
            "sortkey", flat=True
        )
        for sort_key in sort_keys:
            self.assertEqual(self.original_sort_key, sort_key)


class TestUpdateCasesDefaultTester(AuthMixin, HelperAssertions, test.TestCase):
    """Test set default tester to selected cases"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.plan = f.TestPlanFactory(owner=cls.tester, author=cls.tester)
        cls.case_1 = f.TestCaseFactory(
            author=cls.tester, reviewer=cls.tester, default_tester=cls.tester, plan=[cls.plan]
        )
        cls.case_2 = f.TestCaseFactory(
            author=cls.tester, reviewer=cls.tester, default_tester=None, plan=[cls.plan]
        )

        user_should_have_perm(cls.tester, "testcases.change_testcase")

        cls.user_1 = f.UserFactory(username="user1")
        cls.url = reverse("patch-cases")

    def test_set_default_tester(self):
        resp = self.client.patch(
            self.url,
            data={
                "from_plan": self.plan.pk,
                "case": [self.case_1.pk, self.case_2.pk],
                "target_field": "default_tester",
                "new_value": self.user_1.username,
            },
            content_type="application/json",
        )

        self.assertJsonResponse(resp, {})

        case: TestCase
        for case in [self.case_1, self.case_2]:
            self.assertEqual(self.user_1, TestCase.objects.get(pk=case.pk).default_tester)
            self.assertTrue(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="default_tester",
                    original_value="None"
                    if case.default_tester is None
                    else case.default_tester.username,
                    new_value=self.user_1.username,
                ).exists()
            )

    def test_given_username_does_not_exist(self):
        resp = self.client.patch(
            self.url,
            data={
                "from_plan": self.plan.pk,
                "case": [self.case_1.pk, self.case_2.pk],
                "target_field": "default_tester",
                "new_value": "unknown",
            },
            content_type="application/json",
        )

        self.assertJsonResponse(
            resp,
            {
                "message": [
                    "unknown cannot be set as a default tester, since this user does not exist.",
                ]
            },
            status_code=HTTPStatus.BAD_REQUEST,
        )

        case: TestCase
        for case in [self.case_1, self.case_2]:
            self.assertEqual(case.default_tester, TestCase.objects.get(pk=case.pk).default_tester)


class TestChangeTestCasePriority(BasePlanCase):
    """Test AJAX request to change test case priority"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.perm = "testcases.change_testcase"
        user_should_have_perm(cls.tester, cls.perm)
        cls.url = reverse("patch-cases")
        cls.request_data = {
            "case": [cls.case_1.pk, cls.case_3.pk],
            "target_field": "priority",
            "new_value": None,  # Must be set in the individual test
        }

    def test_change_priority(self):
        data = self.request_data.copy()
        p4 = Priority.objects.get(value="P4")
        data["new_value"] = p4.pk
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assert200(resp)
        self.assertEqual(p4, TestCase.objects.get(pk=self.case_1.pk).priority)
        self.assertEqual(p4, TestCase.objects.get(pk=self.case_3.pk).priority)

        case: TestCase
        for case in [self.case_1, self.case_3]:
            self.assertTrue(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="priority",
                    original_value=case.priority.value,
                    new_value=p4.value,
                ).exists()
            )

    def test_unknown_priority(self):
        data = self.request_data.copy()
        result = Priority.objects.aggregate(max_pk=Max("pk"))
        data["new_value"] = result["max_pk"] + 1
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assertJsonResponse(
            resp,
            {"message": ["The priority you specified to change does not exist."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )


class TestChangeTestCaseReviewer(BasePlanCase):
    """Test AJAX request to change test case reviewer"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.perm = "testcases.change_testcase"
        user_should_have_perm(cls.tester, cls.perm)
        cls.url = reverse("patch-cases")
        cls.request_data = {
            "case": [cls.case_1.pk, cls.case_3.pk],
            "target_field": "reviewer",
            "new_value": None,  # Must be set in the individual test
        }
        cls.reviewer = f.UserFactory(username="reviewer")

    def test_change_reviewer(self):
        data = self.request_data.copy()
        data["new_value"] = self.reviewer.username
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assert200(resp)

        case: TestCase
        for case in [self.case_1, self.case_3]:
            self.assertEqual(self.reviewer, TestCase.objects.get(pk=case.pk).reviewer)
            self.assertTrue(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="reviewer",
                    original_value=str(case.reviewer),
                    new_value=self.reviewer.username,
                ).exists()
            )

    def test_nonexistent_reviewer(self):
        data = self.request_data.copy()
        data["new_value"] = "someone"
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assertJsonResponse(
            resp,
            {"message": ["Reviewer someone is not found"]},
            status_code=HTTPStatus.BAD_REQUEST,
        )


class TestChangeTestCaseStatus(BasePlanCase):
    """Test AJAX request to change test case status"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.perm = "testcases.change_testcase"
        user_should_have_perm(cls.tester, cls.perm)
        cls.url = reverse("patch-cases")
        cls.request_data = {
            "from_plan": cls.plan.pk,
            "case": [cls.case_1.pk, cls.case_3.pk],
            "target_field": "case_status",
            "new_value": None,  # Must be set in the individual test
        }

    def test_change_status(self):
        data = self.request_data.copy()
        data["new_value"] = self.case_status_proposed.pk
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assertJsonResponse(resp, {})

        case: TestCase
        for case in [self.case_1, self.case_3]:
            self.assertEqual(
                self.case_status_proposed, TestCase.objects.get(pk=case.pk).case_status
            )
            self.assertTrue(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="case_status",
                    original_value=case.case_status.name,
                    new_value=self.case_status_proposed.name,
                ).exists()
            )

    def test_nonexistent_status(self):
        data = self.request_data.copy()
        result = TestCaseStatus.objects.aggregate(max_pk=Max("pk"))
        data["new_value"] = result["max_pk"] + 1
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assertJsonResponse(
            resp,
            {"message": ["The status you choose does not exist."]},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_avoid_updating_duplicate_status(self):
        data = self.request_data.copy()
        confirmed_status = TestCaseStatus.objects.get(name="CONFIRMED")
        data["new_value"] = confirmed_status.pk
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assert200(resp)
        for case_pk in data["case"]:
            self.assertFalse(
                TCMSLogModel.objects.filter(
                    who=self.tester,
                    field="case_status",
                    original_value=str(TestCase.objects.get(pk=case_pk).case_status),
                    new_value=confirmed_status.pk,
                    object_pk=case_pk,
                ).exists()
            )


class TestChangeTestCaseSortKey(BasePlanCase):
    """Test AJAX request to change test case sort key"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.perm = "testcases.change_testcase"
        user_should_have_perm(cls.tester, cls.perm)
        cls.url = reverse("patch-cases")
        cls.new_sort_key = 100
        cls.request_data = {
            "plan": cls.plan.pk,
            "case": [cls.case_1.pk, cls.case_3.pk],
            "target_field": "sortkey",
            "new_value": cls.new_sort_key,
        }

    def test_change_sort_key(self):
        data = self.request_data.copy()
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assert200(resp)
        self.assertEqual(
            self.new_sort_key,
            TestCasePlan.objects.get(plan=self.plan, case=self.case_1).sortkey,
        )
        self.assertEqual(
            self.new_sort_key,
            TestCasePlan.objects.get(plan=self.plan, case=self.case_3).sortkey,
        )

    def test_sort_key_is_out_of_range(self):
        data = self.request_data.copy()
        for sort_key in [SORT_KEY_MAX + 1, SORT_KEY_MAX + 10]:
            data["new_value"] = sort_key
            resp = self.client.patch(self.url, data=data, content_type="application/json")
            self.assertJsonResponse(
                resp,
                {"message": ["New sortkey is out of range [0, 32300]."]},
                status_code=HTTPStatus.BAD_REQUEST,
            )

    @patch("django.db.models.Manager.bulk_update")
    def test_avoid_updating_duplicate_sort_key(self, bulk_update):
        data = self.request_data.copy()
        # Sort key of case_3 should not be updated.
        new_sort_key = TestCasePlan.objects.get(plan=self.plan, case=self.case_3).sortkey
        data["new_value"] = new_sort_key
        resp = self.client.patch(self.url, data=data, content_type="application/json")
        self.assert200(resp)

        args, _ = bulk_update.call_args
        changed, changed_fields = args
        self.assertEqual(1, len(changed))  # Only sortkey of the case_1 is changed.
        changed_rel = changed[0]
        self.assertEqual(self.case_1, changed_rel.case)
        self.assertEqual(new_sort_key, changed_rel.sortkey)
        self.assertListEqual(["sortkey"], changed_fields)


class TestModuleUpdateActions(AuthMixin, HelperAssertions, test.TestCase):
    """Test the core behavior of ModuleUpdateActions class"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.case = f.TestCaseFactory()
        cls.perm = "testcases.change_testcase"

    def setUp(self):
        super().setUp()
        user_should_have_perm(self.tester, self.perm)

    def _request(
        self, target_field: Optional[str] = None, new_status: Optional[TestCaseStatus] = None
    ):
        new_value = 1 if new_status is None else new_status.pk
        return self.client.patch(
            reverse("patch-cases"),
            data={
                "case": [self.case.pk],
                "target_field": target_field or "case_status",
                "new_value": new_value,
            },
            content_type="application/json",
        )

    def test_no_perm(self):
        remove_perm_from_user(self.tester, self.perm)
        self.assert403(self._request())

    @patch("tcms.core.ajax.PatchTestCasesView._simple_patch")
    def test_return_default_json_if_action_returns_nothing(self, _update_case_status):
        _update_case_status.return_value = None
        self.assertJsonResponse(self._request(), {})

    def test_cannot_find_action_method(self):
        self.assertJsonResponse(
            self._request("unknown_field"),
            {"message": "Not know what to update."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @patch("tcms.core.ajax.PatchTestCasesView._simple_patch")
    def test_handle_raised_error_from_action_method(self, _update_case_status):
        _update_case_status.side_effect = ValueError

        self.assertJsonResponse(
            self._request(),
            {
                "message": "Update failed. Please try again or request support from your organization."
            },
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_missing_target_field(self):
        resp = self.client.patch(
            reverse("patch-cases"),
            data={
                "case": [self.case.pk],
                "new_value": 1,
            },
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp, {"message": "Missing argument target_field."}, status_code=HTTPStatus.BAD_REQUEST
        )

    def test_missing_new_value(self):
        resp = self.client.patch(
            reverse("patch-cases"),
            data={
                "case": [self.case.pk],
                "target_field": "case_status",
            },
            content_type="application/json",
        )
        self.assertJsonResponse(
            resp, {"message": ["Missing argument new_value."]}, status_code=HTTPStatus.BAD_REQUEST
        )

    @patch("tcms.testcases.models.TestCase.log_action")
    @patch("tcms.core.ajax.logger")
    def test_fallback_to_warning_if_log_action_fails(self, logger, log_action):
        log_action.side_effect = ValueError("something wrong")
        new_status = TestCaseStatus.objects.exclude(pk=self.case.case_status.pk)[0]
        resp = self._request(new_status=new_status)
        self.assert200(resp)
        logger.warning.assert_called_once_with(
            "Failed to log update action for case run %s. Field: %s, original: %s, new: %s, by: %s",
            self.case.pk,
            "case_status",
            str(TestCaseStatus.objects.get(pk=self.case.case_status.pk)),
            str(new_status),
            User.objects.get(pk=self.tester.pk),
        )


class TestAjaxGetInfo(HelperAssertions, test.TestCase):
    """Test AJAX request to get management objects"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.product_a = f.ProductFactory(name="Product A")
        cls.product_b = f.ProductFactory(name="Product B")

        cls.pa_ver_1_0 = f.VersionFactory(product=cls.product_a, value="1.0")
        cls.pa_ver_1_1 = f.VersionFactory(product=cls.product_a, value="1.1")
        cls.pa_ver_1_2dev = f.VersionFactory(product=cls.product_a, value="1.2dev")

        cls.pb_ver_202101 = f.VersionFactory(product=cls.product_b, value="202101")
        cls.pb_ver_202103 = f.VersionFactory(product=cls.product_b, value="202103")

        cls.build_1 = f.TestBuildFactory(name="build1", product=cls.product_a)
        cls.build_2 = f.TestBuildFactory(name="build2", product=cls.product_a, is_active=False)
        cls.build_3 = f.TestBuildFactory(name="build3", product=cls.product_b)

        cls.case_category_1 = f.TestCaseCategoryFactory(name="functional", product=cls.product_a)
        cls.case_category_2 = f.TestCaseCategoryFactory(name="auto", product=cls.product_a)
        cls.case_category_3 = f.TestCaseCategoryFactory(name="manual", product=cls.product_b)

        cls.component_db = f.ComponentFactory(name="db", product=cls.product_a)
        cls.component_docs = f.ComponentFactory(name="docs", product=cls.product_a)
        cls.component_cli = f.ComponentFactory(name="cli", product=cls.product_b)

        cls.env_win = f.TestEnvironmentFactory(name="win", product=cls.product_a)
        cls.env_linux = f.TestEnvironmentFactory(name="linux", product=cls.product_a)
        cls.env_bsd = f.TestEnvironmentFactory(name="bsd", product=cls.product_a)

        cls.env_group_a = f.TCMSEnvGroupFactory(name="group-a")
        cls.env_group_b = f.TCMSEnvGroupFactory(name="group-b")

        cls.env_property_py = f.TCMSEnvPropertyFactory(name="python")
        f.TCMSEnvValueFactory(value="3.8", property=cls.env_property_py)
        f.TCMSEnvValueFactory(value="3.9", property=cls.env_property_py)
        f.TCMSEnvValueFactory(value="3.10", property=cls.env_property_py)
        cls.env_property_go = f.TCMSEnvPropertyFactory(name="go")
        f.TCMSEnvValueFactory(value="1.14", property=cls.env_property_go)
        f.TCMSEnvValueFactory(value="1.15", property=cls.env_property_go)

        cls.env_property_rust = f.TCMSEnvPropertyFactory(name="rust")

        f.TCMSEnvGroupPropertyMapFactory(group=cls.env_group_a, property=cls.env_property_py)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.env_group_a, property=cls.env_property_go)
        f.TCMSEnvGroupPropertyMapFactory(group=cls.env_group_b, property=cls.env_property_rust)

        cls.url = reverse("ajax-getinfo")

    def test_unknown_info_type(self):
        resp = self.client.get(
            self.url, data={"product_id": self.product_a.pk, "info_type": "unknown info type"}
        )
        self.assertJsonResponse(
            resp, {"message": "Unrecognizable infotype"}, status_code=HTTPStatus.BAD_REQUEST
        )

    def test_missing_info_type(self):
        resp = self.client.get(self.url, data={"product_id": self.product_a.pk})
        self.assertJsonResponse(
            resp, {"message": "Missing parameter info_type."}, status_code=HTTPStatus.BAD_REQUEST
        )

    def test_invalid_product_id(self):
        resp = self.client.get(self.url, data={"product_id": "productname", "info_type": "envs"})
        self.assertJsonResponse(
            resp,
            {"message": "Invalid product id productname. It must be a positive integer."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_get_data_in_ulli_format(self):
        resp = self.client.get(
            self.url,
            data={"product_id": self.product_a.pk, "info_type": "builds", "format": "ulli"},
        )
        bs = BeautifulSoup(resp.content.decode(), "html.parser")
        build_names = sorted(item.text for item in bs.find_all("li"))
        expected = sorted(
            TestBuild.objects.filter(product=self.product_a).values_list("name", flat=True)
        )
        self.assertListEqual(expected, build_names)

    @staticmethod
    def _sort_serialized_data(json_data):
        return sorted(json_data, key=itemgetter("pk"))

    def _assert_request_data(self, request_data, expected_objects):
        resp = self.client.get(self.url, data=request_data)
        test_data = self._sort_serialized_data(json.loads(resp.content))
        expected = self._sort_serialized_data(
            json.loads(serializers.serialize("json", expected_objects, fields=("name", "value"))),
        )
        self.assertEqual(expected, test_data)

    def test_get_versions(self):
        self._assert_request_data(
            {"product_id": self.product_a.pk, "info_type": "versions"},
            Version.objects.filter(product=self.product_a),
        )

    def test_get_test_builds(self):
        products = [self.product_a.pk, self.product_b.pk]
        for is_active in [True, False]:
            data = {"product_id": products, "info_type": "builds"}
            if is_active:
                data["is_active"] = 1
            expected_filter = {"product__in": products}
            if is_active:
                expected_filter["is_active"] = 1

            self._assert_request_data(data, TestBuild.objects.filter(**expected_filter))

    def test_get_case_categories(self):
        self._assert_request_data(
            {"product_id": self.product_a.pk, "info_type": "categories"},
            TestCaseCategory.objects.filter(product=self.product_a),
        )

    def test_get_case_components(self):
        self._assert_request_data(
            {"product_id": self.product_a.pk, "info_type": "components"},
            Component.objects.filter(product=self.product_a),
        )

    def test_get_environments(self):
        self._assert_request_data(
            {"product_id": self.product_a.pk, "info_type": "envs"},
            TestEnvironment.objects.filter(product=self.product_a),
        )

    def test_get_env_groups(self):
        self._assert_request_data({"info_type": "env_groups"}, TCMSEnvGroup.objects.all())

    def test_get_env_properties(self):
        self._assert_request_data({"info_type": "env_properties"}, TCMSEnvProperty.objects.all())

    def test_get_env_properties_by_group(self):
        self._assert_request_data(
            {"info_type": "env_properties", "env_group_id": self.env_group_a.pk},
            TCMSEnvProperty.objects.filter(name__in=["python", "go"]),
        )

    def test_get_env_values(self):
        self._assert_request_data(
            {"info_type": "env_values", "env_property_id": self.env_property_go.pk},
            TCMSEnvValue.objects.filter(value__in=["1.14", "1.15"]),
        )

    def test_get_env_values_without_specifying_property_id(self):
        self._assert_request_data({"info_type": "env_values"}, [])


@pytest.mark.parametrize(
    "criteria,expected_username",
    [
        [{"username": "user1"}, "user1"],
        [{"email__contains": "myhome.io"}, "user2"],
    ],
)
def test_get_users_info(criteria, expected_username, base_data: BaseDataContext, client):
    User.objects.create(username="user1", email="user1@localhost")
    User.objects.create(username="user2", email="user2@myhome.io")
    data = {"info_type": "users"}
    data.update(criteria)
    response = client.get(reverse("ajax-getinfo"), data=data)

    test_data = sorted(json.loads(response.content), key=itemgetter("pk"))
    expected = sorted(
        json.loads(
            serializers.serialize(
                "json", User.objects.filter(username=expected_username), fields=("name", "value")
            )
        ),
        key=itemgetter("pk"),
    )
    assert expected == test_data


@pytest.mark.parametrize(
    "criteria,expected_tags",
    [
        [{}, ["python", "rust", "ruby", "perl"]],
        [{"name__startswith": "ru"}, ["rust", "ruby"]],
    ],
)
@pytest.mark.django_db
def test_get_tags_info(criteria: Dict[str, str], expected_tags: List[str], client):
    for tag in ("python", "rust", "ruby", "perl"):
        TestTag.objects.create(name=tag)

    data = {"info_type": "tags"}
    data.update(criteria)
    response = client.get(reverse("ajax-getinfo"), data=data)

    got = sorted(item["fields"]["name"] for item in json.loads(response.content))
    expected = sorted(expected_tags)
    assert expected == got

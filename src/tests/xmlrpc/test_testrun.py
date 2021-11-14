# -*- coding: utf-8 -*-

import itertools
import operator
import xmlrpc.client
from http import HTTPStatus
from typing import Any, Callable, ContextManager, Dict, List, Union

import pytest
from django import test
from django.contrib.auth.models import User

from tcms.core.utils import string_to_list
from tcms.management.models import TCMSEnvProperty, TCMSEnvValue, TestTag, Version
from tcms.testcases.models import TestCase
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TCMSEnvRunValueMap, TestCaseRun, TestRun, TestRunTag
from tcms.xmlrpc.api import testrun as testrun_api
from tcms.xmlrpc.serializer import datetime_to_str
from tcms.xmlrpc.utils import pre_process_ids
from tests import BaseDataContext
from tests import factories as f
from tests import user_should_have_perm
from tests.xmlrpc.utils import XmlrpcAPIBaseTest, make_http_request


class TestGet(test.TestCase):
    """Test TestRun.get"""

    @classmethod
    def setUpTestData(cls):
        cls.user = f.UserFactory()
        cls.http_req = make_http_request(user=cls.user)

        cls.product = f.ProductFactory()
        cls.version = f.VersionFactory(product=cls.product)
        cls.build = f.TestBuildFactory(product=cls.product)
        cls.plan = f.TestPlanFactory(
            product=cls.product,
            product_version=cls.version,
        )
        cls.plan_manager = f.UserFactory()
        cls.plan_default_tester = f.UserFactory()
        cls.tag_fedora = f.TestTagFactory(name="fedora")
        cls.tag_python = f.TestTagFactory(name="automation")
        cls.test_run = f.TestRunFactory(
            plan_text_version=1,
            notes="Running tests ...",
            product_version=cls.version,
            build=cls.build,
            plan=cls.plan,
            manager=cls.plan_manager,
            default_tester=cls.plan_default_tester,
            tag=[cls.tag_fedora, cls.tag_python],
        )

    def test_non_existing_id(self):
        result = testrun_api.get(self.http_req, self.test_run.pk + 1)
        self.assertNotIsInstance(result, dict)

    def test_get(self):
        expected_run = {
            "run_id": self.test_run.pk,
            "summary": self.test_run.summary,
            "plan_text_version": 1,
            "start_date": datetime_to_str(self.test_run.start_date),
            "stop_date": None,
            "notes": self.test_run.notes,
            "estimated_time": "00:00:00",
            "environment_id": 0,
            "plan_id": self.plan.pk,
            "plan": self.plan.name,
            "build_id": self.build.pk,
            "build": self.build.name,
            "manager_id": self.plan_manager.pk,
            "manager": self.plan_manager.username,
            "product_version_id": self.version.pk,
            "product_version": self.version.value,
            "default_tester_id": self.plan_default_tester.pk,
            "default_tester": self.plan_default_tester.username,
            "env_value": [],
            "tag": ["automation", "fedora"],
            "cc": [],
            "auto_update_run_status": False,
        }

        run = testrun_api.get(self.http_req, self.test_run.pk)
        run["tag"].sort()
        self.assertEqual(expected_run, run)


class TestGetIssues(XmlrpcAPIBaseTest):
    """Test get_issues"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.run_1 = f.TestRunFactory()
        cls.case_1 = f.TestCaseFactory(plan=[cls.run_1.plan])
        cls.case_2 = f.TestCaseFactory(plan=[cls.run_1.plan])
        cls.case_run_1 = f.TestCaseRunFactory(case=cls.case_1, run=cls.run_1)
        cls.case_run_2 = f.TestCaseRunFactory(case=cls.case_2, run=cls.run_1)

        cls.run_2 = f.TestRunFactory()
        cls.case_3 = f.TestCaseFactory(plan=[cls.run_2.plan])
        cls.case_4 = f.TestCaseFactory(plan=[cls.run_2.plan])
        cls.case_run_3 = f.TestCaseRunFactory(case=cls.case_3, run=cls.run_2)
        cls.case_run_4 = f.TestCaseRunFactory(case=cls.case_4, run=cls.run_2)

        cls.tracker = f.IssueTrackerFactory(
            name="coolbz",
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            validate_regex=r"^\d+$",
        )

        cls.case_run_1.add_issue("1", cls.tracker)
        cls.case_run_1.add_issue("2", cls.tracker)
        cls.case_run_2.add_issue("3", cls.tracker)
        cls.case_run_3.add_issue("4", cls.tracker)
        cls.case_run_4.add_issue("5", cls.tracker)
        cls.case_run_4.add_issue("6", cls.tracker)

    def test_get_issues(self):
        test_data = (
            (self.run_1.pk, ("1", "2", "3")),
            ([self.run_1.pk, self.run_2.pk], ("1", "2", "3", "4", "5", "6")),
            (f"{self.run_1.pk}, {self.run_2.pk}", ("1", "2", "3", "4", "5", "6")),
        )

        for run_ids, expected_issue_keys in test_data:
            issues = testrun_api.get_issues(self.request, run_ids)
            issue_keys = tuple(
                item["issue_key"] for item in sorted(issues, key=operator.itemgetter("issue_key"))
            )
            self.assertEqual(expected_issue_keys, issue_keys)


@pytest.mark.parametrize("run_ids", ["", 1, [1, 2]])
@pytest.mark.parametrize("case_ids", ["", 1, [2, 3]])
def test_add_cases(run_ids, case_ids, tester, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    case_1: TestCase = base_data.case_creator(pk=1, summary="case 1")
    case_2: TestCase = base_data.case_creator(pk=2, summary="case 2")
    case_3: TestCase = base_data.case_creator(pk=3, summary="case 3")

    plan.add_case(case_1)
    plan.add_case(case_2)
    plan.add_case(case_3)

    run_1: TestRun = base_data.run_creator(pk=1, plan=plan)
    run_2: TestRun = base_data.run_creator(pk=2, plan=plan)

    request = make_http_request(tester, "testruns.add_testcaserun")
    testrun_api.add_cases(request, run_ids, case_ids)

    if run_ids == "" or case_ids == "":
        assert not TestCaseRun.objects.filter(run=run_1).exists()
        assert not TestCaseRun.objects.filter(run=run_2).exists()
        return

    for run_id, case_id in itertools.product(pre_process_ids(run_ids), pre_process_ids(case_ids)):
        assert TestCaseRun.objects.filter(run_id=run_id, case_id=case_id).exists()


@pytest.mark.parametrize("run_ids", ["", 1, [1, 2]])
@pytest.mark.parametrize("case_ids", ["", 1, [2, 3]])
def test_remove_cases(run_ids, case_ids, tester, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    case_1: TestCase = base_data.case_creator(pk=1, summary="case 1")
    case_2: TestCase = base_data.case_creator(pk=2, summary="case 2")
    case_3: TestCase = base_data.case_creator(pk=3, summary="case 3")

    plan.add_case(case_1)
    plan.add_case(case_2)
    plan.add_case(case_3)

    run_1: TestRun = base_data.run_creator(pk=1, plan=plan)
    run_1.add_case_run(case_1)
    run_2: TestRun = base_data.run_creator(pk=2, plan=plan)
    run_2.add_case_run(case_2)
    run_2.add_case_run(case_3)

    request = make_http_request(tester, "testruns.delete_testcaserun")
    testrun_api.remove_cases(request, run_ids, case_ids)

    if run_ids == "" or case_ids == "":
        assert TestCaseRun.objects.filter(run=run_1, case=case_1).exists()
        assert TestCaseRun.objects.filter(run=run_2, case=case_2).exists()
        assert TestCaseRun.objects.filter(run=run_2, case=case_3).exists()
        return

    for run_id, case_id in itertools.product(pre_process_ids(run_ids), pre_process_ids(case_ids)):
        assert not TestCaseRun.objects.filter(run_id=run_id, case_id=case_id).exists()


@pytest.mark.parametrize("run_ids", ["", 1, [1, 2]])
@pytest.mark.parametrize("tags", ["", "tag1,tag3", ["tag1", "tag2"]])
def test_add_tag(
    run_ids: Union[int, List[int]],
    tags: Union[str, List[str]],
    tester,
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    run_1: TestRun = base_data.run_creator(pk=1, plan=plan)
    run_2: TestRun = base_data.run_creator(pk=2, plan=plan)

    TestTag.objects.create(name="tag1")
    TestTag.objects.create(name="tag2")

    request = make_http_request(tester, "testruns.add_testruntag")

    testrun_api.add_tag(request, run_ids, tags)

    if run_ids == "" or tags == "":
        assert not TestRunTag.objects.filter(run=run_1).exists()
        assert not TestRunTag.objects.filter(run=run_2).exists()
        return

    for run_id, tag in itertools.product(pre_process_ids(run_ids), string_to_list(tags)):
        assert TestRunTag.objects.filter(run_id=run_id, tag__name=tag).exists()


@pytest.mark.parametrize("run_ids", ["", 1, [1, 2]])
@pytest.mark.parametrize("tags", ["", "tag1,tag3", ["tag1", "tag2"]])
def test_remove_tag(
    run_ids: Union[int, List[int]],
    tags: Union[str, List[str]],
    tester,
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    base_data.run_creator(pk=1, plan=plan)
    run_2: TestRun = base_data.run_creator(pk=2, plan=plan)

    run_2.add_tag(TestTag.objects.create(name="tag1"))
    run_2.add_tag(TestTag.objects.create(name="tag2"))

    request = make_http_request(tester, "testruns.delete_testruntag")

    testrun_api.remove_tag(request, run_ids, tags)

    if run_ids == "" or tags == "":
        assert TestRunTag.objects.filter(run=run_2, tag__name="tag1").exists()
        assert TestRunTag.objects.filter(run=run_2, tag__name="tag2").exists()
        return

    for run_id, tag in itertools.product(pre_process_ids(run_ids), string_to_list(tags)):
        assert not TestRunTag.objects.filter(run_id=run_id, tag__name=tag).exists()


@pytest.mark.parametrize("target_func", [testrun_api.env_value, testrun_api.link_env_value])
@pytest.mark.parametrize("run_ids", ["", 1, [1, 2]])
@pytest.mark.parametrize("env_value_ids", ["", 1, "2,3", [1, 2]])
def test_add_env_value(
    target_func: Callable,
    run_ids: Union[str, int, List[int]],
    env_value_ids: Union[str, int, List[int]],
    tester,
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    run_1: TestRun = base_data.run_creator(pk=1, plan=plan)
    run_2: TestRun = base_data.run_creator(pk=2, plan=plan)

    property_py = TCMSEnvProperty.objects.create(name="py")
    TCMSEnvValue.objects.create(pk=1, value="3.9", property=property_py)
    TCMSEnvValue.objects.create(pk=2, value="3.8", property=property_py)

    request = make_http_request(tester)

    if target_func is testrun_api.env_value:
        user_should_have_perm(request.user, "testruns.change_tcmsenvrunvaluemap")
        testrun_api.env_value(request, "add", run_ids, env_value_ids)
    elif target_func is testrun_api.link_env_value:
        user_should_have_perm(request.user, "testruns.add_tcmsenvrunvaluemap")
        testrun_api.link_env_value(request, run_ids, env_value_ids)

    if run_ids == "" or env_value_ids == "":
        assert not TCMSEnvRunValueMap.objects.filter(run=run_1).exists()
        assert not TCMSEnvRunValueMap.objects.filter(run=run_2).exists()
        return

    for run_id, env_value_id in itertools.product(
        pre_process_ids(run_ids),
        pre_process_ids(env_value_ids),
    ):
        if env_value_id == 3:
            # Env value with id 3 does not exist.
            assert not TCMSEnvRunValueMap.objects.filter(
                run_id=run_id, value_id=env_value_id
            ).exists()
        else:
            assert TCMSEnvRunValueMap.objects.filter(run_id=run_id, value_id=env_value_id).exists()


@pytest.mark.parametrize("target_func", [testrun_api.env_value, testrun_api.unlink_env_value])
@pytest.mark.parametrize("run_ids", ["", 1, [1, 2]])
@pytest.mark.parametrize("env_value_ids", ["", 1, "2,3", [1, 2]])
def test_remove_env_value(
    target_func: Callable,
    run_ids: Union[str, int, List[int]],
    env_value_ids: Union[str, int, List[int]],
    tester,
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    run_1: TestRun = base_data.run_creator(pk=1, plan=plan)
    run_2: TestRun = base_data.run_creator(pk=2, plan=plan)

    property_py = TCMSEnvProperty.objects.create(name="py")
    value_1 = TCMSEnvValue.objects.create(pk=1, value="3.9", property=property_py)
    value_2 = TCMSEnvValue.objects.create(pk=2, value="3.8", property=property_py)
    value_3 = TCMSEnvValue.objects.create(pk=3, value="3.10", property=property_py)

    run_1.add_env_value(value_1)
    run_1.add_env_value(value_2)
    run_2.add_env_value(value_3)

    request = make_http_request(tester)

    if target_func is testrun_api.env_value:
        user_should_have_perm(request.user, "testruns.change_tcmsenvrunvaluemap")
        testrun_api.env_value(request, "remove", run_ids, env_value_ids)
    elif target_func is testrun_api.unlink_env_value:
        user_should_have_perm(request.user, "testruns.delete_tcmsenvrunvaluemap")
        testrun_api.unlink_env_value(request, run_ids, env_value_ids)

    for run_id, env_value_id in itertools.product(
        pre_process_ids(run_ids),
        pre_process_ids(env_value_ids),
    ):
        assert not TCMSEnvRunValueMap.objects.filter(run_id=run_id, value_id=env_value_id).exists()


@pytest.mark.parametrize(
    "criteria,expected_run_ids",
    [
        [{"product_version__value": "4.10"}, [2]],
        [{"plan": 2}, [3]],
        [{"run_id": 1}, [1]],
        [{"build__name": "dev_build"}, [1, 2, 3]],
    ],
)
def test_filter_and_get_count(
    criteria: Dict[str, Any], expected_run_ids: List[int], tester, base_data: BaseDataContext
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    new_version = Version.objects.create(value="4.10", product=base_data.product)
    base_data.run_creator(pk=1, plan=plan)
    base_data.run_creator(pk=2, plan=plan, product_version=new_version)

    plan_2: TestPlan = base_data.plan_creator(pk=2, name="plan 2")
    base_data.run_creator(pk=3, plan=plan_2)

    request = make_http_request(tester)
    runs = testrun_api.filter(request, criteria)
    assert expected_run_ids == sorted(item["run_id"] for item in runs)
    assert len(expected_run_ids) == testrun_api.filter_count(request, criteria)


@pytest.mark.parametrize(
    "run_id,expected",
    [
        [1, []],
        [100, []],  # nonexisting run id.
        [
            2,
            [
                {
                    "id": 1,
                    "value": "3.9",
                    "is_active": True,
                    "property_id": 1,
                    "property": "py",
                },
                {
                    "id": 2,
                    "value": "3.10",
                    "is_active": True,
                    "property_id": 1,
                    "property": "py",
                },
            ],
        ],
    ],
)
def test_get_env_values(run_id, expected, tester, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    base_data.run_creator(pk=1, plan=plan)
    run_2: TestRun = base_data.run_creator(pk=2, plan=plan)

    property_py = TCMSEnvProperty.objects.create(pk=1, name="py")
    run_2.add_env_value(TCMSEnvValue.objects.create(pk=1, value="3.9", property=property_py))
    run_2.add_env_value(TCMSEnvValue.objects.create(pk=2, value="3.10", property=property_py))

    request = make_http_request(tester)
    assert expected == sorted(
        testrun_api.get_env_values(request, run_id), key=lambda item: item["id"]
    )


@pytest.mark.parametrize(
    "run_id,expected",
    [
        [2, []],
        [100, []],  # nonexisting run id.
        [1, ["tag1", "tag2"]],
    ],
)
def test_get_tags(run_id: int, expected, tester, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    run_1: TestRun = base_data.run_creator(pk=1, plan=plan)

    run_1.add_tag(TestTag.objects.create(name="tag1"))
    run_1.add_tag(TestTag.objects.create(name="tag2"))

    base_data.run_creator(pk=2, plan=plan)

    request = make_http_request(tester)

    if run_id == 100:
        with pytest.raises(xmlrpc.client.Fault) as exc:
            testrun_api.get_tags(request, run_id)
        assert HTTPStatus.NOT_FOUND == exc.value.faultCode
    else:
        assert expected == [
            item["name"]
            for item in sorted(
                testrun_api.get_tags(request, run_id),
                key=lambda item: item["id"],
            )
        ]


@pytest.mark.parametrize(
    "run_id,expected",
    [
        [0, []],
        [100, []],
        [1, []],
        [2, [1, 2]],
    ],
)
def test_get_test_case_runs(run_id, expected, tester, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    case_1: TestCase = base_data.case_creator(pk=1, summary="case 1")
    case_2: TestCase = base_data.case_creator(pk=2, summary="case 2")

    plan.add_case(case_1)
    plan.add_case(case_2)

    base_data.run_creator(pk=1, plan=plan)
    run_2: TestRun = base_data.run_creator(pk=2, plan=plan)
    TestCaseRun.objects.create(
        pk=1,
        run=run_2,
        case=case_1,
        case_text_version=1,
        build=base_data.dev_build,
        case_run_status=base_data.case_run_status_running,
    )
    TestCaseRun.objects.create(
        pk=2,
        run=run_2,
        case=case_2,
        case_text_version=1,
        build=base_data.dev_build,
        case_run_status=base_data.case_run_status_idle,
    )

    request = make_http_request(tester)

    result = testrun_api.get_test_case_runs(request, run_id)
    assert expected == sorted(item["case_run_id"] for item in result)


@pytest.mark.parametrize(
    "run_id,expected",
    [
        [100, []],
        [2, []],
        [
            1,
            [
                {"case_id": 1, "case_run_id": 1, "case_run_status": "IDLE"},
                {"case_id": 2, "case_run_id": 2, "case_run_status": "FAILED"},
            ],
        ],
    ],
)
def test_get_test_cases(run_id, expected, tester, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    case_1: TestCase = base_data.case_creator(pk=1, summary="case 1")
    case_2: TestCase = base_data.case_creator(pk=2, summary="case 2")

    plan.add_case(case_1)
    plan.add_case(case_2)

    run_1: TestRun = base_data.run_creator(pk=1, plan=plan)
    TestCaseRun.objects.create(
        pk=1,
        run=run_1,
        case=case_1,
        case_run_status=base_data.case_run_status_idle,
        case_text_version=1,
        build=base_data.dev_build,
    )
    TestCaseRun.objects.create(
        pk=2,
        run=run_1,
        case=case_2,
        case_run_status=base_data.case_run_status_failed,
        case_text_version=1,
        build=base_data.dev_build,
    )

    base_data.run_creator(pk=2, plan=plan)

    request = make_http_request(tester)
    result = sorted(testrun_api.get_test_cases(request, run_id), key=operator.itemgetter("case_id"))
    for expected_case, result_case in zip(expected, result):
        assert expected_case["case_id"] == result_case["case_id"]
        assert expected_case["case_run_id"] == result_case["case_run_id"]
        assert expected_case["case_run_status"] == result_case["case_run_status"]


@pytest.mark.parametrize("run_id,expected", [[100, None], [1, 1]])
def test_get_plan(run_id, expected, tester, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    case_1: TestCase = base_data.case_creator(pk=1, summary="case 1")
    run_1: TestRun = base_data.run_creator(pk=1, plan=plan)
    run_1.add_case_run(case_1)

    request = make_http_request(tester)

    if run_id == 100:
        with pytest.raises(xmlrpc.client.Fault) as exc:
            testrun_api.get_test_plan(request, run_id)
        assert HTTPStatus.NOT_FOUND == exc.value.faultCode
    else:
        assert expected == testrun_api.get_test_plan(request, run_id)["plan_id"]


@pytest.mark.parametrize(
    "run_ids,values,expected",
    [
        [1, {"plan_text_version": 100}, {"plan_text_version": 100}],
        [1, {"summary": "Updated"}, {"summary": "Updated"}],
        [1, {"estimated_time": "2m"}, {"estimated_time": "00:02:00"}],
        [1, {"notes": "new notes"}, {"notes": "new notes"}],
        [1, {"manager": 2}, {"manager_id": 2}],
        [1, {"default_tester": 2}, {"default_tester_id": 2}],
        [1, {"default_tester": None}, {"default_tester_id": None}],
        # The new plan's text version will be used to update
        [1, {"plan": 2}, {"plan_id": 2, "plan_text_version": 1}],
        # Use the specified plan_text_version to update
        [1, {"plan": 2, "plan_text_version": 2}, {"plan_id": 2, "plan_text_version": 2}],
        [1, {"build": 3}, {"build_id": 3}],
        [1, {"product": 1, "product_version": 3}, {"product_version_id": 3}],
        [1, {"notes": ""}, {"notes": ""}],
        [1, {"status": 0}, {"stop_date": None}],
        # The expected value will be checked separately.
        [1, {"status": 1}, {"stop_date": "special case"}],
        [
            1,
            {"product_version": 3},
            pytest.raises(
                xmlrpc.client.Fault, match='Field "product" is required by product_version'
            ),
        ],
        [1, {"estimated_time": "8640020"}, pytest.raises(xmlrpc.client.Fault)],
        # Nonexisting build id
        [1, {"build": 9999}, pytest.raises(xmlrpc.client.Fault)],
        [
            [1, 2],
            {"plan_text_version": 100, "summary": "Updated"},
            {"plan_text_version": 100, "summary": "Updated"},
        ],
    ],
)
def test_update(
    run_ids: Union[int, List[int]],
    values: Dict[str, Any],
    expected: Union[Dict[str, Any], ContextManager],
    tester,
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    case_1: TestCase = base_data.case_creator(pk=1, summary="case 1")
    run_1: TestRun = base_data.run_creator(
        pk=1, plan=plan, build=base_data.alpha_build, default_tester=tester
    )
    run_1.add_case_run(case_1)

    run_2: TestRun = base_data.run_creator(pk=2, plan=plan, build=base_data.alpha_build)
    run_2.add_case_run(case_1)

    plan_2: TestPlan = base_data.plan_creator(pk=2, name="plan 1")
    plan_2.add_text(tester, "document content")

    User.objects.create(pk=2, username="user1", email="user1@example.com")
    Version.objects.create(pk=3, value="pre-release", product=base_data.product)

    request = make_http_request(tester, "testruns.change_testrun")

    if not isinstance(expected, dict):
        with expected:
            testrun_api.update(request, run_ids, values)
        return

    updated_runs: List[Dict[str, Any]] = testrun_api.update(request, run_ids, values)

    if values.get("status") == 1:
        assert (
            updated_runs[0]["stop_date"] is not None
        ), "stop_date is not set when status is set to 1"
    else:
        for run in updated_runs:
            for field_name, field_value in expected.items():
                assert field_value == run[field_name]


@pytest.mark.parametrize(
    "extra_optional_fields,expected",
    [
        [{"product": 1}, {}],
        [{"product": 1, "estimated_time": "120s"}, {"estimated_time": 120}],
        [{"product": 1, "case": [1, 2]}, {"case": [1, 2]}],
        [{"product": 1, "tag": "tag1,tag2"}, {"tag": ["tag1", "tag2"]}],
        [{"product_version": 2}, pytest.raises(xmlrpc.client.Fault)],
        # Non-existing product version
        [{"product": 1, "product_version": 1000}, pytest.raises(xmlrpc.client.Fault)],
    ],
)
def test_create(
    extra_optional_fields, expected: Dict[str, Any], tester, base_data: BaseDataContext
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    base_data.case_creator(pk=1, summary="case 1")
    base_data.case_creator(pk=2, summary="case 2")

    summary = "new test run"
    values: Dict[str, Any] = {
        "plan": plan.pk,
        "build": base_data.dev_build.pk,
        "manager": tester.pk,
        "summary": summary,
        "product_version": base_data.product_version.pk,
        "plan_text_version": 1,
    }

    values.update(extra_optional_fields)

    request = make_http_request(tester, "testruns.add_testrun")

    if not isinstance(expected, dict):
        with expected:
            testrun_api.create(request, values)
        return

    new_run: Dict[str, Any] = testrun_api.create(request, values)

    assert plan.pk == new_run["plan_id"]
    assert base_data.dev_build.pk == new_run["build_id"]
    assert tester.pk == new_run["manager_id"]
    assert summary == new_run["summary"]
    assert base_data.product_version.pk == new_run["product_version_id"]

    for field_name, field_value in expected.items():
        if field_name == "case":
            assert field_value == list(
                TestCaseRun.objects.filter(run_id=new_run["run_id"])
                .values_list("case_id", flat=True)
                .order_by("case_id")
            )
        elif field_name == "tag":
            assert (
                list(
                    TestRunTag.objects.filter(run_id=new_run["run_id"], tag__name__in=field_value)
                    .values_list("tag__pk", flat=True)
                    .order_by("tag__pk")
                )
                == new_run["tag"]
            )
        else:
            assert field_value == new_run[field_name]

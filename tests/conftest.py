import itertools
from dataclasses import dataclass, field
from typing import Any, Optional

import pytest
from django.contrib.auth.models import User

from tcms.management.models import Classification, Priority, Product, TestBuild, Version
from tcms.testcases.models import TestCase, TestCaseCategory, TestCaseStatus
from tcms.testplans.models import TestPlan, TestPlanType
from tcms.testruns.models import TestCaseRunStatus, TestRun

TESTER_PASSWORD = "password"


@pytest.fixture
def tester(django_user_model):
    user: User = django_user_model.objects.create(username="tester", email="tester@example.com")
    user.set_password(TESTER_PASSWORD)
    user.save()
    return user


@pytest.fixture
def logged_in_tester(tester, client):
    client.login(username=tester.username, password=TESTER_PASSWORD)
    return tester


@pytest.fixture
@pytest.mark.django_db
def base_data(tester):
    return BaseDataContext(tester)


@dataclass
class BaseDataContext:
    tester: Optional[User] = field(repr=False, compare=False, default=None)

    classification: Classification = field(init=False, repr=False, compare=False)
    product: Product = field(init=False, repr=False, compare=False)
    product_version: Version = field(init=False, repr=False, compare=False)

    p1: Priority = field(init=False, repr=False, compare=False)
    p2: Priority = field(init=False, repr=False, compare=False)
    p3: Priority = field(init=False, repr=False, compare=False)

    dev_build: TestBuild = field(init=False, repr=False, compare=False)
    alpha_build: TestBuild = field(init=False, repr=False, compare=False)
    candidate_build: TestBuild = field(init=False, repr=False, compare=False)

    # for case
    case_status_proposed: TestCaseStatus = field(init=False, repr=False, compare=False)
    case_status_confirmed: TestCaseStatus = field(init=False, repr=False, compare=False)
    case_status_disabled: TestCaseStatus = field(init=False, repr=False, compare=False)
    case_status_need_update: TestCaseStatus = field(init=False, repr=False, compare=False)
    case_category_smoke: TestCaseCategory = field(init=False, repr=False, compare=False)
    case_category_regression: TestCaseCategory = field(init=False, repr=False, compare=False)

    # for plan
    plan_type_function: TestPlanType = field(init=False, repr=False, compare=False)
    plan_type_smoke: TestPlanType = field(init=False, repr=False, compare=False)
    plan_type_regression: TestPlanType = field(init=False, repr=False, compare=False)

    # # for run and case run
    case_run_status_idle: TestCaseRunStatus = field(init=False, repr=False, compare=False)
    case_run_status_running: TestCaseRunStatus = field(init=False, repr=False, compare=False)
    case_run_status_failed: TestCaseRunStatus = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self._plan_counter = itertools.count(1)
        self._case_counter = itertools.count(1)
        self._run_counter = itertools.count(1)

        if self.tester is None:
            self.tester = User.objects.create(username="tester", email="tester@example.com")

        self.classification = Classification.objects.create(name="webapp")
        self.product = Product.objects.create(
            pk=1, name="nitrate", classification=self.classification
        )
        self.product_version = Version.objects.create(pk=2, value="4.5", product=self.product)

        self.dev_build = TestBuild.objects.create(
            pk=2, name="dev_build", milestone="dev", product=self.product
        )
        self.alpha_build = TestBuild.objects.create(
            pk=3, name="alpha_build", milestone="alpha", product=self.product
        )
        self.candidate_build = TestBuild.objects.create(
            pk=4, name="candidate_build", milestone="CR", product=self.product
        )

        self.p1, _ = Priority.objects.get_or_create(value="P1")
        self.p2, _ = Priority.objects.get_or_create(value="P2")
        self.p3, _ = Priority.objects.get_or_create(value="P3")

        self.case_status_confirmed, _ = TestCaseStatus.objects.get_or_create(name="CONFIRMED")
        self.case_status_proposed, _ = TestCaseStatus.objects.get_or_create(name="PROPOSED")
        self.case_status_disabled, _ = TestCaseStatus.objects.get_or_create(name="DISABLED")
        self.case_status_need_update, _ = TestCaseStatus.objects.get_or_create(name="NEED_UPDATE")

        self.case_category_smoke, _ = TestCaseCategory.objects.get_or_create(
            name="Smoke", product=self.product
        )
        self.case_category_regression, _ = TestCaseCategory.objects.get_or_create(
            name="Regression", product=self.product
        )

        self.plan_type_function, _ = TestPlanType.objects.get_or_create(name="Function")
        self.plan_type_smoke, _ = TestPlanType.objects.get_or_create(name="Smoke")
        self.plan_type_regression, _ = TestPlanType.objects.get_or_create(name="Regression")

        self.case_run_status_idle, _ = TestCaseRunStatus.objects.get_or_create(name="IDLE")
        self.case_run_status_running, _ = TestCaseRunStatus.objects.get_or_create(name="RUNNING")
        self.case_run_status_failed, _ = TestCaseRunStatus.objects.get_or_create(name="FAILED")

    def create_plan(self, **kwargs) -> TestPlan:
        attrs: dict[str, Any] = {
            "author": self.tester,
            "owner": self.tester,
            "type": self.plan_type_function,
            "product": self.product,
            "product_version": self.product_version,
        }
        attrs.update(kwargs)
        if "name" not in attrs:
            attrs["name"] = f"Plan {next(self._plan_counter)}"
        return TestPlan.objects.create(**attrs)

    def create_case(self, **kwargs) -> TestCase:
        attrs: dict[str, Any] = {
            "case_status": self.case_status_confirmed,
            "priority": self.p1,
            "author": self.tester,
            "category": self.case_category_smoke,
        }
        attrs.update(kwargs)
        if "summary" not in attrs:
            attrs["summary"] = f"Case {next(self._case_counter)}"
        return TestCase.objects.create(**attrs)

    def create_test_run(self, **kwargs) -> TestRun:
        attrs: dict[str, Any] = {
            "plan_text_version": 1,
            "build": self.dev_build,
            "manager": self.tester,
            "product_version": self.product_version,
        }
        attrs.update(kwargs)
        if "summary" not in attrs:
            attrs["summary"] = f"Test run f{next(self._run_counter)}"
        return TestRun.objects.create(**attrs)

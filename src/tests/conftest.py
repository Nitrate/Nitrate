from functools import partial

import pytest
from django.contrib.auth.models import User

from tcms.management.models import Classification, Priority, Product, TestBuild, Version
from tcms.testcases.models import TestCase, TestCaseCategory, TestCaseStatus
from tcms.testplans.models import TestPlan, TestPlanType
from tcms.testruns.models import TestCaseRunStatus, TestRun
from tests import BaseDataContext

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
    c = BaseDataContext()
    c.classification = Classification.objects.create(name="webapp")
    c.product = Product.objects.create(pk=1, name="nitrate", classification=c.classification)
    c.product_version = Version.objects.create(pk=2, value="4.5", product=c.product)

    c.dev_build = TestBuild.objects.create(pk=2, name="dev_build", product=c.product)
    c.alpha_build = TestBuild.objects.create(pk=3, name="alpha_build", product=c.product)
    c.candidate_build = TestBuild.objects.create(pk=4, name="candidate_build", product=c.product)

    c.p1, _ = Priority.objects.get_or_create(value="P1")
    c.p2, _ = Priority.objects.get_or_create(value="P2")
    c.p3, _ = Priority.objects.get_or_create(value="P3")

    c.case_status_confirmed, _ = TestCaseStatus.objects.get_or_create(name="CONFIRMED")
    c.case_status_proposed, _ = TestCaseStatus.objects.get_or_create(name="PROPOSED")
    c.case_status_disabled, _ = TestCaseStatus.objects.get_or_create(name="DISABLED")
    c.case_status_need_update, _ = TestCaseStatus.objects.get_or_create(name="NEED_UPDATE")

    c.case_category_smoke, _ = TestCaseCategory.objects.get_or_create(
        name="Smoke", product=c.product
    )
    c.case_category_regression, _ = TestCaseCategory.objects.get_or_create(
        name="Regression", product=c.product
    )

    c.plan_type_function, _ = TestPlanType.objects.get_or_create(name="Function")
    c.plan_type_smoke, _ = TestPlanType.objects.get_or_create(name="Smoke")
    c.plan_type_regression, _ = TestPlanType.objects.get_or_create(name="Regression")

    c.case_run_status_idle, _ = TestCaseRunStatus.objects.get_or_create(name="IDLE")
    c.case_run_status_running, _ = TestCaseRunStatus.objects.get_or_create(name="RUNNING")
    c.case_run_status_failed, _ = TestCaseRunStatus.objects.get_or_create(name="FAILED")

    c.plan_creator = partial(
        TestPlan.objects.create,
        author=tester,
        owner=tester,
        type=c.plan_type_function,
        product=c.product,
        product_version=c.product_version,
    )

    c.case_creator = partial(
        TestCase.objects.create,
        case_status=c.case_status_confirmed,
        priority=c.p1,
        author=tester,
        category=c.case_category_smoke,
    )

    c.run_creator = partial(
        TestRun.objects.create,
        plan_text_version=1,
        build=c.dev_build,
        manager=tester,
        product_version=c.product_version,
    )

    return c

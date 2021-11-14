# -*- coding: utf-8 -*-
from textwrap import dedent
from typing import Dict, List, Optional, Tuple, Union

import pytest
from _pytest.python_api import RaisesContext
from django import test
from django.contrib.auth.models import User
from django.core import mail
from django.db.models import QuerySet
from django.db.utils import IntegrityError

from tcms.core.utils import checksum
from tcms.management.models import Component, TCMSEnvGroup, TestAttachment, TestTag
from tcms.testcases.models import NoneText, TestCase, TestCasePlan, TestCaseTag
from tcms.testplans.helpers import email
from tcms.testplans.models import (
    TCMSEnvPlanMap,
    TestPlan,
    TestPlanComponent,
    TestPlanTag,
    TestPlanText,
    _disconnect_signals,
    _listen,
)
from tcms.testruns.models import TestRun
from tests import BaseDataContext, BasePlanCase
from tests import factories as f
from tests import no_raised_error


class TestSendEmailOnPlanUpdated(test.TestCase):
    """Test send email on a plan is updated"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = f.UserFactory(username="owner", email="owner@example.com")
        cls.plan = f.TestPlanFactory(owner=cls.owner, author=cls.owner)
        cls.plan.current_user = cls.owner

        cls.plan.email_settings.auto_to_plan_owner = True
        cls.plan.email_settings.auto_to_plan_author = True
        cls.plan.email_settings.notify_on_plan_update = True
        cls.plan.email_settings.save()

    def setUp(self):
        _listen()

    def tearDown(self):
        _disconnect_signals()

    def test_send_email(self):
        self.plan.name = "Update to send email ..."
        self.plan.save()

        out_mail = mail.outbox[0]
        self.assertEqual(f"TestPlan {self.plan.pk} has been updated.", out_mail.subject)
        self.assertEqual(["owner@example.com"], out_mail.recipients())

        body = dedent(
            f"""\
            TestPlan [{self.plan.name}] has been updated by {self.owner.username}

            Plan -
            {self.plan.get_full_url()}

            --
            Configure mail: {self.plan.get_full_url()}/edit/
            ------- You are receiving this mail because: -------
            You have subscribed to the changes of this TestPlan
            You are related to this TestPlan"""
        )

        self.assertEqual(body, out_mail.body)


class TestSendEmailOnPlanDeleted(test.TestCase):
    """Test send email on a plan is deleted"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = f.UserFactory(username="owner", email="owner@example.com")
        cls.plan = f.TestPlanFactory(owner=cls.owner, author=cls.owner)

        cls.plan.email_settings.auto_to_plan_owner = True
        cls.plan.email_settings.auto_to_plan_author = True
        cls.plan.email_settings.notify_on_plan_delete = True
        cls.plan.email_settings.save()

    def setUp(self):
        _listen()

    def tearDown(self):
        _disconnect_signals()

    def test_send_email(self):
        plan_id = self.plan.pk
        self.plan.delete()

        out_mail = mail.outbox[0]
        self.assertEqual(f"TestPlan {plan_id} has been deleted.", out_mail.subject)
        self.assertEqual(["owner@example.com"], out_mail.recipients())

        body = dedent(
            f"""\
            TestPlan [{self.plan.name}] has been deleted.

            --

            ------- You are receiving this mail because: -------
            You have subscribed to the changes of this TestCase
            You are related to this TestCase"""
        )

        self.assertEqual(body, out_mail.body)


class TestGetPlanNotificationRecipients(test.TestCase):
    """Test TestPlan.get_notification_recipients"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = f.UserFactory(username="user1")
        cls.plan_owner = f.UserFactory(username="plan_owner")
        cls.plan = f.TestPlanFactory(owner=cls.plan_owner, author=cls.owner)

        cls.case_1 = f.TestCaseFactory(
            author=f.UserFactory(username="user2"),
            default_tester=f.UserFactory(username="user3"),
            plan=[cls.plan],
        )

        cls.case_2 = f.TestCaseFactory(
            author=f.UserFactory(username="user4"),
            default_tester=f.UserFactory(username="user5"),
            plan=[cls.plan],
        )

        cls.case_3 = f.TestCaseFactory(
            author=f.UserFactory(username="user6"),
            default_tester=f.UserFactory(username="user7", email=""),
            plan=[cls.plan],
        )

    def test_collect_recipients(self):
        # Test data is a tuple of 5-elements tuples, each of one contains:
        # auto_to_plan_owner, auto_to_plan_author,
        # auto_to_case_owner, auto_to_case_default_tester, expected
        test_data = (
            (0, 0, 0, 0, []),
            (1, 0, 0, 0, ["plan_owner@example.com"]),
            (1, 1, 0, 0, ["plan_owner@example.com", "user1@example.com"]),
            (
                1,
                1,
                1,
                0,
                [
                    "plan_owner@example.com",
                    "user1@example.com",
                    "user2@example.com",
                    "user4@example.com",
                    "user6@example.com",
                ],
            ),
            (
                1,
                1,
                1,
                1,
                [
                    "plan_owner@example.com",
                    "user1@example.com",
                    "user2@example.com",
                    "user3@example.com",
                    "user4@example.com",
                    "user5@example.com",
                    "user6@example.com",
                ],
            ),
        )

        for item in test_data:
            (
                auto_to_plan_owner,
                auto_to_plan_author,
                auto_to_case_owner,
                auto_to_case_default_tester,
                expected,
            ) = item

            es = self.plan.email_settings
            es.auto_to_plan_owner = bool(auto_to_plan_owner)
            es.auto_to_plan_author = bool(auto_to_plan_author)
            es.auto_to_case_owner = bool(auto_to_case_owner)
            es.auto_to_case_default_tester = bool(auto_to_case_default_tester)
            es.save()

            plan: TestPlan = TestPlan.objects.get(pk=self.plan.pk)

            # Since this test contains the case of plan.owner is None,
            # recover the plan's owner here.
            plan.owner = self.plan_owner
            plan.save(update_fields=["owner"])

            recipients = plan.get_notification_recipients()
            self.assertListEqual(expected, sorted(recipients))

            # plan's owner could be put into the test data, but that would make
            # the test data larger.
            plan.owner = None
            plan.save(update_fields=["owner"])

            recipients = sorted(plan.get_notification_recipients())
            if self.plan_owner.email in expected:
                expected.remove(self.plan_owner.email)
            self.assertListEqual(expected, recipients)

    def test_no_recipients_for_email_plan_update(self):
        es = self.plan.email_settings
        es.auto_to_plan_owner = False
        es.auto_to_plan_author = False
        es.auto_to_case_owner = False
        es.auto_to_case_default_tester = False
        es.save()

        plan = TestPlan.objects.get(pk=self.plan.pk)
        plan.current_user = self.owner
        email.email_plan_update(plan)

        self.assertEqual(len(mail.outbox), 0)

    def test_no_recipients_for_email_plan_deletion(self):
        es = self.plan.email_settings
        es.auto_to_plan_owner = False
        es.auto_to_plan_author = False
        es.auto_to_case_owner = False
        es.auto_to_case_default_tester = False
        es.save()

        plan = TestPlan.objects.get(pk=self.plan.pk)
        plan.current_user = self.owner
        email.email_plan_deletion(plan)

        self.assertEqual(len(mail.outbox), 0)


class TestPlanTreeView(BasePlanCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_treeview_data()

    def test_get_ancestor_ids(self):
        expected = [self.plan.pk, self.plan_2.pk, self.plan_3.pk]
        plan: TestPlan = TestPlan.objects.get(pk=self.plan_4.pk)
        self.assertListEqual(expected, sorted(plan.get_ancestor_ids()))

    def test_get_ancestors(self):
        ancestor_ids = [self.plan.pk, self.plan_2.pk, self.plan_3.pk]
        expected = list(
            TestPlan.objects.filter(pk__in=ancestor_ids).values_list("pk", flat=True).order_by("pk")
        )
        self.assertListEqual(
            list(
                TestPlan.objects.get(pk=self.plan_4.pk)
                .get_ancestors()
                .values_list("pk", flat=True)
                .order_by("pk")
            ),
            expected,
        )

    def test_get_descendant_ids(self):
        expected = [self.plan_4.pk, self.plan_5.pk, self.plan_6.pk, self.plan_7.pk]
        plan: TestPlan = TestPlan.objects.get(pk=self.plan_3.pk)
        self.assertListEqual(expected, sorted(plan.get_descendant_ids()))

    def test_get_descendants(self):
        descendant_ids = [
            self.plan_4.pk,
            self.plan_5.pk,
            self.plan_6.pk,
            self.plan_7.pk,
        ]
        expected = list(
            TestPlan.objects.get(pk=self.plan_3.pk)
            .get_descendants()
            .values_list("pk", flat=True)
            .order_by("pk")
        )
        self.assertListEqual(
            list(
                TestPlan.objects.filter(pk__in=descendant_ids)
                .values_list("pk", flat=True)
                .order_by("pk")
            ),
            expected,
        )

    def test_get_direct_descendants(self):
        test_data = [
            [self.plan.pk, [self.plan_2.pk]],
            [self.plan_5.pk, []],
            [self.plan_3.pk, [self.plan_4.pk, self.plan_7.pk]],
        ]

        for parent_plan, expected in test_data:
            plan: TestPlan = TestPlan.objects.get(pk=parent_plan)
            self.assertListEqual(expected, sorted(plan.get_descendant_ids(True)))


@pytest.mark.parametrize(
    "text,expected",
    [
        [[], None],
        [["add first text", "the second one"], "the second one"],
    ],
)
@pytest.mark.django_db()
def test_plan_latest_text(text: List[str], expected, tester):
    plan = f.TestPlanFactory()

    for item in text:
        plan.add_text(tester, item)

    if expected is None:
        assert expected == plan.latest_text()
    else:
        assert expected == plan.latest_text().plan_text


@pytest.mark.parametrize(
    "text,expected",
    [
        [[], False],
        [["add first text"], True],
        [["add first text", "the second one"], True],
    ],
)
@pytest.mark.django_db()
def test_plan_text_exist(text: List[str], expected, tester):
    plan = f.TestPlanFactory()

    for item in text:
        plan.add_text(tester, item)

    assert expected == plan.text_exist()


@pytest.mark.parametrize(
    "text,expected",
    [
        [[], None],
        [["add first text"], checksum("add first text")],
        [["add first text", "the second one"], checksum("the second one")],
    ],
)
@pytest.mark.django_db()
def test_plan_text_checksum(text: List[str], expected, tester):
    plan = f.TestPlanFactory()

    for item in text:
        plan.add_text(tester, item)

    assert expected == plan.text_checksum()


@pytest.mark.parametrize(
    "text_version,text,expected",
    [
        [None, [], None],
        [None, ["first"], "first"],
        [None, ["first", "second"], "second"],
        [1, [], None],
        [1, ["first"], "first"],
        [1, ["first", "second"], "first"],
        [2, [], None],
        [2, ["first"], None],
        [2, ["first", "second"], "second"],
    ],
)
@pytest.mark.django_db()
def test_plan_get_text_with_version(text_version: Optional[int], text: List[str], expected, tester):
    plan = f.TestPlanFactory()

    for item in text:
        plan.add_text(tester, item)

    the_text = plan.get_text_with_version(text_version)

    if expected is None:
        assert the_text is None
    else:
        assert expected == the_text.plan_text


@pytest.mark.parametrize("include_cases_count", [True, False])
@pytest.mark.parametrize("include_runs_count", [True, False])
@pytest.mark.parametrize("include_children_count", [True, False])
@pytest.mark.parametrize("test_empty_queryset", [True, False])
@pytest.mark.django_db()
def test_plan_apply_subtotal(
    test_empty_queryset: bool,
    include_cases_count: bool,
    include_runs_count: bool,
    include_children_count: bool,
    base_data: BaseDataContext,
    # tester,
):
    """Test TestPlan.apply_subtotal

    plan 1: 6 cases
    plan 2: child of 1
    plan 3: child of 1
    plan 4: 2 runs
    """
    plan_1: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    base_data.plan_creator(pk=2, name="plan 2", parent=plan_1)
    base_data.plan_creator(pk=3, name="plan 3", parent=plan_1)

    for i in range(6):
        plan_1.add_case(base_data.case_creator(pk=i + 1, summary=f"case summary {i + 1}"))

    plan_4: TestPlan = base_data.plan_creator(pk=4, name="plan 4")

    case_7 = base_data.case_creator(pk=7, summary="case summary 7")
    case_8 = base_data.case_creator(pk=8, summary="case summary 8")

    plan_4.add_case(case_7)
    plan_4.add_case(case_8)

    run_1: TestRun = base_data.run_creator(pk=1, summary="run 1", plan=plan_4)
    run_1.add_case_run(case_7)

    run_2: TestRun = base_data.run_creator(pk=2, summary="run 2", plan=plan_4)
    run_2.add_case_run(case_8)

    if test_empty_queryset:
        plans: QuerySet[TestPlan] = TestPlan.apply_subtotal(TestPlan.objects.none())
        assert [] == list(plans)
        return

    plans: QuerySet[TestPlan] = TestPlan.apply_subtotal(
        TestPlan.objects.filter(pk__in=[1, 4]),
        cases_count=include_cases_count,
        runs_count=include_runs_count,
        children_count=include_children_count,
    )

    for plan in plans:
        if plan.pk == 1:
            if include_cases_count:
                assert 6 == plan.cases_count
            else:
                assert not hasattr(plan, "cases_count")
            if include_runs_count:
                assert 0 == plan.runs_count
            else:
                assert not hasattr(plan, "runs_count")
            if include_children_count:
                assert 2 == plan.children_count
            else:
                assert not hasattr(plan, "children_count")
        elif plan.pk == 4:
            if include_cases_count:
                assert 2 == plan.cases_count
            else:
                assert not hasattr(plan, "cases_count")
            if include_runs_count:
                assert 2 == plan.runs_count
            else:
                assert not hasattr(plan, "runs_count")
            if include_children_count:
                assert 0 == plan.children_count
            else:
                assert not hasattr(plan, "children_count")


@pytest.mark.parametrize("has_text_already", [True, False])
@pytest.mark.parametrize(
    "text,text_checksum,text_version",
    [
        [None, None, None],
        ["", None, None],
        ["first text", None, None],
        ["first text", None, 3],
        ["first text", checksum("first text"), None],
        # The added text should have the specified text version 3.
        ["first text", checksum("first text"), 3],
        # Add an existing text. If the latest text has same checksum, return it
        # directly, otherwise add it.
        ["old text", None, None],
    ],
)
def test_plan_add_text(
    text: Union[str, None],
    text_checksum: Union[str, None],
    text_version: Union[int, None],
    has_text_already: bool,
    tester,
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")

    existing_plan_text: Union[TestPlanText, None] = None
    if has_text_already:
        existing_plan_text = plan.add_text(tester, "old text")

    added_text = plan.add_text(
        tester, text, text_checksum=text_checksum, plan_text_version=text_version
    )

    if text is None:
        assert added_text is None
    else:
        if has_text_already:
            if text == existing_plan_text.plan_text:
                assert added_text == existing_plan_text
                assert (
                    1 == TestPlanText.objects.filter(plan=plan).count()
                ), "No new text should be added"
            else:
                assert TestPlanText.objects.filter(plan=plan).count() > 1
                assert text == plan.latest_text().plan_text
                expected = 2 if text_version is None else text_version
                assert expected == added_text.plan_text_version
        else:
            assert text == added_text.plan_text
            assert checksum(text) == added_text.checksum
            expected = 1 if text_version is None else text_version
            assert expected == added_text.plan_text_version


@pytest.mark.parametrize(
    "plan_id,case_id_to_add,sort_key,expected",
    [
        # the first plan has case added.
        [1, 1, None, [(1, 1)]],
        [1, 2, None, [(1, 1), (2, None)]],
        [1, 2, 10, [(1, 1), (2, 10)]],
        # the second plan does not have any case yet.
        [2, 1, None, [(1, None)]],
        [2, 2, None, [(2, None)]],
        [2, 2, 10, [(2, 10)]],
    ],
)
def test_plan_add_case(
    plan_id: int,
    case_id_to_add: int,
    sort_key: Union[int, None],
    expected: List[Tuple[int, int]],
    base_data: BaseDataContext,
):
    """Test TestPlan.add_case"""
    plan_1: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    for i in range(3):
        base_data.case_creator(pk=i + 1, summary=f"case summary {i + 1}")
    plan_1.add_case(TestCase.objects.get(pk=1))

    base_data.plan_creator(pk=2, name="plan 2")

    TestPlan.objects.get(pk=plan_id).add_case(
        TestCase.objects.get(pk=case_id_to_add),
        sortkey=sort_key,
    )

    rel: Dict[str, int]
    result: List[Tuple[int, int]] = [
        (rel["case"], rel["sortkey"])
        for rel in TestCasePlan.objects.filter(plan_id=plan_id)
        .values("case", "sortkey")
        .order_by("case")
    ]
    assert expected == result


@pytest.mark.parametrize(
    "sort_keys,expected",
    [
        # The number of sort keys is also the number of cases to be created.
        [[], None],
        [[1, 1], 11],
        [[1, 2], 12],
        [[2, 1], 12],
    ],
)
def test_plan_get_case_sortkey(
    sort_keys: List[int],
    expected: Optional[int],
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")

    for sort_key in sort_keys:
        plan.add_case(base_data.case_creator(summary=f"case {sort_key}"), sort_key)

    assert expected == plan.get_case_sortkey()


@pytest.mark.parametrize(
    "component_name_to_add,expected",
    [
        # Test passing None to component argument
        [None, False],
        ["db", TestPlanComponent],
        # web is already associated with plan
        ["web", False],
    ],
)
def test_plan_add_component(
    component_name_to_add: Union[str, None],
    expected: Union[bool, TestPlanComponent],
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(name="plan 1")
    TestPlanComponent.objects.create(
        plan=plan,
        component=Component.objects.create(name="web", product=base_data.product),
    )
    component_db = Component.objects.create(name="db", product=base_data.product)

    component_to_add = None
    if component_name_to_add:
        component_to_add = Component.objects.get(name=component_name_to_add)

    rel: Union[TestPlanComponent, bool] = plan.add_component(component_to_add)

    if type(expected) == bool:
        assert expected == rel
    else:
        assert isinstance(rel, expected)
        assert plan == rel.plan
        assert component_db == rel.component


@pytest.mark.parametrize("group_name", ["os", "lang", None])
def test_plan_add_env_group(group_name, tester, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(name="plan 1")
    if group_name == "lang":
        plan.add_env_group(TCMSEnvGroup.objects.create(name="lang", manager=tester))

    if group_name is None:
        with pytest.raises(IntegrityError):
            plan.add_env_group(None)
    elif group_name == "lang":  # add duplicate env group again
        plan.add_env_group(TCMSEnvGroup.objects.get(name=group_name))
        # side-effect: the code does not handle the duplication. Should fix this?
        assert 2 == TCMSEnvPlanMap.objects.filter(plan=plan, group__name=group_name).count()
    else:
        env_group = TCMSEnvGroup.objects.create(name=group_name, manager=tester)
        plan.add_env_group(env_group)
        rels: List[TCMSEnvPlanMap] = list(TCMSEnvPlanMap.objects.all())
        assert 1 == len(rels)
        assert env_group == rels[0].group


@pytest.mark.parametrize("plan_id", [1, 2])
def test_plan_clear_env_groups(plan_id: int, tester, base_data: BaseDataContext):
    plan_1: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    plan_1.add_env_group(TCMSEnvGroup.objects.create(name="os", manager=tester))
    plan_1.add_env_group(TCMSEnvGroup.objects.create(name="lang", manager=tester))
    base_data.plan_creator(pk=2, name="plan 2")

    plan: TestPlan = TestPlan.objects.get(pk=plan_id)
    plan.clear_env_groups()

    assert 0 == TCMSEnvPlanMap.objects.filter(plan=plan).count()


@pytest.mark.parametrize("component_name", ["docs", "db"])
def test_plan_remove_component(component_name, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(name="plan 1")
    plan.add_component(Component.objects.create(name="webapp", product=base_data.product))
    plan.add_component(Component.objects.create(name="db", product=base_data.product))

    component_to_remove = Component.objects.filter(name=component_name).first()
    plan.remove_component(component_to_remove)

    assert not TestPlanComponent.objects.filter(plan=plan, component__name=component_name).exists()


@pytest.mark.parametrize("description", ["sample attachment", None])
def test_plan_add_attachment(description, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(name="plan 1")

    if description:
        attachment = TestAttachment.objects.create(
            description=description,
            file_name="hello.py",
            stored_name="/tmp/hello.py",
            checksum="abc",
        )
        rel = plan.add_attachment(attachment)
        assert attachment == rel.attachment
    else:
        with pytest.raises(IntegrityError):
            plan.add_attachment(None)


@pytest.mark.parametrize("tag_name", ["future-tag", None])
def test_plan_remove_non_existing_tag(tag_name, base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(name="plan 1")
    plan.add_tag(TestTag.objects.create(name="upstream"))
    plan.add_tag(TestTag.objects.create(name="local-tests"))
    TestTag.objects.create(name="future-tag")

    plan.remove_tag(TestTag.objects.get(name=tag_name) if tag_name else None)
    existing_tags = (
        TestPlanTag.objects.filter(plan=plan)
        .values_list("tag__name", flat=True)
        .order_by("tag__name")
    )
    assert ["local-tests", "upstream"] == list(existing_tags)


def test_plan_remove_existing_tag(base_data: BaseDataContext):
    plan: TestPlan = base_data.plan_creator(name="plan 1")
    plan.add_tag(TestTag.objects.create(name="upstream"))
    plan.add_tag(TestTag.objects.create(name="local-tests"))

    plan.remove_tag(TestTag.objects.get(name="local-tests"))

    existing_tags = (
        TestPlanTag.objects.filter(plan=plan)
        .values_list("tag__name", flat=True)
        .order_by("tag__name")
    )
    assert ["upstream"] == list(existing_tags)


@pytest.mark.parametrize("copy_attachments", [True, False])
@pytest.mark.parametrize("copy_environment_group", [True, False])
@pytest.mark.parametrize("copy_texts", [True, False])
@pytest.mark.parametrize("text_author", [None, "tester"])
@pytest.mark.parametrize("link_cases", [True, False])
@pytest.mark.parametrize("copy_cases", [True, False])
@pytest.mark.parametrize("component_initial_owner", [None, "tester"])
# whether the plan should have cases for this test. Mainly for testing the
# copy_tests with or without cases.
@pytest.mark.parametrize("has_cases", [True, False])
def test_plan_clone(
    has_cases: bool,
    copy_attachments: bool,
    copy_environment_group: bool,
    copy_texts: bool,
    text_author: Optional[str],
    link_cases: bool,
    copy_cases: bool,
    component_initial_owner: Optional[str],
    tester,
    base_data: BaseDataContext,
):
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    plan.add_text(tester, "first text")
    plan.add_text(tester, "second text")
    plan.add_tag(TestTag.objects.create(name="upstream"))
    plan.add_tag(TestTag.objects.create(name="smoke"))
    plan.add_attachment(
        TestAttachment.objects.create(
            description="fake for testing clone",
            file_name="hello.py",
            stored_name="/tmp/hello.py",
            checksum="abc",
        )
    )
    plan.add_env_group(TCMSEnvGroup.objects.create(name="os", manager=tester))

    if has_cases:
        case_1: TestCase = base_data.case_creator(pk=1, summary="case 1")
        plan.add_case(case_1)
        case_1.add_text("action1", "effect1", "setup1", "breakdown1", author=tester)
        # Add another one in order to test this latest text will be copied to the copied case.
        case_1.add_text("action2", "effect2", "setup2", "breakdown2", author=tester)

        case_2: TestCase = base_data.case_creator(pk=2, summary="case 2")
        plan.add_case(case_2)
        case_2.add_tag(TestTag.objects.create(name="upstream"))
        case_2.add_component(Component.objects.create(name="db", product=base_data.product))
        case_2.add_component(Component.objects.create(name="docs", product=base_data.product))

    if not copy_texts and not text_author:
        expected_error = pytest.raises(ValueError, match="Missing default text author")
    elif copy_cases and not component_initial_owner:
        expected_error = pytest.raises(ValueError, match="Missing default component initial owner")
    else:
        expected_error = no_raised_error()

    with expected_error:
        if text_author is None:
            default_text_author = None
        else:
            default_text_author = User.objects.get(username=text_author)
        if component_initial_owner is None:
            initial_owner = None
        else:
            initial_owner = User.objects.get(username=component_initial_owner)
        cloned_plan: TestPlan = plan.clone(
            default_component_initial_owner=initial_owner,
            copy_attachments=copy_attachments,
            copy_environment_group=copy_environment_group,
            copy_texts=copy_texts,
            default_text_author=default_text_author,
            link_cases=link_cases,
            copy_cases=copy_cases,
        )

    if isinstance(expected_error, RaisesContext):
        return

    assert "Copy of plan 1" == cloned_plan.name
    assert plan.product == cloned_plan.product
    assert plan.type == cloned_plan.type
    assert plan.is_active == cloned_plan.is_active
    assert plan.extra_link == cloned_plan.extra_link
    assert plan.author == cloned_plan.author
    assert plan.product_version == cloned_plan.product_version
    assert plan == cloned_plan.parent

    # TODO: how to assert the create_date? The microsecond is changed.
    # assert plan.create_date == cloned_plan.create_date

    if copy_texts:
        assert cloned_plan.text.filter(plan_text="first text").exists()
        assert cloned_plan.text.filter(plan_text="second text").exists()
    else:
        added_text: QuerySet[TestPlanText] = cloned_plan.text.all()
        assert 1 == len(added_text)
        assert "" == added_text[0].plan_text

    assert cloned_plan.tag.filter(name="upstream").exists()
    assert cloned_plan.tag.filter(name="smoke").exists()

    if copy_attachments:
        attachment: TestAttachment
        for attachment in plan.attachments.all():
            assert cloned_plan.attachments.filter(attachment_id=attachment.pk).exists()
    else:
        assert 0 == cloned_plan.attachments.count()

    if copy_environment_group:
        assert cloned_plan.env_group.filter(name="os").exists()
    else:
        assert 0 == cloned_plan.env_group.count()

    if link_cases and copy_cases and has_cases:
        # NOTE: no need to verify the copied test case once the code is migrated to TestCase.clone

        case: TestCase
        for case in plan.case.all():
            assert not TestCasePlan.objects.filter(
                plan=cloned_plan, case=case
            ).exists(), (
                f"Case {case.pk} should not be associated with cloned plan, since it is copied."
            )

            qs: QuerySet[TestCase] = TestCase.objects.filter(summary=case.summary).order_by("pk")
            orig_case: TestCase
            copied_case: TestCase
            orig_case, copied_case = list(qs)

            new_rel: TestCasePlan = TestCasePlan.objects.filter(
                plan=cloned_plan, case=copied_case
            ).first()
            assert (
                new_rel is not None
            ), f"Copied case {copied_case.pk} is not associated with plan {plan.pk}"

            orig_rel: TestCasePlan = TestCasePlan.objects.filter(plan=plan, case=orig_case).first()
            assert new_rel.sortkey == orig_rel.sortkey

            tag: TestTag
            for tag in orig_case.tag.all():
                assert TestCaseTag.objects.filter(case=copied_case, tag=tag).exists()

            orig_text = orig_case.get_text_with_version()
            # only one case has text added. This if is specifc to the case_1.
            if orig_text is not NoneText:
                copied_text = copied_case.get_text_with_version()
                assert orig_text.author == copied_text.author
                assert orig_text.action == copied_text.action
                assert orig_text.effect == copied_text.effect
                assert orig_text.setup == copied_text.setup
                assert orig_text.breakdown == copied_text.breakdown

    if link_cases and not copy_cases and has_cases:
        rel: TestCasePlan
        for rel in TestCasePlan.objects.filter(plan=plan):
            linked_rel: Optional[TestCasePlan] = TestCasePlan.objects.filter(
                plan=cloned_plan, case=rel.case
            ).first()
            assert linked_rel is not None
            assert rel.sortkey == linked_rel.sortkey

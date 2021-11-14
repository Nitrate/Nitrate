# -*- coding: utf-8 -*-

from datetime import timedelta
from textwrap import dedent
from unittest.mock import patch

import pytest
from django import test
from django.contrib.auth.models import User
from django.core import mail
from django.db.models import Max
from django.db.models.signals import post_delete, post_save, pre_save

from tcms.core.utils import checksum
from tcms.issuetracker.models import Issue
from tcms.management.models import Component, Priority, Product
from tcms.testcases import signals as case_watchers
from tcms.testcases.models import (
    TestCase,
    TestCaseCategory,
    TestCaseEmailSettings,
    TestCasePlan,
    TestCaseStatus,
    TestCaseText,
    _listen,
)
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestRun
from tests import BaseCaseRun, BaseDataContext, BasePlanCase
from tests import factories as f


class TestCaseRemoveIssue(BasePlanCase):
    """Test TestCase.remove_ssue"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.build = f.TestBuildFactory(product=cls.product)
        cls.test_run = f.TestRunFactory(
            product_version=cls.version,
            plan=cls.plan,
            manager=cls.tester,
            default_tester=cls.tester,
        )
        cls.case_run = f.TestCaseRunFactory(
            assignee=cls.tester,
            tested_by=cls.tester,
            case=cls.case,
            run=cls.test_run,
            build=cls.build,
        )
        cls.bz_tracker = f.IssueTrackerFactory(name="TestBZ")

    def setUp(self):
        self.issue_key_1 = "12345678"
        self.case.add_issue(
            self.issue_key_1, self.bz_tracker, summary="error when add a bug to a case"
        )
        self.issue_key_2 = "10000"
        self.case.add_issue(self.issue_key_2, self.bz_tracker, case_run=self.case_run)

    def tearDown(self):
        self.case.issues.all().delete()

    def test_remove_case_issue(self):
        self.case.remove_issue(self.issue_key_1)

        bug_found = self.case.issues.filter(issue_key=self.issue_key_1).exists()
        self.assertFalse(bug_found)

        bug_found = self.case.issues.filter(issue_key=self.issue_key_2).exists()
        self.assertTrue(
            bug_found,
            "Issue key {} does not exist. It should not be deleted.".format(self.issue_key_2),
        )

    def test_case_issue_not_removed_by_passing_case_run(self):
        self.case.remove_issue(self.issue_key_1, case_run=self.case_run.pk)
        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_1).exists())
        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_2).exists())

    def test_remove_case_run_issue(self):
        self.case.remove_issue(self.issue_key_2, case_run=self.case_run.pk)

        self.assertFalse(self.case.issues.filter(issue_key=self.issue_key_2).exists())
        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_1).exists())

    def test_case_run_issue_not_removed_by_missing_case_run(self):
        self.case.remove_issue(self.issue_key_2)

        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_1).exists())
        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_2).exists())


class TestCaseRemoveComponent(BasePlanCase):
    """Test TestCase.remove_component"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.component_1 = f.ComponentFactory(
            name="Application",
            product=cls.product,
            initial_owner=cls.tester,
            initial_qa_contact=cls.tester,
        )
        cls.component_2 = f.ComponentFactory(
            name="Database",
            product=cls.product,
            initial_owner=cls.tester,
            initial_qa_contact=cls.tester,
        )

        cls.cc_rel_1 = f.TestCaseComponentFactory(case=cls.case, component=cls.component_1)
        cls.cc_rel_2 = f.TestCaseComponentFactory(case=cls.case, component=cls.component_2)

    def test_remove_a_component(self):
        self.case.remove_component(self.component_1)

        found = self.case.component.filter(pk=self.component_1.pk).exists()
        self.assertFalse(
            found,
            "Component {} exists. But, it should be removed.".format(self.component_1.pk),
        )
        found = self.case.component.filter(pk=self.component_2.pk).exists()
        self.assertTrue(
            found,
            "Component {} does not exist. It should not be removed.".format(self.component_2.pk),
        )


class TestCaseRemovePlan(BasePlanCase):
    """Test TestCase.remove_plan"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.new_case = f.TestCaseFactory(
            author=cls.tester, default_tester=None, reviewer=cls.tester, plan=[cls.plan]
        )

    def test_remove_plan(self):
        self.new_case.remove_plan(self.plan)

        found = self.plan.case.filter(pk=self.new_case.pk).exists()
        self.assertFalse(found)


class TestCaseRemoveTag(BasePlanCase):
    """Test TestCase.remove_tag"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tag_rhel = f.TestTagFactory(name="rhel")
        cls.tag_fedora = f.TestTagFactory(name="fedora")
        f.TestCaseTagFactory(case=cls.case, tag=cls.tag_rhel, user=cls.tester.pk)
        f.TestCaseTagFactory(case=cls.case, tag=cls.tag_fedora, user=cls.tester.pk)

    def test_remove_tag(self):
        self.case.remove_tag(self.tag_rhel)

        tag_pks = list(self.case.tag.all().values_list("pk", flat=True))
        self.assertEqual([self.tag_fedora.pk], tag_pks)


class TestGetPlainText(BasePlanCase):
    """Test TestCaseText.get_plain_text"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.action = "<p>First step:</p>"
        cls.effect = """<ul>
    <li>effect 1</li>
    <li>effect 2</li>
</ul>"""
        cls.setup = '<p><a href="/setup_guide">setup</a></p>'
        cls.breakdown = "<span>breakdown</span>"

        cls.text_author = User.objects.create_user(username="author", email="my@example.com")
        TestCaseText.objects.create(
            case=cls.case,
            case_text_version=1,
            author=cls.text_author,
            action=cls.action,
            effect=cls.effect,
            setup=cls.setup,
            breakdown=cls.breakdown,
            action_checksum=checksum(cls.action),
            effect_checksum=checksum(cls.effect),
            setup_checksum=checksum(cls.setup),
            breakdown_checksum=checksum(cls.breakdown),
        )

    def test_get_plain_text(self):
        case_text = TestCaseText.objects.all()[0]
        plain_text = case_text.get_plain_text()

        # These expected values were converted from html2text.
        self.assertEqual("First step:", plain_text.action)
        self.assertEqual("  * effect 1\n  * effect 2", plain_text.effect)
        self.assertEqual("[setup](/setup_guide)", plain_text.setup)
        self.assertEqual("breakdown", plain_text.breakdown)


class TestSendMailOnCaseIsUpdated(BasePlanCase):
    """Test send mail on case post_save signal is triggered"""

    def setUp(self):
        super().setUp()
        _listen()

    def tearDown(self):
        post_save.disconnect(case_watchers.on_case_save, TestCase)
        post_delete.disconnect(case_watchers.on_case_delete, TestCase)
        pre_save.disconnect(case_watchers.pre_save_clean, TestCase)
        super().tearDown()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.case.add_text("action", "effect", "setup", "breakdown")

        cls.email_setting = f.TestCaseEmailSettingsFactory(
            case=cls.case, notify_on_case_update=True, auto_to_case_author=True
        )

        cls.case_editor = User.objects.create_user(username="editor")
        # This is actually done when update a case. Setting current_user
        # explicitly here aims to mock that behavior.
        cls.case.current_user = cls.case_editor

    def test_send_mail_to_case_author(self):
        self.case.summary = "New summary for running test"
        self.case.save()

        full_url = self.case.get_full_url()
        expected_mail_body = dedent(
            f"""\
            TestCase [{self.case.summary}] has been updated by editor

            Case -
            {full_url}?#log

            --
            Configure mail: {full_url}/edit/
            ------- You are receiving this mail because: -------
            You have subscribed to the changes of this TestCase
            You are related to this TestCase"""
        )

        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(expected_mail_body, mail.outbox[0].body)
        self.assertEqual([self.case.author.email], mail.outbox[0].to)


class TestCreate(BasePlanCase):
    """Test TestCase.create"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tag_fedora = f.TestTagFactory(name="fedora")
        cls.tag_python = f.TestTagFactory(name="python")

        cls.component_db = f.ComponentFactory(name="db", product=cls.product)
        cls.component_web = f.ComponentFactory(name="web", product=cls.product)

    def test_create(self):
        values = {
            "summary": f"Test new case: {self.__class__.__name__}",
            "is_automated": True,
            "is_automated_proposed": True,
            "script": "",
            "arguments": "",
            "extra_link": "https://localhost/case-2",
            "requirement": "",
            "alias": "alias",
            "estimated_time": 0,
            "case_status": TestCaseStatus.objects.get(name="CONFIRMED"),
            "category": TestCaseCategory.objects.all()[0],
            "priority": Priority.objects.all()[0],
            "default_tester": self.tester,
            "notes": "",
            "tag": [self.tag_fedora, self.tag_python],
            "component": [self.component_db, self.component_web],
        }
        TestCase.create(self.tester, values=values, plans=[self.plan])

        new_case = TestCase.objects.get(summary=values["summary"])

        expected = values.copy()
        expected["estimated_time"] = timedelta(0)

        from tests.testcases import assert_new_case

        assert_new_case(new_case, expected)

        self.assertTrue(TestCasePlan.objects.filter(plan=self.plan, case=new_case).exists())


class TestUpdateTags(test.TestCase):
    """Test TestCase.update_tags"""

    @classmethod
    def setUpTestData(cls):
        cls.tag_fedora = f.TestTagFactory(name="fedora")
        cls.tag_python = f.TestTagFactory(name="python")
        cls.tag_perl = f.TestTagFactory(name="perl")
        cls.tag_cpp = f.TestTagFactory(name="C++")
        cls.case = f.TestCaseFactory(tag=[cls.tag_fedora, cls.tag_python])

    def test_add_and_remove_tags(self):
        # Tag fedora is removed.
        self.case.update_tags([self.tag_python, self.tag_perl, self.tag_cpp])
        self.assertEqual({self.tag_python, self.tag_perl, self.tag_cpp}, set(self.case.tag.all()))


class TestAddIssue(BaseCaseRun):
    """Test TestCase.add_issue"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.issue_tracker = f.IssueTrackerFactory()
        cls.issue_tracker_1 = f.IssueTrackerFactory()

    def test_case_run_is_not_associated_with_case(self):
        # self.case_run_6 is not associated with self.case
        self.assertRaisesRegex(
            ValueError,
            r"Case run .+ is not associated with",
            self.case.add_issue,
            issue_key="123456",
            issue_tracker=self.issue_tracker,
            case_run=self.case_run_6,
        )

    def test_issue_already_exists(self):
        issue_key = "234567"
        self.case_1.add_issue(issue_key=issue_key, issue_tracker=self.issue_tracker)

        existing_issue = Issue.objects.get(issue_key=issue_key, tracker=self.issue_tracker)

        # Add same issue key to same issue tracker againe, no new issue should
        # be added.
        issue = self.case_1.add_issue(issue_key=issue_key, issue_tracker=self.issue_tracker)

        self.assertEqual(existing_issue, issue)

    def test_add_issue_key_to_different_issue_tracker(self):
        issue_key = "456789"
        self.case_1.add_issue(issue_key=issue_key, issue_tracker=self.issue_tracker)
        self.case_1.add_issue(issue_key=issue_key, issue_tracker=self.issue_tracker_1)

        self.assertTrue(
            Issue.objects.filter(issue_key=issue_key, tracker=self.issue_tracker).exists()
        )

        self.assertTrue(
            Issue.objects.filter(issue_key=issue_key, tracker=self.issue_tracker_1).exists()
        )

    def test_add_issue_to_case(self):
        issue_key = "123890"
        issue = self.case_1.add_issue(issue_key=issue_key, issue_tracker=self.issue_tracker)
        added_issue = Issue.objects.get(issue_key=issue_key, tracker=self.issue_tracker)
        self.assertEqual(added_issue, issue)

    def test_add_issue_to_case_run(self):
        issue_key = "223890"
        issue = self.case_1.add_issue(
            issue_key=issue_key,
            issue_tracker=self.issue_tracker,
            case_run=self.case_run_1,
        )
        added_issue = Issue.objects.get(
            issue_key=issue_key, tracker=self.issue_tracker, case_run=self.case_run_1
        )
        self.assertEqual(added_issue, issue)

    @patch("tcms.testcases.models.find_service")
    def test_link_external_tracker(self, find_service):
        tracker_service = find_service.return_value
        issue_key = "243891"
        self.case_1.add_issue(
            issue_key=issue_key,
            issue_tracker=self.issue_tracker,
            case_run=self.case_run_1,
            link_external_tracker=True,
        )
        tracker_service.add_external_tracker.assert_called_once_with(issue_key)

    def test_issue_must_be_validated_before_add(self):
        self.assertValidationError(
            "issue_key",
            r"Issue key PROJ-1 is in wrong format",
            self.case_1.add_issue,
            issue_key="PROJ-1",
            issue_tracker=self.issue_tracker,
        )


class TestGetPreviousAndNext(BasePlanCase):
    """Test TestCase.get_previous_and_next"""

    def test_get_the_case(self):
        test_data = (
            ((self.case.pk, self.case_3.pk, self.case_6.pk), (self.case, self.case_6)),
            (
                (self.case_3.pk, self.case_2.pk, self.case_5.pk),
                (self.case_5, self.case_2),
            ),
            (
                (self.case_4.pk, self.case_6.pk, self.case_3.pk),
                (self.case_6, self.case_4),
            ),
            ((self.case_6.pk, self.case_2.pk, self.case_1.pk), (None, None)),
        )

        test_target = self.case_3

        for example_input, expected_output in test_data:
            output = test_target.get_previous_and_next(example_input)
            self.assertTupleEqual(expected_output, output)


class TestAddTextToCase(test.TestCase):
    """Test TestCase.add_text"""

    @classmethod
    def setUpTestData(cls):
        cls.case = f.TestCaseFactory()
        cls.tester = f.UserFactory(username="zhangsan", email="zhangsan@cool")

    def test_add_new_text(self):
        args = [
            {
                "action": "action",
                "effect": "effect",
                "setup": "setup",
                "breakdown": "breakdown",
            },
            {
                "action": "action 1",
                "effect": "effect 1",
                "setup": "setup 1",
                "breakdown": "breakdown 1",
            },
            {
                "action": "action 1",
                "effect": "effect 1",
                "setup": "setup 1",
                "breakdown": "break into several steps",
            },
            {
                "action": "take some action",
                "effect": "expected result",
                "setup": "setup environemnt",
                "breakdown": "break into several steps",
                "action_checksum": checksum("take some action"),
                "effect_checksum": checksum("expected result"),
            },
            {
                "action": "action 1",
                "effect": "effect 1",
                "setup": "setup 1",
                "breakdown": "breakdown 1",
                "action_checksum": checksum("action 1"),
                "effect_checksum": checksum("effect 1"),
                "setup_checksum": checksum("setup 1"),
                "breakdown_checksum": checksum("breakdown 1"),
            },
        ]

        for expected_text_version, kwargs in enumerate(args, 1):
            self.case.add_text(**kwargs)

            new_text = self.case.text.order_by("pk").last()

            self.assertEqual(expected_text_version, new_text.case_text_version)
            self.assertEqual(kwargs["action"], new_text.action)
            self.assertEqual(kwargs["effect"], new_text.effect)
            self.assertEqual(kwargs["setup"], new_text.setup)
            self.assertEqual(kwargs["breakdown"], new_text.breakdown)

            self.assertEqual(checksum(kwargs["action"]), new_text.action_checksum)
            self.assertEqual(checksum(kwargs["effect"]), new_text.effect_checksum)
            self.assertEqual(checksum(kwargs["setup"]), new_text.setup_checksum)
            self.assertEqual(checksum(kwargs["breakdown"]), new_text.breakdown_checksum)

    def test_do_not_add_if_all_checksum_are_same(self):
        action_checksum = checksum("action")
        effect_checksum = checksum("effect")
        setup_checksum = checksum("setup")
        breakdown_checksum = checksum("breakdown")

        args = [
            {
                "action": "action",
                "effect": "effect",
                "setup": "setup",
                "breakdown": "breakdown",
            },
            {
                "action": "action",
                "effect": "effect",
                "setup": "setup",
                "breakdown": "breakdown",
                "action_checksum": action_checksum,
                "setup_checksum": setup_checksum,
            },
            {
                "action": "action",
                "effect": "effect",
                "setup": "setup",
                "breakdown": "breakdown",
                "action_checksum": action_checksum,
                "effect_checksum": effect_checksum,
                "setup_checksum": setup_checksum,
                "breakdown_checksum": breakdown_checksum,
            },
        ]

        text = self.case.add_text(**args[0])

        for kwargs in args:
            new_text = self.case.add_text(**kwargs)

            self.assertEqual(text.case_text_version, new_text.case_text_version)
            self.assertEqual(text.action, new_text.action)
            self.assertEqual(text.effect, new_text.effect)
            self.assertEqual(text.setup, new_text.setup)
            self.assertEqual(text.breakdown, new_text.breakdown)

            self.assertEqual(action_checksum, new_text.action_checksum)
            self.assertEqual(effect_checksum, new_text.effect_checksum)
            self.assertEqual(setup_checksum, new_text.setup_checksum)
            self.assertEqual(breakdown_checksum, new_text.breakdown_checksum)

    def test_set_author_correctly(self):
        text = self.case.add_text(
            action="action",
            effect="effect",
            setup="setup",
            breakdown="breakdown",
            author=self.tester,
        )
        self.assertEqual(self.tester, text.author)

    def test_use_case_author_if_text_author_is_not_specified(self):
        text = self.case.add_text(
            action="action", effect="effect", setup="setup", breakdown="breakdown"
        )
        self.assertEqual(self.case.author, text.author)


class TestGetLatestTextVersion(test.TestCase):
    """Test TestCase.latest_text_version"""

    @classmethod
    def setUpTestData(cls):
        cls.case = f.TestCaseFactory(summary="Test with no text")

        cls.case_1 = f.TestCaseFactory(summary="Test with text added")
        cls.case_1.add_text(action="action", effect="effect", setup="setup", breakdown="breakdown")
        cls.text = cls.case_1.add_text(
            action="another action",
            effect="effect",
            setup="setup",
            breakdown="breakdown",
        )
        cls.text.case_text_version = 3
        cls.text.save()

    def test_get_when_no_text_is_added(self):
        self.assertEqual(0, self.case.latest_text_version())

    def test_get_the_version(self):
        self.assertEqual(self.text.case_text_version, self.case_1.latest_text_version())


class TestListCases(BasePlanCase):
    """Test TestCase.list"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.bz_tracker = cls.create_bz_tracker()

        cls.case_author = f.UserFactory(username="case-author")
        cls.default_tester = f.UserFactory(username="default-tester")

        cls.case_1.summary = "Test list case"
        cls.case_1.is_automated = 1
        cls.case_1.is_automated_proposed = True
        cls.case_1.author = cls.case_author
        cls.case_1.default_tester = cls.default_tester
        cls.case_1.category = f.TestCaseCategoryFactory(name="functional", product=cls.product)
        cls.case_1.priority = Priority.objects.get(value="P3")
        cls.case_1.case_status = TestCaseStatus.objects.first()
        cls.case_1.save()

        cls.case_1.add_issue("2000", cls.bz_tracker)
        cls.case_1.add_issue("2001", cls.bz_tracker)

        f.TestCaseComponentFactory(case=cls.case_1, component=f.ComponentFactory(name="db"))
        f.TestCaseComponentFactory(case=cls.case_1, component=f.ComponentFactory(name="web"))

        f.TestCaseTagFactory(case=cls.case_1, tag=f.TestTagFactory(name="python"))
        f.TestCaseTagFactory(case=cls.case_1, tag=f.TestTagFactory(name="fedora"))

    def test_simple_list_by_property(self):
        criteria = [
            {"summary": "list case"},
            {"author": self.case_1.author.username},
            {"author": self.case_1.author.email},
            {"default_tester": self.case_1.default_tester.username},
            {"default_tester": self.case_1.default_tester.email},
            {"tag__name__in": ["python"]},
            {"category": TestCaseCategory.objects.get(name="functional")},
            {"priority": [Priority.objects.get(value="P3")]},
            {"case_status": [TestCaseStatus.objects.first()]},
            {"component": Component.objects.get(name="db")},
            {"is_automated": 1},
            {"is_automated_proposed": True},
            {"product": self.product.pk},
            {"issue_key": ["2000", "1000"]},
        ]

        for item in criteria:
            cases = TestCase.list(item)
            self.assertEqual([self.case_1], list(cases))

    def test_list_a_set_of_cases(self):
        cases = TestCase.list({"case_id_set": [self.case_2.pk, self.case_5.pk]})
        self.assertEqual([self.case_2, self.case_5], list(cases))

    def test_list_by_plan(self):
        cases = TestCase.list({"product": self.product.pk}, plan=self.plan).order_by("pk")
        self.assertEqual([self.case_1], list(cases))

    def test_list_by_search_keyword(self):
        criteria = [
            {"search": "Test list"},
            {"search": self.case_author.email.split("@")[0]},
        ]

        for item in criteria:
            cases = TestCase.list(item)
            self.assertEqual([self.case_1], list(cases))

    def test_list_by_multiple_criteria(self):
        cases = TestCase.list(
            {
                "category": TestCaseCategory.objects.get(name="functional"),
                "issue_key": ["2000"],
            }
        )
        self.assertEqual([self.case_1], list(cases))

    def test_get_empty_result(self):
        result = Product.objects.aggregate(max_pk=Max("pk"))
        unknown_pk = result["max_pk"] + 1
        self.assertListEqual([], list(TestCase.list({"product": unknown_pk})))


class TestUpdateCases(BasePlanCase):
    """Test TestCase.update"""

    def test_update(self):
        TestCase.update(
            self.case_1.pk,
            {
                "category": f.TestCaseCategoryFactory(name="functional", product=self.product),
                "is_automated": 1,
                "notes": "",
                "script": "",
            },
        )

        case = TestCase.objects.get(pk=self.case_1.pk)

        category = TestCaseCategory.objects.get(name="functional", product=self.product)

        self.assertEqual(category, case.category)
        self.assertEqual(1, case.is_automated)
        self.assertEqual("", case.notes)
        self.assertEqual("", case.script)


class TestTextExist(test.TestCase):
    """Test TestCase.text_exist"""

    @classmethod
    def setUpTestData(cls):
        cls.case_1 = f.TestCaseFactory(summary="case 2")
        cls.case_1.add_text(action="action", effect="effect", setup="setup", breakdown="breakdown")
        cls.case_1.add_text(
            action="action 1",
            effect="effect 1",
            setup="setup 1",
            breakdown="breakdown 1",
        )
        cls.case_1.add_text(
            action="action 2",
            effect="effect 2",
            setup="setup 2",
            breakdown="breakdown 2",
        )
        cls.case_2 = f.TestCaseFactory(summary="case 2")

    def test_text_exists(self):
        self.assertTrue(self.case_1.text_exist())

    def test_text_not_exist(self):
        self.assertFalse(self.case_2.text_exist())


class TestDeleteCase(test.TestCase):
    """
    Test a or a set of test cases can be deleted correctly with email settings
    set
    """

    @classmethod
    def setUpTestData(cls):
        cls.case_1 = f.TestCaseFactory()
        cls.case_1.emailing
        cls.plan = f.TestPlanFactory()
        cls.case_2 = f.TestCaseFactory(plan=[cls.plan])
        cls.case_2.emailing
        cls.case_3 = f.TestCaseFactory(plan=[cls.plan])
        cls.case_3.emailing

    def test_delete_a_case(self):
        """Test delete a case by Model.delete()"""

        self.case_1.delete()
        self.assertFalse(TestCase.objects.filter(pk=self.case_1.pk).exists())
        self.assertFalse(TestCaseEmailSettings.objects.filter(pk=self.case_1.emailing.pk).exists())

    def test_delete_a_set_of_cases(self):
        """Test delete a case by QuerySet.delete()"""

        TestCase.objects.filter(plan__in=[self.plan.pk]).delete()

        self.assertFalse(TestCase.objects.filter(pk=self.case_2.pk).exists())
        self.assertFalse(TestCaseEmailSettings.objects.filter(pk=self.case_2.emailing.pk).exists())

        self.assertFalse(TestCase.objects.filter(pk=self.case_3.pk).exists())
        self.assertFalse(TestCaseEmailSettings.objects.filter(pk=self.case_3.emailing.pk).exists())


@pytest.mark.parametrize("auto_to_case_author", [True, False])
@pytest.mark.parametrize("auto_to_case_tester", [True, False])
@pytest.mark.parametrize("auto_to_run_manager", [True, False])
@pytest.mark.parametrize("auto_to_run_tester", [True, False])
@pytest.mark.parametrize("auto_to_case_run_assignee", [True, False])
def test_case_get_notification_recipients(
    auto_to_case_author: bool,
    auto_to_case_tester: bool,
    auto_to_run_manager: bool,
    auto_to_run_tester: bool,
    auto_to_case_run_assignee: bool,
    base_data: BaseDataContext,
):
    user_1: User = User.objects.create_user(username="user1", email="user1@example.com")
    plan: TestPlan = base_data.plan_creator(pk=1, name="plan 1")
    case_1: TestCase = base_data.case_creator(pk=1, summary="case 1", default_tester=user_1)
    plan.add_case(case_1)

    manager: User = User.objects.create_user(username="manager1", email="manager1@example.com")
    run_tester: User = User.objects.create_user(
        username="run_tester", email="run_tester@example.com"
    )
    run_1: TestRun = base_data.run_creator(
        pk=1, summary="run 1", plan=plan, manager=manager, default_tester=run_tester
    )
    run_1.add_case_run(case_1, assignee=run_tester)

    emailing = case_1.emailing
    emailing.auto_to_case_author = auto_to_case_author
    emailing.auto_to_case_tester = auto_to_case_tester
    emailing.auto_to_run_manager = auto_to_run_manager
    emailing.auto_to_run_tester = auto_to_run_tester
    emailing.auto_to_case_run_assignee = auto_to_case_run_assignee

    recipients = case_1.get_notification_recipients()

    if auto_to_case_author:
        assert case_1.author.email in recipients
    if auto_to_case_tester:
        if case_1.default_tester:
            assert case_1.default_tester.email in recipients
        else:
            assert case_1.default_tester.email not in recipients
    if auto_to_run_manager:
        assert run_1.manager.email in recipients
    if auto_to_run_tester or auto_to_case_run_assignee:
        assert 1 == recipients.count(run_tester.email)
        assert run_tester.email in recipients

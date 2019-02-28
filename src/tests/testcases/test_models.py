# -*- coding: utf-8 -*-

from __future__ import absolute_import

import six

from mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.db.models.signals import post_save, post_delete, pre_save
from django import test

from tcms.core.utils.checksum import checksum
from tcms.issuetracker.models import Issue
from tcms.management.models import Priority
from tcms.testcases import signals as case_watchers
from tcms.testcases.models import _listen
from tcms.testcases.models import TestCase
from tcms.testcases.models import TestCaseCategory
from tcms.testcases.models import TestCaseStatus
from tcms.testcases.models import TestCaseText
from tests.factories import ComponentFactory
from tests.factories import IssueTrackerFactory
from tests.factories import TestBuildFactory
from tests.factories import TestCaseComponentFactory
from tests.factories import TestCaseEmailSettingsFactory
from tests.factories import TestCaseFactory
from tests.factories import TestCaseRunFactory
from tests.factories import TestCaseTagFactory
from tests.factories import TestRunFactory
from tests.factories import TestTagFactory
from tests import BaseCaseRun
from tests import BasePlanCase


class TestCaseRemoveIssue(BasePlanCase):
    """Test TestCase.remove_ssue"""

    @classmethod
    def setUpTestData(cls):
        super(TestCaseRemoveIssue, cls).setUpTestData()
        cls.build = TestBuildFactory(product=cls.product)
        cls.test_run = TestRunFactory(product_version=cls.version,
                                      plan=cls.plan,
                                      manager=cls.tester,
                                      default_tester=cls.tester)
        cls.case_run = TestCaseRunFactory(assignee=cls.tester,
                                          tested_by=cls.tester,
                                          case=cls.case,
                                          run=cls.test_run,
                                          build=cls.build)
        cls.bz_tracker = IssueTrackerFactory(name='TestBZ')

    def setUp(self):
        self.issue_key_1 = '12345678'
        self.case.add_issue(self.issue_key_1, self.bz_tracker,
                            summary='error when add a bug to a case')
        self.issue_key_2 = '10000'
        self.case.add_issue(self.issue_key_2, self.bz_tracker,
                            case_run=self.case_run)

    def tearDown(self):
        self.case.issues.all().delete()

    def test_remove_case_issue(self):
        self.case.remove_issue(self.issue_key_1)

        bug_found = self.case.issues.filter(
            issue_key=self.issue_key_1).exists()
        self.assertFalse(bug_found)

        bug_found = self.case.issues.filter(
            issue_key=self.issue_key_2).exists()
        self.assertTrue(
            bug_found,
            'Issue key {} does not exist. It should not be deleted.'
            .format(self.issue_key_2))

    def test_case_issue_not_removed_by_passing_case_run(self):
        self.case.remove_issue(self.issue_key_1, case_run=self.case_run.pk)
        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_1)
                                        .exists())
        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_2)
                                        .exists())

    def test_remove_case_run_issue(self):
        self.case.remove_issue(self.issue_key_2, case_run=self.case_run.pk)

        self.assertFalse(self.case.issues.filter(issue_key=self.issue_key_2)
                                         .exists())
        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_1)
                                        .exists())

    def test_case_run_issue_not_removed_by_missing_case_run(self):
        self.case.remove_issue(self.issue_key_2)

        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_1)
                                        .exists())
        self.assertTrue(self.case.issues.filter(issue_key=self.issue_key_2)
                                        .exists())


class TestCaseRemoveComponent(BasePlanCase):
    """Test TestCase.remove_component"""

    @classmethod
    def setUpTestData(cls):
        super(TestCaseRemoveComponent, cls).setUpTestData()

        cls.component_1 = ComponentFactory(name='Application',
                                           product=cls.product,
                                           initial_owner=cls.tester,
                                           initial_qa_contact=cls.tester)
        cls.component_2 = ComponentFactory(name='Database',
                                           product=cls.product,
                                           initial_owner=cls.tester,
                                           initial_qa_contact=cls.tester)

        cls.cc_rel_1 = TestCaseComponentFactory(case=cls.case,
                                                component=cls.component_1)
        cls.cc_rel_2 = TestCaseComponentFactory(case=cls.case,
                                                component=cls.component_2)

    def test_remove_a_component(self):
        self.case.remove_component(self.component_1)

        found = self.case.component.filter(pk=self.component_1.pk).exists()
        self.assertFalse(
            found,
            'Component {} exists. But, it should be removed.'.format(
                self.component_1.pk))
        found = self.case.component.filter(pk=self.component_2.pk).exists()
        self.assertTrue(
            found,
            'Component {} does not exist. It should not be removed.'.format(
                self.component_2.pk))


class TestCaseRemovePlan(BasePlanCase):
    """Test TestCase.remove_plan"""

    @classmethod
    def setUpTestData(cls):
        super(TestCaseRemovePlan, cls).setUpTestData()

        cls.new_case = TestCaseFactory(author=cls.tester, default_tester=None, reviewer=cls.tester,
                                       plan=[cls.plan])

    def test_remove_plan(self):
        self.new_case.remove_plan(self.plan)

        found = self.plan.case.filter(pk=self.new_case.pk).exists()
        self.assertFalse(
            found, 'Case {0} should has no relationship to plan {0} now.'.format(self.new_case.pk,
                                                                                 self.plan.pk))


class TestCaseRemoveTag(BasePlanCase):
    """Test TestCase.remove_tag"""

    @classmethod
    def setUpTestData(cls):
        super(TestCaseRemoveTag, cls).setUpTestData()

        cls.tag_rhel = TestTagFactory(name='rhel')
        cls.tag_fedora = TestTagFactory(name='fedora')
        TestCaseTagFactory(case=cls.case, tag=cls.tag_rhel, user=cls.tester.pk)
        TestCaseTagFactory(case=cls.case, tag=cls.tag_fedora, user=cls.tester.pk)

    def test_remove_tag(self):
        self.case.remove_tag(self.tag_rhel)

        tag_pks = list(self.case.tag.all().values_list('pk', flat=True))
        self.assertEqual([self.tag_fedora.pk], tag_pks)


class TestGetPlainText(BasePlanCase):
    """Test TestCaseText.get_plain_text"""

    @classmethod
    def setUpTestData(cls):
        super(TestGetPlainText, cls).setUpTestData()

        cls.action = '<p>First step:</p>'
        cls.effect = '''<ul>
    <li>effect 1</li>
    <li>effect 2</li>
</ul>'''
        cls.setup = '<p><a href="/setup_guide">setup</a></p>'
        cls.breakdown = '<span>breakdown</span>'

        cls.text_author = User.objects.create_user(username='author',
                                                   email='my@example.com')
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
            breakdown_checksum=checksum(cls.breakdown))

    def test_get_plain_text(self):
        case_text = TestCaseText.objects.all()[0]
        plain_text = case_text.get_plain_text()

        # These expected values were converted from html2text.
        self.assertEqual('First step:', plain_text.action)
        self.assertEqual('  * effect 1\n  * effect 2', plain_text.effect)
        self.assertEqual('[setup](/setup_guide)', plain_text.setup)
        self.assertEqual('breakdown', plain_text.breakdown)


class TestSendMailOnCaseIsUpdated(BasePlanCase):
    """Test send mail on case post_save signal is triggered"""

    def setUp(self):
        super(TestSendMailOnCaseIsUpdated, self).setUp()
        _listen()

    def tearDown(self):
        post_save.disconnect(case_watchers.on_case_save, TestCase)
        post_delete.disconnect(case_watchers.on_case_delete, TestCase)
        pre_save.disconnect(case_watchers.pre_save_clean, TestCase)
        super(TestSendMailOnCaseIsUpdated, self).tearDown()

    @classmethod
    def setUpTestData(cls):
        super(TestSendMailOnCaseIsUpdated, cls).setUpTestData()

        cls.case.add_text('action', 'effect', 'setup', 'breakdown')

        cls.email_setting = TestCaseEmailSettingsFactory(
            case=cls.case,
            notify_on_case_update=True,
            auto_to_case_author=True)

        cls.case_editor = User.objects.create_user(username='editor')
        # This is actually done when update a case. Setting current_user
        # explicitly here aims to mock that behavior.
        cls.case.current_user = cls.case_editor

    def test_send_mail_to_case_author(self):
        self.case.summary = 'New summary for running test'
        self.case.save()

        expected_mail_body = '''TestCase [{0}] has been updated by {1}

Case -
{2}?#log

--
Configure mail: {2}/edit/
------- You are receiving this mail because: -------
You have subscribed to the changes of this TestCase
You are related to this TestCase'''.format(self.case.summary,
                                           'editor',
                                           self.case.get_full_url())

        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(expected_mail_body, mail.outbox[0].body)
        self.assertEqual([self.case.author.email], mail.outbox[0].to)


class TestCreate(BasePlanCase):
    """Test TestCase.create"""

    @classmethod
    def setUpTestData(cls):
        super(TestCreate, cls).setUpTestData()
        cls.tag_fedora = TestTagFactory(name='fedora')
        cls.tag_python = TestTagFactory(name='python')

    def test_create(self):
        values = {
            'summary': 'Test new case: {}'.format(self.__class__.__name__),
            'is_automated': True,
            'is_automated_proposed': True,
            'script': '',
            'arguments': '',
            'extra_link': 'https://localhost/case-2',
            'requirement': '',
            'alias': 'alias',
            'estimated_time': 0,
            'case_status': TestCaseStatus.objects.get(name='CONFIRMED'),
            'category': TestCaseCategory.objects.all()[0],
            'priority': Priority.objects.all()[0],
            'default_tester': self.tester,
            'notes': '',
            'tag': [self.tag_fedora, self.tag_python]
        }
        case = TestCase.create(self.tester, values=values)

        new_case = TestCase.objects.get(summary=values['summary'])

        self.assertEqual(case, new_case)
        self.assertEqual(values['case_status'], new_case.case_status)
        self.assertEqual(set(values['tag']), set(new_case.tag.all()))


class TestUpdateTags(test.TestCase):
    """Test TestCase.update_tags"""

    @classmethod
    def setUpTestData(cls):
        cls.tag_fedora = TestTagFactory(name='fedora')
        cls.tag_python = TestTagFactory(name='python')
        cls.tag_perl = TestTagFactory(name='perl')
        cls.tag_cpp = TestTagFactory(name='C++')
        cls.case = TestCaseFactory(tag=[cls.tag_fedora, cls.tag_python])

    def test_add_and_remove_tags(self):
        # Tag fedora is removed.
        self.case.update_tags([self.tag_python, self.tag_perl, self.tag_cpp])
        self.assertEqual({self.tag_python, self.tag_perl, self.tag_cpp},
                         set(self.case.tag.all()))


class TestAddIssue(BaseCaseRun):
    """Test TestCase.add_issue"""

    @classmethod
    def setUpTestData(cls):
        super(TestAddIssue, cls).setUpTestData()
        cls.issue_tracker = IssueTrackerFactory()
        cls.issue_tracker_1 = IssueTrackerFactory()

    def test_case_run_is_not_associated_with_case(self):
        # self.case_run_6 is not associated with self.case
        six.assertRaisesRegex(
            self, ValueError, r'Case run .+ is not associated with',
            self.case.add_issue,
            issue_key='123456',
            issue_tracker=self.issue_tracker,
            case_run=self.case_run_6)

    def test_issue_already_exists(self):
        issue_key = '234567'
        self.case_1.add_issue(issue_key=issue_key,
                              issue_tracker=self.issue_tracker)

        existing_issue = Issue.objects.get(issue_key=issue_key,
                                           tracker=self.issue_tracker)

        # Add same issue key to same issue tracker againe, no new issue should
        # be added.
        issue = self.case_1.add_issue(issue_key=issue_key,
                                      issue_tracker=self.issue_tracker)

        self.assertEqual(existing_issue, issue)

    def test_add_issue_key_to_different_issue_tracker(self):
        issue_key = '456789'
        self.case_1.add_issue(issue_key=issue_key,
                              issue_tracker=self.issue_tracker)
        self.case_1.add_issue(issue_key=issue_key,
                              issue_tracker=self.issue_tracker_1)

        self.assertTrue(
            Issue.objects.filter(
                issue_key=issue_key, tracker=self.issue_tracker
            ).exists())

        self.assertTrue(
            Issue.objects.filter(
                issue_key=issue_key, tracker=self.issue_tracker_1
            ).exists())

    def test_add_issue_to_case(self):
        issue_key = '123890'
        issue = self.case_1.add_issue(issue_key=issue_key,
                                      issue_tracker=self.issue_tracker)
        added_issue = Issue.objects.get(issue_key=issue_key,
                                        tracker=self.issue_tracker)
        self.assertEqual(added_issue, issue)

    def test_add_issue_to_case_run(self):
        issue_key = '223890'
        issue = self.case_1.add_issue(issue_key=issue_key,
                                      issue_tracker=self.issue_tracker,
                                      case_run=self.case_run_1)
        added_issue = Issue.objects.get(issue_key=issue_key,
                                        tracker=self.issue_tracker,
                                        case_run=self.case_run_1)
        self.assertEqual(added_issue, issue)

    @patch('tcms.testcases.models.find_service')
    def test_link_external_tracker(self, find_service):
        tracker_service = find_service.return_value
        issue_key = '243891'
        self.case_1.add_issue(issue_key=issue_key,
                              issue_tracker=self.issue_tracker,
                              case_run=self.case_run_1,
                              link_external_tracker=True)
        tracker_service.add_external_tracker.assert_called_once_with(issue_key)

    def test_issue_must_be_validated_before_add(self):
        self.assertValidationError(
            'issue_key',
            r'Issue key PROJ-1 is in malformat',
            self.case_1.add_issue,
            issue_key='PROJ-1',
            issue_tracker=self.issue_tracker,
        )

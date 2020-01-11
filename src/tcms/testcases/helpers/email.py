# -*- coding: utf-8 -*-

from django.conf import settings

from tcms.core.mailto import mailto


def email_case_update(case):
    notify_recipients(
        case,
        f'TestCase {case.pk} has been updated.',
        {
            'test_case': case,
            'test_case_text': case.latest_text(),
        },
    )


def email_case_deletion(case):
    notify_recipients(
        case,
        f'TestCase {case.pk} has been deleted.',
        {'case': case},
    )


def notify_recipients(case, subject, context):
    recipients = get_case_notification_recipients(case)
    cc = case.emailing.get_cc_list()
    if len(recipients) == 0:
        return
    template = settings.CASE_EMAIL_TEMPLATE
    mailto(template, subject, recipients, context, cc=cc)


def get_case_notification_recipients(case):
    recipients = set()
    if case.emailing.auto_to_case_author:
        recipients.add(case.author.email)
    if case.emailing.auto_to_case_tester and case.default_tester:
        recipients.add(case.default_tester.email)
    if case.emailing.auto_to_run_manager:
        managers = case.case_run.values_list('run__manager__email', flat=True)
        recipients.update(managers)
    if case.emailing.auto_to_run_tester:
        run_testers = case.case_run.values_list('run__default_tester__email',
                                                flat=True)
        recipients.update(run_testers)
    if case.emailing.auto_to_case_run_assignee:
        assignees = case.case_run.values_list('assignee__email', flat=True)
        recipients.update(assignees)
    return list(filter(lambda e: bool(e), recipients))

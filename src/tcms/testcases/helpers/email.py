# -*- coding: utf-8 -*-

import logging

from tcms.core.mailto import mail_notify

logger = logging.getLogger(__name__)


def email_case_update(case):
    mail_notify(
        case,
        "mail/edit_case.txt",
        f"TestCase {case.pk} has been updated.",
        {
            "summary": case.summary,
            "updated_by": case.current_user.username,
            "full_url": case.get_full_url(),
        },
        cc=case.emailing.get_cc_list(),
    )


def email_case_deletion(case):
    mail_notify(
        case,
        "mail/delete_case.txt",
        f"TestCase {case.pk} has been deleted.",
        {"summary": case.summary},
        cc=case.emailing.get_cc_list(),
    )

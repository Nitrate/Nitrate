# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.models.signals import post_save, post_delete

from tcms.testruns.models import TestRun, TestCaseRun
from tcms.integration.errata.signals import testrun_created_handler
from tcms.integration.errata.signals import testrun_progress_handler
from tcms.integration.errata.signals import issue_added_handler
from tcms.integration.errata.signals import issue_removed_handler
from tcms.integration.issuetracker.models import Issue

# Disable producing progress info to consumers (only errata now) by default.
# Set ENABLE_QPID = True in product.py to reopen it.
if settings.ENABLE_QPID:
    # testrun create listen for qpid
    post_save.connect(testrun_created_handler, sender=TestRun)
    # testrun progress listen for qpid
    post_save.connect(
        testrun_progress_handler,
        sender=TestCaseRun,
        dispatch_uid="tcms.testruns.signals.testrun_progress_handler",
    )

    # Issue add/remove listen for qpid
    post_save.connect(issue_added_handler, Issue)
    post_delete.connect(issue_removed_handler, Issue)

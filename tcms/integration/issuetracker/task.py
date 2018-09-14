# -*- coding: utf-8 -*-
import warnings

from six.moves import xmlrpc_client

from celery import shared_task
from django.conf import settings


@shared_task
def bugzilla_external_track(api_url, bug):
    try:
        proxy = xmlrpc_client.ServerProxy(api_url)
        proxy.ExternalBugs.add_external_bug({
            'Bugzilla_login': settings.BUGZILLA_USER,
            'Bugzilla_password': settings.BUGZILLA_PASSWORD,
            'bug_ids': [int(bug.issue_key), ],
            'external_bugs': [{'ext_bz_bug_id': str(bug.case.case_id),
                               'ext_type_description': 'TCMS Test Case'}, ]
        })
    except Exception as err:
        message = '%s: %s' % (err.__class__.__name__, str(err))
        warnings.warn(message)

# -*- coding: utf-8 -*-

import warnings

from celery import shared_task
from six.moves import xmlrpc_client


@shared_task
def bugzilla_external_track(issue_tracker, issue):
    """Link issue to bug external tracker"""
    try:
        cred = issue_tracker.credential
        proxy = xmlrpc_client.ServerProxy(issue_tracker.api_url)
        proxy.ExternalBugs.add_external_bug({
            'Bugzilla_login': cred['username'],
            'Bugzilla_password': cred['password'],
            'bug_ids': [int(issue.issue_key)],
            'external_bugs': [{
                'ext_bz_bug_id': str(issue.case.pk),
                'ext_type_description': 'Nitrate Test Case',
            }]
        })
    except Exception as err:
        message = '%s: %s' % (err.__class__.__name__, str(err))
        warnings.warn(message)

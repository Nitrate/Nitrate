# -*- coding: utf-8 -*-

import warnings

from celery import shared_task
from django.conf import settings
from six.moves import xmlrpc_client


@shared_task
def bugzilla_external_track(api_url, issue):
    """Link issue to bug external tracker"""
    try:
        proxy = xmlrpc_client.ServerProxy(api_url)
        proxy.ExternalBugs.add_external_bug({
            'Bugzilla_login': settings.BUGZILLA_USER,
            'Bugzilla_password': settings.BUGZILLA_PASSWORD,
            'bug_ids': [int(issue.issue_key)],
            'external_bugs': [{
                'ext_bz_bug_id': str(issue.case.pk),
                'ext_type_description': 'Nitrate Test Case',
            }]
        })
    except Exception as err:
        message = '%s: %s' % (err.__class__.__name__, str(err))
        warnings.warn(message)

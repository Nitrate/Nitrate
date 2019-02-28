# -*- coding: utf-8 -*-

import bugzilla
import warnings

from tcms.core.task import Task


@Task
def bugzilla_external_track(issue_tracker, issue):
    """Link issue to bug external tracker"""
    try:
        cred = issue_tracker.credential
        bz = bugzilla.Bugzilla(issue_tracker.api_url,
                               user=cred['username'],
                               password=cred['password'])
        bz.add_external_tracker(
            int(issue.issue_key), issue.case.pk,

            # Note that, this description should be updated if it is changed in
            # remote Bugzilla service.
            ext_type_description='Nitrate Test Case')

    except Exception as err:
        message = '{}: {}'.format(err.__class__.__name__, str(err))
        warnings.warn(message)

# -*- coding: utf-8 -*-

import unittest

from unittest.mock import patch, Mock
from tcms.issuetracker.task import bugzilla_external_track


class TestBugzillaExternalTrack(unittest.TestCase):
    """Test task bugzilla_external_track"""

    @patch('bugzilla.Bugzilla')
    def test_add_external_tracker(self, Bugzilla):
        issue_tracker = Mock(credential={'username': 'a', 'password': 'b'})
        issue = Mock(issue_key='1')
        bugzilla_external_track(issue_tracker, issue)

        bz = Bugzilla.return_value
        bz.add_external_tracker.assert_called_once_with(
            int(issue.issue_key), issue.case.pk,
            ext_type_description='Nitrate Test Case')

    @patch('bugzilla.Bugzilla')
    @patch('warnings.warn')
    def test_warning_when_error_reported(self, warn, Bugzilla):
        Bugzilla.return_value.add_external_tracker.side_effect = ValueError

        issue_tracker = Mock(credential={'username': 'a', 'password': 'b'})
        issue = Mock(issue_key='1')
        bugzilla_external_track(issue_tracker, issue)

        warn.assert_called_once()

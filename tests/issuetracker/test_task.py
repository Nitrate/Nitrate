# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from tcms.issuetracker.task import bugzilla_external_track


class TestBugzillaExternalTrack(unittest.TestCase):
    """Test task bugzilla_external_track"""

    def setUp(self) -> None:
        self.api_url = "http://bz.localhost/"
        self.credential = {"username": "a", "password": "b"}
        self.issue_key = "1"
        self.case_id = 2

    @patch("bugzilla.Bugzilla")
    def test_add_external_tracker(self, Bugzilla):
        bugzilla_external_track(self.api_url, self.credential, self.issue_key, self.case_id)

        bz = Bugzilla.return_value
        bz.add_external_tracker.assert_called_once_with(
            int(self.issue_key), self.case_id, ext_type_description="Nitrate Test Case"
        )

    @patch("bugzilla.Bugzilla")
    @patch("warnings.warn")
    def test_warning_when_error_reported(self, warn, Bugzilla):
        Bugzilla.return_value.add_external_tracker.side_effect = ValueError
        bugzilla_external_track(self.api_url, self.credential, self.issue_key, self.case_id)
        warn.assert_called_once()

# -*- coding: utf-8 -*-

from unittest import TestCase
from unittest.mock import Mock, patch

from tcms.testplans.signals import notify_on_plan_is_updated


class TestSignalNotifyOnPlanIsUpdated(TestCase):
    """Test signal notify_on_plan_is_updated"""

    @patch("tcms.testplans.signals.email")
    def test_not_send_mail(self, email):
        instance = Mock()
        instance.email_settings.notify_on_plan_update = False
        notify_on_plan_is_updated(Mock(), instance)
        email.email_plan_update.assert_not_called()

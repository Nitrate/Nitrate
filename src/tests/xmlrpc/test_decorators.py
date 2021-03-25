# -*- coding: utf-8 -*-

from unittest import TestCase
from unittest.mock import Mock, patch

from tcms.xmlrpc.decorators import log_call


@log_call(namespace="test")
def func(request, name, status, plans=None, tags=None):
    pass


@log_call(namespace="test")
def search(request, values=None):
    pass


@log_call()
def find_something(request, object_id):
    pass


class TestLogCall(TestCase):
    """Test log_call"""

    @patch("tcms.xmlrpc.decorators.create_log")
    def test_call_with_only_args(self, create_log):
        request = Mock()
        func(request, "name1", "idle")

        create_log.assert_called_once_with(
            user=request.user,
            method="test.func",
            args=str([("name", "name1"), ("status", "idle")]),
        )

    @patch("tcms.xmlrpc.decorators.create_log")
    def test_call_with_args_and_kwargs(self, create_log):
        request = Mock()
        func(request, "name1", "idle", tags=["tag1", "tag2"])

        create_log.assert_called_once_with(
            user=request.user,
            method="test.func",
            args=str([("name", "name1"), ("status", "idle"), ("tags", ["tag1", "tag2"])]),
        )

    @patch("tcms.xmlrpc.decorators.create_log")
    def test_call_with_only_kwargs(self, create_log):
        request = Mock()
        search(request, values={"name": "name1", "status": "running"})

        create_log.assert_called_once_with(
            user=request.user,
            method="test.search",
            args=str([("values", {"name": "name1", "status": "running"})]),
        )

    @patch("tcms.xmlrpc.decorators.create_log")
    def test_log_without_namespace(self, create_log):
        request = Mock()
        find_something(request, 100)

        create_log.assert_called_once_with(
            user=request.user, method="find_something", args=str([("object_id", 100)])
        )

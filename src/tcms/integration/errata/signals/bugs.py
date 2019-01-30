# -*- coding: utf-8 -*-


def issue_added_handler(sender, *args, **kwargs):
    # TODO: Send message to message bus when bug is added. Topic: bugs.added
    pass


def issue_removed_handler(sender, *args, **kwargs):
    # TODO: Send message to message bus when bug is removed.
    # Topic: bugs.dropped
    pass

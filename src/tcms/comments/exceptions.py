# -*- coding: utf-8 -*-


class InvalidCommentPostRequest(Exception):
    """Raised if comment is not valid"""

    def __init__(self, target, form):
        self.target = target
        self.form = form

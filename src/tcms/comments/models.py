# -*- coding: utf-8 -*-

import logging

import tcms.comments
from django.core.exceptions import ObjectDoesNotExist
from tcms.comments.views import (
    get_comment_target_object, post_comment, InvalidCommentPostRequest
)

log = logging.getLogger(__name__)


def add_comment(
        request_user, content_type, object_pks, comment, remote_addr=None):
    """Add comment to given target objects

    This function is useful particularly for not add a comment from WebUI by
    clicking a button, and allow to add a comment to more than one model
    objects at once.

    :param request_user: the user object who requests to add this comment.
    :type request_user: :class:`django.contrib.auth.models.User`
    :param str content_type: the content type of the model in format
        ``app_label.model_name``, e.g. ``testcases.testcase``.
    :param object_pks: list of object IDs in order to allow adding a comment to
        more than on models.
    :type object_pks: list[int]
    :param str comment: content of the comment to be added.
    :param remote_addr: remote IP address of the user.
    :type remote_addr: str or None
    :return: list of comments just added.
    :rtype: list[:class:`django_comments.models.Comment`]
    """
    new_comments = []
    comment_form = tcms.comments.get_form()
    for object_pk in object_pks:
        try:
            target = get_comment_target_object(content_type, object_pk)
        except ObjectDoesNotExist:
            log.error('%s object with id %s does not exist in database. '
                      'Ignore it and continue to add comment to next one.',
                      content_type, object_pk)
            continue
        initial_form = comment_form(target)
        comment_data = initial_form.initial.copy()
        comment_data['comment'] = comment
        try:
            _, new_comment = post_comment(
                comment_data, request_user, remote_addr)
        except InvalidCommentPostRequest:
            log.error(
                'Failed to add comment, continue to add comment to next one.')
        else:
            new_comments.append(new_comment)
    return new_comments

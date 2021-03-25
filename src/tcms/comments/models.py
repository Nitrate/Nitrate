# -*- coding: utf-8 -*-

import logging
from typing import List

from django.core.exceptions import ObjectDoesNotExist
from django_comments.models import Comment

import tcms.comments
from tcms.comments.exceptions import InvalidCommentPostRequest
from tcms.core import utils

log = logging.getLogger(__name__)


def get_comment_target_object(content_type: str, object_pk: int):
    """Get corresponding model object

    :param content_type: a string representing the model's content type in
        format ``app_name.model_name``, for example, ``testcases.testcase``.
    :type content_type: str
    :param object_pk: the pk of the object.
    :type object_pk: int
    :return: the model object according to the content type.
    """
    return utils.get_model(content_type)._default_manager.get(pk=object_pk)


def post_comment(comment_data, request_user, remote_addr=None):
    """Save a comment

    This function is a customized version of
    ``django_comments.views.comments.post_comment`` by cutting off part of the
    code that are not necessary for Nitrate, for example, this method does not
    send signal before and after saving comment. A significant change between
    them is this function is not a view function and can be reused to add a
    comment to a given model object.
    """

    if request_user.is_authenticated:
        # Nitrate does not allow user to enter name or email for adding a
        # comment, so when the request is authenticated, use the logged-in
        # user's name and email.
        comment_data["name"] = request_user.get_full_name() or request_user.username
        comment_data["email"] = request_user.email

    ctype = comment_data.get("content_type")
    object_pk = comment_data.get("object_pk")

    target = get_comment_target_object(ctype, int(object_pk))

    form = tcms.comments.get_form()(target, data=comment_data)
    if not form.is_valid():
        log.error("Failed to add comment to %s %s: %r", ctype, object_pk, comment_data)
        log.error("Error messages: %r", form.errors)
        raise InvalidCommentPostRequest(target, form)

    # Otherwise create the comment
    comment = form.get_comment_object()
    comment.ip_address = remote_addr
    if request_user.is_authenticated:
        comment.user = request_user
    comment.save()

    return target, comment


def add_comment(request_user, content_type, object_pks, comment, remote_addr=None) -> List[Comment]:
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
            log.error(
                "%s object with id %s does not exist in database. "
                "Ignore it and continue to add comment to next one.",
                content_type,
                object_pk,
            )
            continue
        initial_form = comment_form(target)
        comment_data = initial_form.initial.copy()
        comment_data["comment"] = comment
        try:
            _, new_comment = post_comment(comment_data, request_user, remote_addr)
        except InvalidCommentPostRequest:
            log.error("Failed to add comment, continue to add comment to next one.")
        else:
            new_comments.append(new_comment)
    return new_comments

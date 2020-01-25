# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import generic
from django.views.decorators.http import require_POST

import django_comments.signals
from django_comments.views.moderation import perform_delete

import tcms.comments
from tcms.core import utils

log = logging.getLogger(__name__)


class InvalidCommentPostRequest(Exception):
    """Raised if comment is not valid"""

    def __init__(self, target, form):
        self.target = target
        self.form = form


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

    ctype = comment_data.get('content_type')
    object_pk = comment_data.get('object_pk')

    target = get_comment_target_object(ctype, int(object_pk))

    form = tcms.comments.get_form()(target, data=comment_data)
    if not form.is_valid():
        log.error('Failed to add comment to %s %s: %r',
                  ctype, object_pk, comment_data)
        log.error('Error messages: %r', form.errors)
        raise InvalidCommentPostRequest(target, form)

    # Otherwise create the comment
    comment = form.get_comment_object()
    comment.ip_address = remote_addr
    if request_user.is_authenticated:
        comment.user = request_user
    comment.save()

    return target, comment


@require_POST
def post(request, template_name='comments/comments.html'):
    """Post a comment"""
    data = request.POST.copy()
    try:
        target, _ = post_comment(
            data, request.user, request.META.get('REMOTE_ADDR'))
    except InvalidCommentPostRequest as e:
        target = e.target
    return render(request, template_name, context={'object': target})


class DeleteCommentView(PermissionRequiredMixin, generic.View):
    """Delete comment from given objects"""

    permission_required = 'django_comments.can_moderate'

    def post(self, request):
        comments = django_comments.get_model().objects.filter(
            pk__in=request.POST.getlist('comment_id'),
            site__pk=settings.SITE_ID,
            is_removed=False,
            user_id=request.user.id
        )

        if not comments:
            return JsonResponse({'rc': 1, 'response': 'Object does not exist.'})

        # Flag the comment as deleted instead of actually deleting it.
        for comment in comments:
            perform_delete(request, comment)

        return JsonResponse({'rc': 0, 'response': 'ok'})

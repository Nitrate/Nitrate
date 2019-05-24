# -*- coding: utf-8 -*-

from django.contrib import admin
from django_comments.admin import CommentsAdmin
from django_comments.models import Comment
from tcms import BaseModelAdmin


class CustomCommentsAdmin(BaseModelAdmin, CommentsAdmin):
    """Customize widgets in Comment admin change page"""


admin.site.unregister(Comment)
admin.site.register(Comment, CustomCommentsAdmin)

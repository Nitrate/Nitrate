# -*- coding: utf-8 -*-

from django.urls import path

from . import views

urlpatterns = [
    path("post/", views.post, name="comments-post"),
    path("delete/", views.DeleteCommentView.as_view(), name="comments-delete"),
]

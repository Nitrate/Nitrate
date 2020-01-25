# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^post/$', views.post, name='comments-post'),
    url(r'^delete/$', views.DeleteCommentView.as_view(), name='comments-delete'),
]

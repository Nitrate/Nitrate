# -*- coding: utf-8 -*-

from django.urls import path

from . import views

urlpatterns = [
    path("", views.advance_search, name="advanced-search"),
]

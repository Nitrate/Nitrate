# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^add/$', views.add, name='add-link-reference'),
    url(r'^get/$', views.get, name='get-link-references'),
    url(r'^remove/(?P<link_id>\d+)/$', views.remove, name='remove-link-reference'),
]

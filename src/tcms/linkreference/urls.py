# -*- coding: utf-8 -*-

from django.conf.urls import url
from tcms.linkreference import views

urlpatterns = [
    url(r'^add/$', views.AddLinkToTargetView.as_view(),
        name='add-link-reference'),

    url(r'^get/$', views.get, name='get-link-references'),

    url(r'^remove/(?P<link_id>\d+)/$', views.RemoveLinkReferenceView.as_view(),
        name='remove-link-reference'),
]

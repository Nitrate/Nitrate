# -*- coding: utf-8 -*-

from django.conf.urls import include, url, patterns

from tcms.testplans.views import NewTestPlanView
from tcms.testplans.views import ShowAllPlanView
from tcms.testplans.views import CloneTestplanView

urlpatterns = patterns('tcms.testplans.views',
    url(r'^$',
        ShowAllPlanView.as_view(),
        name='show_all_plan_view'),
    url(r'^new/$',
        NewTestPlanView.as_view(),
        name='testplan_new_test_plan'
    ),
    url(r'^ajax/$', 'ajax_search'),
    url(r'^treeview/$', 'tree_view'),
    url(r'^clone/$',
        CloneTestplanView.as_view(),
        name='testplans_clone_testplan'
    ),
    url(r'^printable/$','printable'),
    url(r'^export/$', 'export'),
    url(r'^component/$', 'component'),
)

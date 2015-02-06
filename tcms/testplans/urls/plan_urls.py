 # -*- coding: utf-8 -*-

from django.conf.urls import include, url, patterns

from tcms.testplans.views import AddCaseToRunView
from tcms.testplans.views import EditPlanView
from tcms.testplans.views import AttachmentView
from tcms.testplans.views import TestHistoryView

urlpatterns = patterns('tcms.testplans.views',
    url(r'^(?P<plan_id>\d+)/$', 'get', name='test_plan_url'),
    url(r'^(?P<plan_id>\d+)/(?P<slug>[-\w\d]+)$', 'get', name='test_plan_url'),
    url(r'^(?P<plan_id>\d+)/chooseruns/$',
        AddCaseToRunView.as_view(),
        name='add_case_to_run'
    ),
    url(r'^(?P<plan_id>\d+)/edit/$',
        EditPlanView.as_view(),
        name='edit_plan_view'
    ),
    url(r'^(?P<plan_id>\d+)/attachment/$',
        AttachmentView.as_view(),
        name='attachment_view'
    ),
    url(r'^(?P<plan_id>\d+)/history/$',
        TestHistoryView.as_view(),
        name='testplan_text_history'
    ),
    url(r'^(?P<plan_id>\d+)/cases/$',
        'cases'
    ),
)

urlpatterns += patterns('tcms.testruns.views',
    url(r'^(?P<plan_id>\d+)/runs/$',
        'load_runs_of_one_plan',
        name='load_runs_of_one_plan_url'),
)
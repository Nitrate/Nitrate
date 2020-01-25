# -*- coding: utf-8 -*-

from django.conf.urls import url

from .. import views
from tcms.testruns import views as testruns_views

urlpatterns = [
    url(r'^(?P<case_id>\d+)/$', views.get, name='case-get'),
    url(r'^(?P<case_id>\d+)/edit/$', views.edit, name='case-edit'),
    url(r'^(?P<case_id>\d+)/history/$', views.text_history, name='case-text-history'),
    url(r'^(?P<case_id>\d+)/attachment/$', views.ListCaseAttachmentsView.as_view(),
        name='case-attachment'),
    url(r'^(?P<case_id>\d+)/log/$', views.get_log, name='case-get-log'),
    url(r'^(?P<case_id>\d+)/issue/$', views.manage_case_issues, name='case-issue'),
    url(r'^(?P<case_id>\d+)/plan/$', views.plan, name='case-plan'),
    url(r'^(?P<case_id>\d+)/readonly-pane/$', views.SimpleTestCaseView.as_view(),
        name='case-readonly-pane'),
    url(r'^(?P<case_id>\d+)/review-pane/$', views.TestCaseReviewPaneView.as_view(),
        name='case-review-pane'),
    url(r'^(?P<case_id>\d+)/caserun-list-pane/$', views.TestCaseCaseRunListPaneView.as_view(),
        name='caserun-list-pane'),
    url(r'^(?P<case_id>\d+)/caserun-simple-pane/$', views.TestCaseSimpleCaseRunView.as_view(),
        name='caserun-simple-pane'),
    url(r'^(?P<case_id>\d+)/caserun-detail-pane/$', views.TestCaseCaseRunDetailPanelView.as_view(),
        name='caserun-detail-pane'),

    url(r'^(?P<plan_id>\d+)/runs/$', testruns_views.load_runs_of_one_plan,
        name='load_runs_of_one_plan_url'),
]

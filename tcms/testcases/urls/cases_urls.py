# -*- coding: utf-8 -*-

from django.conf.urls import url, patterns
from tcms.testcases.views import CreateNewTestCaseView
from tcms.testcases.views import LoadMoreCaseView
from tcms.testcases.views import SearchView
from tcms.testcases.views import CloneCaseView
from tcms.testcases.views import PrintableView

urlpatterns = patterns('tcms.testcases.views',
                       url(r'^new/$',CreateNewTestCaseView.as_view(),
                           name='testcases_add_new_testcase'
                           ),
                       url(r'^$', 'all'),
                       url(r'^search/$',SearchView.as_view(),
                           name='search_case_view'
                           ),
                       url(r'^load-more/$',LoadMoreCaseView.as_view(),
                           name='load_more_cases'
                           ),
                       url(r'^ajax/$', 'ajax_search'), # no clearly view
                       url(r'^automated/$', 'automated'), # no clearly view
                       url(r'^tag/$', 'tag'), # no clearly view
                       url(r'^component/$', 'component'), # no clearly view
                       url(r'^category/$', 'category'), # no clearly view
                       url(r'^clone/$', CloneCaseView.as_view(),
                           name='testcases_add_clone_testcase'
                           ),
                       url(r'^printable/$',PrintableView.as_view(),
                           'testcase_printable_view'
                           ),
                       url(r'^export/$', 'export'), # It's a XML
                       )

# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

# XML RPC handler
from kobo.django.xmlrpc.views import XMLRPCHandlerFactory

from tcms.core import ajax as tcms_core_ajax
from tcms.testruns import views as testruns_views

xmlrpc_handler = XMLRPCHandlerFactory("TCMS_XML_RPC")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    path("", include("tcms.core.urls")),
    path("", include("tcms.management.urls")),
    # Testplans zone
    path("plan/", include("tcms.testplans.urls.plan_urls")),
    path("plans/", include("tcms.testplans.urls.plans_urls")),
    # Testcases zone
    path("case/", include("tcms.testcases.urls.case_urls")),
    path("cases/", include("tcms.testcases.urls.cases_urls")),
    # Testruns zone
    path("run/", include("tcms.testruns.urls.run_urls")),
    path("runs/", include("tcms.testruns.urls.runs_urls")),
    path("accounts/", include("tcms.profiles.urls")),
    path("linkref/", include("tcms.linkreference.urls")),
    path("comments/", include("tcms.comments.urls")),
    path("advance-search/", include("tcms.search.urls")),
    path("report/", include("tcms.report.urls")),
    path("xmlrpc/", xmlrpc_handler),
    path("tinymce/", include("tinymce.urls")),
    # Using admin js without admin permission
    # refer: https://docs.djangoproject.com/en/1.6/topics/i18n/translation/#module-django.views.i18n
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
]

# Debug zone

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]

# Overwrite default 500 handler
# More details could see django.core.urlresolvers._resolve_special()
handler500 = "tcms.core.views.error.server_error"

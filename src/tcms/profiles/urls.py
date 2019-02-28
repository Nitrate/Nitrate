# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.contrib.auth import views as django_auth_views
from tcms.auth.views import LoginView as NitrateLoginView

from . import views
from tcms.auth import views as tcms_auth_views

urlpatterns = [
    url(r'^profile/$', views.redirect_to_profile, name='user-profile-redirect'),
    url(r'^(?P<username>[\w.@+-]+)/profile/$', views.profile, name='user-profile'),
    url(r'^(?P<username>[\w.@+-]+)/bookmarks/$', views.bookmark, name='user-bookmark'),
    url(r'^(?P<username>[\w.@+-]+)/recent/$', views.recent, name='user-recent'),

    url(r'logout/$', tcms_auth_views.logout, name='nitrate-logout'),
    url(r'register/$', tcms_auth_views.register, name='nitrate-register'),
    url(r'confirm/(?P<activation_key>[A-Za-z0-9\-]+)/$',
        tcms_auth_views.confirm, name='nitrate-activation-confirm'),

    url(r'login/$', NitrateLoginView.as_view(), name='nitrate-login'),
    url(r'changepassword/$', django_auth_views.PasswordChangeView.as_view(), name='password_change'),
    url(r'changepassword/done/$', django_auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    url(r'^passwordreset/$', django_auth_views.PasswordResetView.as_view(), name='password_reset'),
    url(r'^passwordreset/done/$', django_auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    url(r'^passwordreset/confirm//(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        django_auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]

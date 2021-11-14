# -*- coding: utf-8 -*-

from django.contrib.auth import views as django_auth_views
from django.urls import path, re_path

from tcms.auth import views as tcms_auth_views
from tcms.auth.views import LoginView as NitrateLoginView

from . import views

urlpatterns = [
    path("profile/", views.redirect_to_profile, name="user-profile-redirect"),
    re_path(r"^(?P<username>[\w.@+-]+)/profile/$", views.profile, name="user-profile"),
    re_path(r"^(?P<username>[\w.@+-]+)/recent/$", views.recent, name="user-recent"),
    path("logout/", tcms_auth_views.logout, name="nitrate-logout"),
    path("register/", tcms_auth_views.register, name="nitrate-register"),
    re_path(
        r"confirm/(?P<activation_key>[A-Za-z0-9\-]+)/$",
        tcms_auth_views.confirm,
        name="nitrate-activation-confirm",
    ),
    path("login/", NitrateLoginView.as_view(), name="nitrate-login"),
    path(
        "changepassword/",
        django_auth_views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "changepassword/done/",
        django_auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path(
        "passwordreset/",
        django_auth_views.PasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "passwordreset/done/",
        django_auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    re_path(
        r"^passwordreset/confirm//(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$",
        django_auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]

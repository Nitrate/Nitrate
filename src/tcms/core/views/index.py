# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect
from django.urls import reverse


def index(request, template_name="index.html"):
    """
    Home page of TCMS
    """

    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("nitrate-login"))

    return HttpResponseRedirect(reverse("user-recent", args=[request.user.username]))

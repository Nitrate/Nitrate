# -*- coding: utf-8 -*-
# FIXME: Use exception to replace the feature

from django.http import HttpRequest
from django.shortcuts import render

PROMPT_ALERT = "alert"
PROMPT_INFO = "info"


def alert(request: HttpRequest, content: str, next_: str = None):
    return render(
        request,
        "prompt.html",
        context={"type": PROMPT_ALERT, "info": content, "next": next_},
    )


def info(request: HttpRequest, content: str, next_: str = None):
    return render(
        request,
        "prompt.html",
        context={"type": PROMPT_INFO, "info": content, "next": next_},
    )

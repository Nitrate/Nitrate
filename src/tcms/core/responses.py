# -*- coding: utf-8 -*-

from django import http

__all__ = (
    'JsonResponseBadRequest',
    'JsonResponseServerError',
)


class JsonResponseBadRequest(http.JsonResponse):
    status_code = 400


class JsonResponseServerError(http.JsonResponse):
    status_code = 500

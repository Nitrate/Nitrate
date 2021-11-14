# -*- coding: utf-8 -*-

from http import HTTPStatus

from django import http

__all__ = (
    "JsonResponseBadRequest",
    "JsonResponseForbidden",
    "JsonResponseNotFound",
    "JsonResponseServerError",
    "JsonResponseUnauthorized",
)


class JsonResponseBadRequest(http.JsonResponse):
    status_code = HTTPStatus.BAD_REQUEST


class JsonResponseUnauthorized(http.JsonResponse):
    status_code = HTTPStatus.UNAUTHORIZED


class JsonResponseServerError(http.JsonResponse):
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class JsonResponseNotFound(http.JsonResponse):
    status_code = HTTPStatus.NOT_FOUND


class JsonResponseForbidden(http.JsonResponse):
    status_code = HTTPStatus.FORBIDDEN

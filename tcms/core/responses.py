# -*- coding: utf-8 -*-

from functools import partial

from django import http


__all__ = (
    'HttpJSONResponseBadRequest',
    'HttpJSONResponseServerError',
)


MIMETYPE_JSON = 'application/json'

HttpJSONResponseBadRequest = partial(http.HttpResponseBadRequest,
                                     content_type=MIMETYPE_JSON)
HttpJSONResponseServerError = partial(http.HttpResponseServerError,
                                      content_type=MIMETYPE_JSON)

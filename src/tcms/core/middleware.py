# -*- coding: utf-8 -*-


class CsrfDisableMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Do default behavior for this middleware, as here is not where it gets
        # work done.
        return self.get_response(request)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        setattr(request, '_dont_enforce_csrf_checks', True)

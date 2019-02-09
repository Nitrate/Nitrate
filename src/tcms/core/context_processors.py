# -*- coding: utf-8 -*-
from django.conf import settings


def admin_prefix_processor(request):
    """
    Django Admin URL Prefix RequestContext Handler
    """
    return {'ADMIN_PREFIX': settings.ADMIN_PREFIX}


def request_contents_processor(request):
    """
    Django request contents RequestContext Handler
    """
    return {'REQUEST_CONTENTS': request.GET or request.POST}


def settings_processor(request):
    """
    Django settings RequestContext Handler
    """
    return {'SETTINGS': settings}

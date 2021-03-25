# -*- coding: utf-8 -*-

from django.conf import settings

if settings.ASYNC_TASK == "CELERY":
    # This will make sure the app is always imported when
    # Django starts so that shared_task will use this app.
    from .celery import app as celery_app

    __all__ = ["celery_app"]

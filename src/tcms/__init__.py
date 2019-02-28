# -*- coding: utf-8 -*-

from django.conf import settings

try:
    import pymysql
except ImportError:
    # Database backend is selectable. When another is selected other than
    # mysql, skip the call in else section.
    pass
else:
    pymysql.install_as_MySQLdb()

if settings.ASYNC_TASK == 'CELERY':
    # This will make sure the app is always imported when
    # Django starts so that shared_task will use this app.
    from .celery import app as celery_app

    __all__ = ['celery_app']

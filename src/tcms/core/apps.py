# -*- coding: utf-8 -*-

import logging

from django.apps import AppConfig as DjangoAppConfig
from django.conf import settings
from django.db import connections
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


SQLs = {
    'postgresql': (
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = 'django_comments' AND column_name = 'object_pk'",

        'ALTER TABLE django_comments ALTER COLUMN object_pk TYPE INTEGER '
        'USING object_pk::integer'
    ),

    'mysql': (
        "SELECT DATA_TYPE FROM information_schema.columns "
        "WHERE table_schema = '{}' AND table_name = 'django_comments' "
        "AND COLUMN_NAME = 'object_pk'",

        'ALTER TABLE django_comments MODIFY object_pk INT'
    )
}


def ensure_django_comment_object_pk_is_int(*args, **kwargs):
    for db_key, db_info in settings.DATABASES.items():
        _, db_engine = db_info['ENGINE'].rsplit('.', 1)

        if db_engine not in SQLs:
            logger.warning(
                'Engine %s is not supported to modify data type of column '
                'django_comment.object_pk.', db_engine)
            return

        query, alter = SQLs[db_engine]
        schema_name = db_info['NAME']
        query = query.format(schema_name)

        with connections[db_key].cursor() as cursor:
            cursor.execute(query)
            type_name, = cursor.fetchone()
            need_modify = type_name.lower() not in ('int', 'integer')

        if need_modify:
            logger.info(
                'Change django_comments.object_pk to INTEGER in database %s',
                schema_name)
            with connections[db_key].cursor() as cursor:
                cursor.execute(alter)


class AppConfig(DjangoAppConfig):
    label = 'core'
    name = 'tcms.core'
    verbose_name = _("Core App")

    def ready(self):
        post_migrate.connect(ensure_django_comment_object_pk_is_int)

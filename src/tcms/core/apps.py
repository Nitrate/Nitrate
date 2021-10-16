# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from textwrap import dedent

from django.apps import AppConfig as DjangoAppConfig
from django.conf import settings
from django.db import connections
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


SQLs = {
    "postgresql": (
        # Thanks for the answer: https://stackoverflow.com/q/2204058/968262
        dedent(
            """\
            select 'placeholder' as ph1, 'placeholder' as ph2, i.relname as Key_name
            from pg_class t, pg_class i, pg_index ix, pg_attribute a
            where
                t.oid = ix.indrelid
                and i.oid = ix.indexrelid
                and a.attrelid = t.oid
                and a.attnum = ANY(ix.indkey)
                and t.relkind = 'r'
                and t.relname = 'django_comments'
                and a.attname = 'object_pk'
            order by t.relname, i.relname;
        """
        ),
        "DROP INDEX {}",
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = 'django_comments' AND column_name = 'object_pk'",
        "ALTER TABLE django_comments ALTER COLUMN object_pk TYPE INTEGER "
        "USING object_pk::integer",
    ),
    "mysql": (
        # Key_name is the 3rd column
        "SHOW INDEXES FROM django_comments WHERE Column_name = 'object_pk'",
        "DROP INDEX {} ON django_comments",
        "SELECT DATA_TYPE FROM information_schema.columns "
        "WHERE table_schema = '{}' AND table_name = 'django_comments' "
        "AND COLUMN_NAME = 'object_pk'",
        "ALTER TABLE django_comments MODIFY object_pk INT",
    ),
}


def ensure_django_comment_object_pk_is_int(*args, **kwargs):
    for db_key, db_info in settings.DATABASES.items():
        _, db_engine = db_info["ENGINE"].rsplit(".", 1)

        if db_engine not in SQLs:
            logger.warning(
                "Engine %s is not supported to modify data type of column "
                "django_comment.object_pk.",
                db_engine,
            )
            return

        sql_find_indexes, sql_drop_idx, query, alter = SQLs[db_engine]
        schema_name = db_info["NAME"]
        query = query.format(schema_name)

        with connections[db_key].cursor() as cursor:
            cursor.execute(query)
            (type_name,) = cursor.fetchone()
            need_modify = type_name.lower() not in ("int", "integer")

        if need_modify:
            # Before alter the column, find existing indexes and remove them.
            # Later, the indexes will be created back.
            # This is required since the version 2.1.0 of django-contrib-comments,
            # which adds indexes to the django_comments.object_pk column

            with connections[db_key].cursor() as cursor:
                cursor.execute(sql_find_indexes)
                rows = cursor.fetchall()

            had_index = False
            with connections[db_key].cursor() as cursor:
                for row in rows:
                    had_index = True
                    # 2: the column name
                    cursor.execute(sql_drop_idx.format(row[2]))

            logger.info(
                "Change django_comments.object_pk to INTEGER in database %s",
                schema_name,
            )
            with connections[db_key].cursor() as cursor:
                cursor.execute(alter)

            if had_index:
                # For this special case of django_comments, there is no special
                # index on the original django_comments.object_pk column. So,
                # after altering it to the integer type, a btree index is good
                # enough. Note that, btree is the default for PostgreSQL,
                # and the MySQL and MariaDB with InnoDB engine.
                now = datetime.now().strftime("%Y%m%d%H%M%S")
                with connections[db_key].cursor() as cursor:
                    cursor.execute(
                        f"CREATE INDEX django_comments__object_pk__{now} "
                        f"ON django_comments (object_pk)"
                    )


class AppConfig(DjangoAppConfig):
    label = "tcms_core"
    name = "tcms.core"
    verbose_name = _("Core App")

    def ready(self):
        post_migrate.connect(ensure_django_comment_object_pk_is_int)

#!/usr/bin/python3

import logging
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger('entrypoint')

import django
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection


def create_superuser():
    username = os.environ.get('NITRATE_SUPERUSER_USERNAME')
    password = os.environ.get('NITRATE_SUPERUSER_PASSWORD')
    email = os.environ.get('NITRATE_SUPERUSER_EMAIL')

    if not (username and password and email):
        logger.info(
            'NITRATE_SUPERUSER_USERNAME, NITRATE_SUPERUSER_PASSWORD and NITRATE_SUPERUSER_EMAIL are not set. '
            'Skip creating a superuser.'
        )
        return

    try:
        if User.objects.filter(username=username, email=email, is_superuser=True).exists():
            logger.info('Superuser %s has been created.', username)
            return
    except:  # noqa
        pass

    try:
        User.objects.create_superuser(username, email=email, password=password)
        logger.info('Superuser %s is created successfully.', username)
    except Exception as e:
        logger.warning('Failed to create superuser %s: %s', username, e)
        logger.warning('Please check if the database is initialized properly.')


def set_default_permissions():
    if os.environ.get('NITRATE_SET_DEFAULT_PERMS'):
        try:
            call_command('setdefaultperms')
            logger.info('Default groups are created and permissions are set to groups properly.')
        except Exception as e:
            logger.warning('Failed to run command setdefaultperms: %s', e)
            logger.warning('Please check if the database is initialized properly.')
    else:
        logger.info(
            'Environment variable NITRATE_SET_DEFAULT_PERMS is not set. '
            'Skip creating default groups and granting permissions to specific group.'
        )


def migrate_db():
    if os.environ.get('NITRATE_MIGRATE_DB'):
        try:
            call_command('migrate')
            logger.info('Database is migrated successfully.')
        except Exception as e:
            logger.warning('Failed to migrate the database: %s', e)
    else:
        logger.info('Environment variable NITRATE_MIGRATE_DB is not set. Skip migrating database.')


def wait_for_db():
    while 1:
        try:
            connection.cursor()
        except:  # noqa
            logger.debug('Failed to connect to database. Sleep for a while and try again ...')
            time.sleep(0.5)
        else:
            break


if __name__ == '__main__':
    wait_for_db()
    migrate_db()
    create_superuser()
    set_default_permissions()

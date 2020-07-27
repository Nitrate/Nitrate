#!/usr/bin/env python3
#
# Nitrate is a test case management system.
# Copyright (C) 2019  Nitrate Team
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import argparse
import logging
import os
import re
import subprocess

from typing import Dict, List

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

DB_CONTAINER_NAME = 'nitrate-test-db'
TEST_DB_NAME = 'nitrate'
TEST_BOX_IMAGE = 'quay.io/nitrate/testbox:latest'
VALID_NITRATE_DB_NAMES = ['mysql', 'mariadb', 'postgres', 'sqlite']
# Since this script was written originally to work inside Travis-CI, using
# Python version 3.6 and 3.7 would be much easier to match the value of
# environment variable TRAVIS_PYTHON_VERSION.
VALID_PYTHON_VERSIONS = ['3.6', '3.7', '3.8']
DB_CONTAINER_INFO = {
    'mysql': {
        'db_engine': 'mysql',
        'db_image': 'mysql:8.0.20',
    },
    'mariadb': {
        'db_engine': 'mysql',
        'db_image': 'mariadb:10.4.12',
    },
    'sqlite': {
        'db_engine': 'sqlite',
        'db_image': '',
    },
    'postgres': {
        'db_engine': 'pgsql',
        'db_image': 'postgres:12.2',
    },
}


def validate_django_ver(value):
    regex = r'^django(>|>=|<|<=)[0-9]+\.[0-9]+,(>|>=|<|<=)[0-9]+\.[0-9]+$'
    if not re.match(regex, value):
        raise argparse.ArgumentTypeError(
            f"Invalid django version specifier '{value}'.")
    return value


def validate_project_dir(value):
    if os.path.exists(value):
        return value
    return argparse.ArgumentTypeError(
        'Invalid project root directory. It might not exist.')


def docker_run(image,
               rm: bool = False,
               detach: bool = False,
               interactive: bool = False,
               tty: bool = False,
               name: str = None,
               link: str = None,
               volumes: List[str] = None,
               envs: Dict[str, str] = None,
               cmd_args: List[str] = None
               ) -> None:
    cmd = ['docker', 'run']
    if rm:
        cmd.append('--rm')
    if detach:
        cmd.append('--detach')
    if interactive:
        cmd.append('-i')
    if tty:
        cmd.append('-t')
    if name:
        cmd.append('--name')
        cmd.append(name)
    if link:
        cmd.append('--link')
        cmd.append(link)
    if volumes:
        for item in volumes:
            cmd.append('--volume')
            cmd.append(item)
    if envs:
        for var_name, var_value in envs.items():
            cmd.append('--env')
            cmd.append(f'{var_name}={var_value}')
    cmd.append(image)
    if cmd_args:
        cmd.extend(cmd_args)

    log.debug('Run: %r', cmd)
    subprocess.check_call(cmd)


def docker_ps(all_: bool = False,
              filter_: List[str] = None,
              quiet: bool = False) -> str:
    cmd = ['docker', 'ps']
    if all_:
        cmd.append('--all')
    if filter_:
        for item in filter_:
            cmd.append('--filter')
            cmd.append(item)
    if quiet:
        cmd.append('--quiet')

    log.debug('Run: %r', cmd)
    return subprocess.check_output(cmd, universal_newlines=True)


def docker_stop(name: str) -> None:
    cmd = ['docker', 'stop', name]
    log.debug('Run: %r', cmd)
    subprocess.check_call(cmd)


def stop_container(name: str) -> None:
    c_hash = docker_ps(all_=True, filter_=[f'name={name}'], quiet=True)
    if c_hash:
        docker_stop(name)


def main():
    parser = argparse.ArgumentParser(
        description='Run tests matrix inside containers. This is particularly '
                    'useful for running tests in Travis-CI.'
    )
    parser.add_argument(
        '--python-ver',
        choices=VALID_PYTHON_VERSIONS,
        default='3.7',
        help='Specify Python version')
    parser.add_argument(
        '--django-ver',
        type=validate_django_ver,
        default='django<2.3,>=2.2',
        help='Specify django version specifier')
    parser.add_argument(
        '--nitrate-db',
        choices=VALID_NITRATE_DB_NAMES,
        default='sqlite',
        help='Database engine name')
    parser.add_argument(
        '--project-dir',
        metavar='DIR',
        type=validate_project_dir,
        default=os.path.abspath(os.curdir),
        help='Project root directory. Default to current working directory')
    parser.add_argument(
        'targets', nargs='+', help='Test targets')

    args = parser.parse_args()

    container_info = DB_CONTAINER_INFO[args.nitrate_db]
    db_engine = container_info['db_engine']
    db_image = container_info['db_image']

    stop_container(DB_CONTAINER_NAME)

    test_box_run_opts = None

    if db_engine == 'mysql':
        docker_run(
            db_image,
            rm=True,
            name=DB_CONTAINER_NAME,
            detach=True,
            envs={
               'MYSQL_ALLOW_EMPTY_PASSWORD': 'yes',
               'MYSQL_DATABASE': 'nitrate'
            },
            cmd_args=[
               '--character-set-server=utf8mb4',
               '--collation-server=utf8mb4_unicode_ci'
            ])
        test_box_run_opts = {
            'link': f'{DB_CONTAINER_NAME}:mysql',
            'envs': {
                'NITRATE_DB_ENGINE': db_engine,
                'NITRATE_DB_NAME': TEST_DB_NAME,
                'NITRATE_DB_HOST': DB_CONTAINER_NAME,
            }
        }
    elif db_engine == 'pgsql':
        docker_run(
            db_image,
            rm=True,
            detach=True,
            name=DB_CONTAINER_NAME,
            envs={'POSTGRES_PASSWORD': 'admin'}
        )
        test_box_run_opts = {
            'link': f'{DB_CONTAINER_NAME}:postgres',
            'envs': {
                'NITRATE_DB_ENGINE': db_engine,
                'NITRATE_DB_HOST': DB_CONTAINER_NAME,
                'NITRATE_DB_NAME': TEST_DB_NAME,
                'NITRATE_DB_USER': 'postgres',
                'NITRATE_DB_PASSWORD': 'admin',
            }
        }
    elif db_engine == 'sqlite':
        # No need to launch a SQLite docker image
        test_box_run_opts = {
            'envs': {
                'NITRATE_DB_ENGINE': db_engine,
                'NITRATE_DB_NAME': "file::memory:",
            }
        }

    test_box_container_name = f'nitrate-testbox-py{args.python_ver.replace(".", "")}'
    test_box_run_opts.update({
        'rm': True,
        'interactive': True,
        'tty': True,
        'name': test_box_container_name,
        'volumes': [f'{args.project_dir}:/code:Z'],
    })
    test_box_run_opts['envs'].update({
        'PYTHON_VER': f'py{args.python_ver.replace(".", "")}',
        'DJANGO_VER': args.django_ver,
        'TEST_TARGETS': '"{}"'.format(' '.join(args.targets)),
    })

    try:
        log.debug('Start testbox to run tests')
        docker_run(TEST_BOX_IMAGE, **test_box_run_opts)
    finally:
        log.debug('Stop container: %s', DB_CONTAINER_NAME)
        stop_container(DB_CONTAINER_NAME)


if __name__ == '__main__':
    main()

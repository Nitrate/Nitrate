#!/usr/bin/env bash
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

# This script is intended for running tests in Travis-CI.
# However, developer could execute this script locally to run tests inside containers.
#
# Arguments: PY_VERSION:  DJANGO_REL, NITRATE_DB

set -ex

# python version which will run tests. For example, 2.7.15, 3.7.1.
py_version=$1
# django version to run tests with. For example, django>=1.11,<2.0
django_rel=$2
# database engine name to test with. For example, mysql, mariadb and even pgsql.
# This is optional. If omitted, use default SQLite.
nitrate_db=${3-sqlite}

install_extra_deps="tests,docs"
py_version=${py_version%.*}

if [ "$py_version" == "2.7" ] || [ "$py_version" == "3.6" ]; then
    extra_deps="${install_extra_deps},async"
fi

case $py_version in
    2.7)
        py_bin=python2.7
        install_extra_deps="${install_extra_deps},async"
        ;;
    3.6)
        py_bin=python3.6
        install_extra_deps="${install_extra_deps},async"
        ;;
    3.7)
        py_bin=python3.7
        ;;
esac

case "$nitrate_db" in
    mysql)
        db_engine=mysql
        image=mysql:5.7
        ;;
    mariadb)
        db_engine=mysql
        image=mariadb:10.2.21
        ;;
    sqlite)
        db_engine=sqlite
        image=
        ;;
    postgres)
        db_engine=pgsql
        image=postgres:10.6
esac

script_dir=$(dirname "$(realpath "$0")")
project_dir=$(realpath "$script_dir/../..")

# FIXME: how to launch container for pgsql?
# Test database always has name nitrate, and could be accessible by root
# without password.
case "$db_engine" in
    mysql)
        docker run --rm --name db \
            --env MYSQL_ALLOW_EMPTY_PASSWORD=yes \
            --env MYSQL_DATABASE=nitrate \
            --detach \
            "$image" \
            --character-set-server=utf8mb4 \
            --collation-server=utf8mb4_unicode_ci

        docker_run_opts=(--link db:mysql
                         --env NITRATE_DB_ENGINE="$db_engine"
                         --env NITRATE_DB_NAME=nitrate
                         --env NITRATE_DB_HOST=db)
        trap 'docker stop db' EXIT ERR
        ;;
    pgsql)
        docker run --name db -e POSTGRES_PASSWORD=admin --detach "$image"
        docker_run_opts=(--link db:postgres
                         --env NITRATE_DB_ENGINE="$db_engine"
                         --env NITRATE_DB_HOST=db
                         --env NITRATE_DB_NAME=nitrate
                         --env NITRATE_DB_USER=postgres
                         --env NITRATE_DB_PASSWORD=admin)
        trap 'docker stop db' EXIT ERR
        ;;
    sqlite)
        # No need to launch a SQLite docker image
        docker_run_opts=(--env NITRATE_DB_ENGINE="$db_engine"
                         --env NITRATE_DB_NAME="file::memory:")
        ;;
esac

# db is the name of database container
# All rest database relative environment variables are defaults.
# Refer to tcms/settings/test.py

docker run --rm --name nitrate-testbox ${docker_run_opts[@]} \
    -v "$project_dir":/code:Z -i -t registry.fedoraproject.org/fedora:29 \
    /bin/bash -c "
set -e

dnf install -y gcc redhat-rpm-config make mariadb python36 python3-virtualenv \
    python3-devel graphviz-devel postgresql-devel
virtualenv --python=${py_bin} /testenv
source /testenv/bin/activate
pip install \"${django_rel}\"
pip install -e /code[${install_extra_deps}]

cd /code
py.test tcms
flake8 tcms
cd docs; make html
"

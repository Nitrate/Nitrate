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

# shellcheck disable=SC1090

set -ex

if [ "$NITRATE_DB_ENGINE" == "mysql" ]; then
    while true; do
        echo "Waiting for database server to launch completely ..."
        sleep 1
        if echo "use $NITRATE_DB_NAME" | mysql -u root -h $NITRATE_DB_HOST; then
            break
        fi
    done
elif [ "$NITRATE_DB_ENGINE" == "pgsql" ]; then
    export PGPASSWORD=admin
    while true; do
        echo "Waiting for database server to launch completely ..."
        sleep 1
        if psql -U postgres -h $NITRATE_DB_HOST -c "\\l" >/dev/null; then
            break
        fi
    done
fi

echo "Database is ready 🎉"

cd /code

. "/testenv-${PYTHON_VER}/bin/activate"

pip uninstall --yes Django
pip install "$DJANGO_VER"

py.test $(echo $TEST_TARGETS | xargs)

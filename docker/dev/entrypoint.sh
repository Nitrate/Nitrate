#!/usr/bin/env bash

set -e

db_name=nitrate

if [ "$NITRATE_DB_ENGINE" == "mysql" ]; then
    while true; do
        echo "Waiting for database server to launch completely ..."
        sleep 1
        if echo "show databases" | mysql -u root -h $NITRATE_DB_HOST >/dev/null; then
            echo "Database instance is launched."
            break
        fi
    done
    if ! echo "show databases;" | mysql -u root -h db | grep $db_name >/dev/null; then
        echo "create database ${db_name} character set utf8;" | mysql -u root -h db
    fi
fi

source /devenv/bin/activate
cd /code

manage_py=(python3 src/manage.py)

if ${manage_py[@]} showmigrations | grep "\[ \]" >/dev/null; then
    ${manage_py[@]} migrate
    ${manage_py[@]} setdefaultperms
fi

${manage_py[@]} shell -c "
from django.contrib.auth.models import User
username = 'admin'
user = User.objects.filter(username=username).first()
if not user:
    User.objects.create_superuser(username, 'admin@example.com', 'admin')
"

${manage_py[@]} runserver 0.0.0.0:8000

#!/usr/bin/env bash

set -e

db_name=nitrate

if [ "$NITRATE_DB_ENGINE" == "mysql" ]; then
    if ! echo "show databases;" | mysql -u root -h db | grep $db_name >/dev/null; then
        echo "create database ${db_name} character set utf8;" | mysql -u root -h db
    fi
fi

source /devenv/bin/activate
cd /code

if python manage.py showmigrations | grep "\[ \]" >/dev/null; then
    python manage.py migrate
    python contrib/scripts/default-permissions.py
fi

python manage.py shell -c "
from django.contrib.auth.models import User
username = 'admin'
user = User.objects.filter(username=username).first()
if not user:
    User.objects.create_superuser(username, 'admin@example.com', 'admin')
"

python manage.py runserver 0.0.0.0:8000

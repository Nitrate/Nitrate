#!/usr/bin/env bash

function logger
{
    local -r level=$1
    local -r msg=$2
    echo "[${level^^}] $msg"
}

venv_dir=$HOME/nitrate-env
venv_activate="${venv_dir}/bin/activate"
code_dir=/code

if [[ -e "$venv_dir" ]]; then
    logger info "Virtual environment ${venv_dir} exists already."
else
    logger info "Create Python virtual environment."
    python3 -m venv "$venv_dir"
fi

. "$venv_activate"

# Suppress message like:
# You should consider upgrading via the 'pip install --upgrade pip' command
pip install --upgrade pip

cd $code_dir

logger info "Install project dependent packages."
pip install -e .[mysql,krbauth,docs,tests,devtools]

logger info "Migrate database."
./src/manage.py migrate

logger info "Set default permissions to groups."
./src/manage.py setdefaultperms

logger info "Create a superuser if there is no one."
admin_exists=$(./src/manage.py shell -c "\
from django.contrib.auth.models import User
user = User.objects.filter(username='admin').first()
print(user.is_superuser if user is not None else False)
")

if [[ "$admin_exists" == "False" ]]; then
    logger info "Create a superuser with username and password admin:admin"
    ./src/manage.py createsuperuser --noinput --username admin --email admin@example.com
    ./src/manage.py shell -c "\
from django.contrib.auth.models import User
user = User.objects.get(username='admin')
user.set_password('admin')
user.save()
"
fi

deactivate

profile=~/.bash_profile

if ! grep "cd ${code_dir}" "$profile" >/dev/null; then
    echo "cd ${code_dir}" >> "$profile"
fi

if ! grep ". ${venv_activate}" "$profile" >/dev/null; then
    echo ". ${venv_activate}" >> "$profile"
fi

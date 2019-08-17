#!/usr/bin/env bash

function logger
{
    local -r level=$1
    local -r msg=$2
    echo "[${level^^}] $msg"
}

# All commands running from this script require to be root.

dnf install -y \
    copr-cli ctags docker findutils gcc git mock neovim \
    redhat-rpm-config rpm-build rpmdevtools rpmlint \
    graphviz-devel \
    mariadb-devel mariadb-server \
    postgresql postgresql-devel postgresql-server \
    python2 python2-devel \
    python3 python3-devel python3-ipdb python3-ipython

logger info "Add user $USER to group mock"
if ! grep "mock" /etc/group > /dev/null; then
    groupadd mock
fi
usermod -a -G mock "$USER"

# TODO: PostgreSQL should be the default database backend.

if [[ ! -e "/var/lib/pgsql/data/pg_hba.conf" ]]; then
    logger info "Initialize postgresql database"
    postgresql-setup --initdb
else
    logger info "PostgreSQL data directory exists, skip initialization."
fi

for service in mariadb postgresql docker; do
    logger info "Start and enable service $service"
    systemctl start $service
    systemctl enable $service
done

if ! mysql -uroot -e "SHOW DATABASES;" | grep "nitrate" >/dev/null; then
    logger info "Create database nitrate in MariaDB."
    mysql -uroot -e "CREATE DATABASE nitrate CHARACTER SET utf8mb4;"
fi

logger info "Add user $USER to group docker."
if ! grep "docker" /etc/group > /dev/null; then
    groupadd docker
fi
usermod -aG docker "$USER"
systemctl restart docker

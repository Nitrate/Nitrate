FROM registry.fedoraproject.org/fedora:31
LABEL maintainer="Chenxiong Qi <qcxhome@gmail.com>" \
      description="Test box for running Nitrate tests. This test box must work with a database image." \
      version="0.2"

# The image has Python 3.7 by default. So, python36 has to be installed explicitly.

RUN dnf update -y && \
    dnf install -y \
        --nogpgcheck \
        --setopt=deltarpm=0 \
        --setopt=install_weak_deps=false \
        --setopt=tsflags=nodocs \
        gcc redhat-rpm-config make mariadb python36 \
        python3-devel mariadb-devel postgresql-devel krb5-devel && \
    dnf clean all

# Container will have two virtual environments created with Python 3.6 and 3.7
# separately.
# Script running inside container is responsible for selecting the required
# environment by itself.

ADD VERSION.txt README.rst setup.py /code/

RUN mkdir /code/src && \
    python3.6 -m venv /testenv-py36 && \
    /testenv-py36/bin/python -m pip install --no-cache-dir --upgrade pip && \
    /testenv-py36/bin/python -m pip install --no-cache-dir -e \
        /code[tests,async,mysql,pgsql,docs,krbauth] && \
    python3.7 -m venv /testenv-py37 && \
    /testenv-py37/bin/python -m pip install --no-cache-dir --upgrade pip && \
    /testenv-py37/bin/python -m pip install --no-cache-dir -e \
        /code[tests,async,mysql,pgsql,docs,krbauth] && \
    rm -r /code

COPY contrib/travis-ci/entrypoint.sh /opt/test-entrypoint.sh
ENTRYPOINT "/opt/test-entrypoint.sh"

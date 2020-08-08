FROM registry.fedoraproject.org/fedora:32
LABEL maintainer="Chenxiong Qi <qcxhome@gmail.com>" \
      description="Test box for running Nitrate tests. This test box must work with a database image." \
      version="0.5"

ARG pypi_index=https://pypi.org/simple

# The image has Python 3.7 by default. So, python36 has to be installed explicitly.

RUN dnf update -y \
 && dnf install -y \
        --nogpgcheck \
        --setopt=deltarpm=0 \
        --setopt=install_weak_deps=false \
        --setopt=tsflags=nodocs \
        gcc redhat-rpm-config make mariadb postgresql python36 python37 \
        python3-devel mariadb-devel postgresql-devel krb5-devel libxcrypt-compat \
 && dnf clean all

# Container will have two virtual environments created with Python 3.6 and 3.7
# separately.
# Script running inside container is responsible for selecting the required
# environment by itself.

ADD VERSION.txt README.rst setup.py /code/

RUN mkdir /code/src \
 && PIP_INST=(python3 -m pip install --index-url $pypi_index --no-cache-dir) \
 && function make_venv { \
      python$1 -m venv /testenv-py$2; \
      source /testenv-py${2}/bin/activate; \
      ${PIP_INST[@]} --upgrade pip; \
      ${PIP_INST[@]} -e /code[tests,async,mysql,pgsql,docs,krbauth]; \
      deactivate; \
    } \
 && make_venv 3.6 36 \
 && make_venv 3.7 37 \
 && make_venv 3.8 38 \
 && rm -r /code

COPY contrib/travis-ci/entrypoint.sh /opt/test-entrypoint.sh
ENTRYPOINT "/opt/test-entrypoint.sh"

FROM registry.fedoraproject.org/fedora:29

LABEL maintainer="Chenxiong Qi <qcxhome@gmail.com>" \
      description="Test box for running Nitrate tests. This test box must work \
with a database image." \
      version="0.1"

# Use mysql provided by mariadb to connect MySQL server or MariaDB server.
RUN dnf install -y gcc redhat-rpm-config make mariadb mariadb-devel python36 python3-devel graphviz-devel && \
    dnf clean all

ADD . /code

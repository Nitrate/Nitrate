FROM registry.fedoraproject.org/fedora:32

LABEL maintainer="Chenxiong Qi <qcxhome@gmail.com>" \
      version="dev" \
      description="Nitrate development docker image built \
current branch, generally it is the develop branch." \
      io.github.nitrate.url="https://nitrate.readthedocs.io/" \
      io.github.nitrate.vcs-url="https://github.com/Nitrate/Nitrate"

ARG pypi_index=https://pypi.org/simple

RUN dnf update -y \
 && dnf install -y gcc redhat-rpm-config mariadb mariadb-devel python3 python3-devel graphviz-devel \
 && dnf clean all

ADD . /code

RUN rm -rf /code/.git \
 && python3 -m venv /devenv \
 && source /devenv/bin/activate \
 && python3 -m pip install -i $pypi_index --no-cache-dir -e /code[mysql,devtools,async,multiauth] \
 && deactivate

ADD docker/dev/entrypoint.sh /code/

# Nitrate will run by django's runserver command and listen on 8000.
EXPOSE 8000

# devel settings sets this directory to store uploaded files.
VOLUME ["/code/uploads"]

ENTRYPOINT "/code/entrypoint.sh"

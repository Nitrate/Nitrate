FROM registry.fedoraproject.org/fedora:28

LABEL maintainer="Chenxiong Qi <qcxhome@gmail.com>" \
      version="dev" \
      description="Nitrate development docker image built \
current branch, generally it is the develop branch." \
      io.github.nitrate.url="https://nitrate.readthedocs.io/" \
      io.github.nitrate.vcs-url="https://github.com/Nitrate/Nitrate"

RUN dnf update -y && \
    dnf install -y gcc redhat-rpm-config mariadb python3 python3-devel graphviz-devel && \
    dnf clean all

ADD . /code

RUN rm -rf /code/.git && \
    python3 -m venv /devenv && \
    /devenv/bin/pip install --no-cache-dir -e /code[mysql,devtools,async,multiauth]

ADD docker/dev/entrypoint.sh /code/

# Nitrate will run by django's runserver command and listen on 8000.
EXPOSE 8000

# devel settings sets this directory to store uploaded files.
VOLUME ["/code/uploads"]

CMD ["/code/entrypoint.sh"]

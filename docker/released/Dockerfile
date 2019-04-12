FROM registry.fedoraproject.org/fedora:28
ENV VCS_URL="https://github.com/Nitrate/Nitrate"
LABEL version="$VERSION" \
      maintainer="Chenxiong Qi <qcxhome@gmail.com>" \
      description="Run Nitrate from a Python virtual environment behind \
httpd. Authentication is not special. Common username and password \
authentication is used by default. A default superuser is created, both \
username and password are 'admin'." \
      io.github.nitrate.url="https://nitrate.readthedocs.io/" \
      io.github.nitrate.vcs-url="${VCS_URL}" \
      io.github.nitrate.issues-url="${VCS_URL}/issues/"

# install virtualenv and libraries needed to build the python dependencies
RUN dnf update -y && \
    dnf install -y --setopt=deltarpm=0 --setopt=install_weak_deps=false --setopt=tsflags=nodocs \
      gcc python3-devel graphviz-devel httpd mariadb python3-mod_wsgi mariadb-devel && \
    dnf clean all

WORKDIR /code
COPY . .

# Hack: easier to set database password via environment variable
COPY ./docker/released/product.py src/tcms/settings/product.py

# Create a virtualenv for the application dependencies
# Using --system-site-packages b/c Apache configuration
# expects the tcms directory to be there!
RUN python3 -m venv --system-site-packages /prodenv && /prodenv/bin/pip install --no-cache-dir .[mysql]

COPY ./contrib/conf/nitrate-httpd.conf /etc/httpd/conf.d/

# Just copying without renaming will cause error :
# AH00526: Syntax error on line 3 of /etc/httpd/conf.d/wsgi-venv.conf:
# Name duplicates previous WSGI daemon definition.
# However, if rename it with prefix "00-", it works well.
COPY ./contrib/conf/wsgi-venv.conf /etc/httpd/conf.d/00-wsgi-venv.conf

# Disable event module and enable prefork module
RUN sed -i -e 's/^#\(LoadModule mpm_prefork_module .\+\.so\)$/\1/' \
        /etc/httpd/conf.modules.d/00-mpm.conf && \
    sed -i -e 's/^\(LoadModule mpm_event_module .\+\.so\)$/#\1/' \
        /etc/httpd/conf.modules.d/00-mpm.conf

# Create and configure directory to hold uploaded files
RUN mkdir -p /var/nitrate/uploads && chown apache:apache /var/nitrate/uploads

# Install static files
RUN mkdir -p /usr/share/nitrate/static && \
    NITRATE_DB_ENGINE=sqlite /prodenv/bin/python src/manage.py collectstatic --settings=tcms.settings.product --noinput

# Install templates
RUN mkdir -p /usr/share/nitrate/templates && cp -r src/templates/* /usr/share/nitrate/templates/

# All the things are installed already. No need to keep source code inside.
# Don't worry, /code was set above as current working directory
RUN rm -rf *
EXPOSE 80
VOLUME ["/var/www", "/var/log/httpd", "/var/nitrate/uploads"]
CMD ["httpd", "-D", "FOREGROUND"]

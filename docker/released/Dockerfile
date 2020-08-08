FROM registry.fedoraproject.org/fedora:32
ARG version
ARG vcs_url="https://github.com/Nitrate/Nitrate"
LABEL version="${version}" \
      maintainer="Chenxiong Qi <qcxhome@gmail.com>" \
      description="Run Nitrate from a Python virtual environment behind \
httpd. Authentication is not special. Common username and password \
authentication is used by default. A default superuser is created, both \
username and password are 'admin'." \
      io.github.nitrate.url="https://nitrate.readthedocs.io/" \
      io.github.nitrate.vcs-url="${vcs_url}" \
      io.github.nitrate.issues-url="${vcs_url}/issues/"

# install virtualenv and libraries needed to build the python dependencies
RUN dnf update -y \
 && dnf install -y \
        --setopt=deltarpm=0 \
        --setopt=install_weak_deps=false \
        --setopt=tsflags=nodocs \
        dnf-utils \
 && dnf copr enable -y cqi/python-nitrate-tcms \
 && dnf install -y \
        --setopt=deltarpm=0 \
        --setopt=install_weak_deps=false \
        --setopt=tsflags=nodocs \
        httpd \
        python3-mod_wsgi \
        python3-nitrate-tcms \
 && dnf clean all

# Hack: easier to set database password via environment variable
COPY ./docker/released/product.py /usr/lib/python3.7/site-packages/tcms/settings/product.py

# Disable event module and enable prefork module
RUN sed -i -e 's/^#\(LoadModule mpm_prefork_module .\+\.so\)$/\1/' \
        /etc/httpd/conf.modules.d/00-mpm.conf \
 && sed -i -e 's/^\(LoadModule mpm_event_module .\+\.so\)$/#\1/' \
        /etc/httpd/conf.modules.d/00-mpm.conf

# Create and configure directory to hold uploaded files
RUN mkdir -p /var/nitrate/uploads \
 && chown apache:apache /var/nitrate/uploads

EXPOSE 80

VOLUME ["/var/log/httpd", "/var/nitrate/uploads"]

CMD ["httpd", "-D", "FOREGROUND"]

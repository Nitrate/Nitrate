FROM registry.fedoraproject.org/fedora:32

ARG version=latest
ARG vcs_url="https://github.com/Nitrate/Nitrate"
ARG build_latest=no

LABEL \
    name=Nitrate \
    license=GPLv2+ \
    version="${version}" \
    maintainer="Chenxiong Qi <qcxhome@gmail.com>" \
    vendor="" \
    io.github.nitrate.url="https://nitrate.readthedocs.io/" \
    io.github.nitrate.vcs-url="${vcs_url}" \
    io.github.nitrate.issues-url="${vcs_url}/issues/" \
    description="\
Nitrate is a new test plan, test run and test case management system, which is \
written in Python and Django (the Python web framework)."

RUN dnf --setopt=deltarpm=0 --setopt=install_weak_deps=false --nodocs \
        install -y dnf-utils httpd python3-mod_wsgi && \
    dnf copr enable -y cqi/python-nitrate-tcms && \
    if [[ "${build_latest}" == "yes" ]]; then \
        dnf copr enable -y cqi/python-nitrate-tcms-testing; \
    fi && \
    dnf --setopt=deltarpm=0 --setopt=install_weak_deps=false --nodocs \
        install -y python3-nitrate-tcms && \
    dnf copr remove -y cqi/python-nitrate-tcms && \
    if [[ "${build_latest}" == "yes" ]]; then \
        dnf copr remove -y cqi/python-nitrate-tcms-testing; \
    fi && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Disable event module and enable prefork module
RUN sed -i -e 's/^#\(LoadModule mpm_prefork_module .\+\.so\)$/\1/' \
        /etc/httpd/conf.modules.d/00-mpm.conf && \
    sed -i -e 's/^\(LoadModule mpm_event_module .\+\.so\)$/#\1/' \
        /etc/httpd/conf.modules.d/00-mpm.conf

# Create and configure directory to hold uploaded files
RUN mkdir -p /var/nitrate/uploads && \
    chown apache:apache /var/nitrate/uploads

# Directory holding customized settings module.
RUN mkdir /nitrate-config

VOLUME ["/var/log/httpd", "/var/nitrate/uploads", "/nitrate-config"]

# Prepare for running entrypoint script
RUN mkdir /bootstrap
ADD init.py entrypoint.sh /bootstrap/

ENV PYTHONPATH=/nitrate-config DJANGO_SETTINGS_MODULE=tcms.settings.product
EXPOSE 80
ENTRYPOINT "/bootstrap/entrypoint.sh"

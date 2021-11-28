%define debug_package %{nil}
%global codename nitrate
%global pypi_name %{codename}-tcms
%global egginfo_name %{codename}_tcms
%global mainpkg python3-%{pypi_name}

Name:           python-%{pypi_name}
Version:        4.12
Release:        1%{?dist}
Summary:        Test Case Management System

License:        GPLv2+
URL:            https://github.com/Nitrate/Nitrate/
Source0:        %{pypi_source}
BuildArch:      noarch

%description
Nitrate is a tool for tracking testing being done on a product.

It is a database-backed web application built on top of Django.


%package -n %{mainpkg}
Summary:        Test Case Management System

# required since f34
BuildRequires:  make

BuildRequires:  python3-devel
BuildRequires:  python3dist(setuptools)

BuildRequires:  python3-kobo-django
BuildRequires:  python3dist(beautifulsoup4)
BuildRequires:  python3dist(celery)
BuildRequires:  python3dist(django)
BuildRequires:  python3dist(django-contrib-comments)
BuildRequires:  python3dist(django-tinymce)
BuildRequires:  python3dist(django-uuslug)
BuildRequires:  python3dist(html2text)
BuildRequires:  python3dist(kerberos)
BuildRequires:  python3dist(odfpy)
BuildRequires:  python3dist(mysqlclient)
BuildRequires:  python3dist(python-bugzilla)
BuildRequires:  python3dist(xmltodict)

BuildRequires:  python3dist(factory-boy)
BuildRequires:  python3dist(pytest)
BuildRequires:  python3dist(pytest-cov)
BuildRequires:  python3dist(pytest-django)
BuildRequires:  python3dist(sphinx)
BuildRequires:  python3dist(sphinx-rtd-theme)
# Required by the Django SQL backend during tests run
BuildRequires:  python3dist(sqlparse)

Requires:       python3-kobo-django
Requires:       python3dist(beautifulsoup4)
Requires:       python3dist(django)
Requires:       python3dist(django-contrib-comments)
Requires:       python3dist(django-tinymce)
Requires:       python3dist(django-uuslug)
Requires:       python3dist(html2text)
Requires:       python3dist(odfpy)
Requires:       python3dist(xmltodict)


%{?python_provide:%python_provide python3-%{pypi_name}}

%description -n %{mainpkg}
Nitrate is a tool for tracking testing being done on a product.

It is a database-backed web application built on top of Django.


%package -n %{pypi_name}-doc
Summary:        Documentation of Nitrate

%description -n %{pypi_name}-doc
Documentation of Nitrate

%prep
%autosetup -n %{pypi_name}-%{version}
# Remove bundled egg-info
rm -rf %{egginfo_name}.egg-info

%check
DJANGO_SETTINGS_MODULE=tcms.settings.test PYTHONPATH=src/ \
%{pytest} src/tests/

%build
%py3_build

cd docs
make html
cd -

%install
%py3_install

data_dir=%{buildroot}%{_datadir}/nitrate
%{__mkdir_p} ${data_dir}

%{__mkdir} ${data_dir}/conf
%{__cp} contrib/conf/* ${data_dir}/conf

# Install templates files.
%{__mkdir} ${data_dir}/templates
%{__cp} -r src/templates/* ${data_dir}/templates

# Install static files.
%{__mkdir} ${data_dir}/static

echo "STATIC_ROOT = '${data_dir}/static'" >> src/tcms/settings/common.py

PYTHONPATH=src/ \
NITRATE_DB_ENGINE=sqlite \
NITRATE_SECRET_KEY=some-key \
%{__python3} src/manage.py collectstatic \
--settings=tcms.settings.product --noinput

%files -n python3-%{pypi_name}
%doc AUTHORS CHANGELOG.rst README.rst VERSION.txt
%license LICENSE
%{_datadir}/nitrate
%{python3_sitelib}/tcms/
%{python3_sitelib}/%{egginfo_name}-%{version}-py*.egg-info/

%files -n %{pypi_name}-doc
%doc docs/target/html
%license LICENSE

%package -n %{mainpkg}+mysql
Summary: Metapackage for %{mainpkg} to install dependencies.
Requires: %{mainpkg} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires: python3dist(mysqlclient)
%description -n %{mainpkg}+mysql
A metapackage for %{mainpkg} to install dependencies for running with MySQL or
MariaDB. No code is included.
%files -n %{mainpkg}+mysql
%ghost %{python3_sitelib}/%{egginfo_name}-%{version}-py*.egg-info/

%package -n %{mainpkg}+pgsql
Summary: Metapackage for %{mainpkg} to install dependencies.
Requires: %{mainpkg} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires: python3dist(psycopg2)
%description -n %{mainpkg}+pgsql
A metapackage for %{mainpkg} to install dependencies for running with
PostgreSQL. No code is included.
%files -n %{mainpkg}+pgsql
%ghost %{python3_sitelib}/%{egginfo_name}-%{version}-py*.egg-info/

%package -n %{mainpkg}+async
Summary: Metapackage for %{mainpkg} to install dependencies.
Requires: %{mainpkg} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires: python3dist(celery)
%description -n %{mainpkg}+async
A metapackage for %{mainpkg} to install dependencies for running asynchronous
tasks in Celery. No code is included.
%files -n %{mainpkg}+async
%ghost %{python3_sitelib}/%{egginfo_name}-%{version}-py*.egg-info/

%package -n %{mainpkg}+krbauth
Summary: Metapackage for %{mainpkg} to install dependencies.
Requires: %{mainpkg} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires: python3dist(kerberos)
%description -n %{mainpkg}+krbauth
A metapackage for %{mainpkg} to install dependencies for the authentication
backend based on Kerberos username and password. No code is included.
%files -n %{mainpkg}+krbauth
%ghost %{python3_sitelib}/%{egginfo_name}-%{version}-py*.egg-info/

%package -n %{mainpkg}+socialauth
Summary: Metapackage for %{mainpkg} to install dependencies.
Requires: %{mainpkg} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires: python3dist(social-auth-core)
Requires: python3dist(social-auth-app-django) >= 3.4.0
%description -n %{mainpkg}+socialauth
A metapackage for %{mainpkg} to install dependencies in order to leverage
various social-based authentications, e.g. Fedora account system (aka. FAS).
No code is included.
For detailed information, please refer to the package python-social-auth-core.
%files -n %{mainpkg}+socialauth
%ghost %{python3_sitelib}/%{egginfo_name}-%{version}-py*.egg-info/

%package -n %{mainpkg}+bugzilla
Summary: Metapackage for %{mainpkg} to install dependencies.
Requires: %{mainpkg} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires: python3dist(python-bugzilla)
%description -n %{mainpkg}+bugzilla
A metapackage for %{mainpkg} to install dependencies for the authentication
backend against a Bugzilla instance, or the issue tracker working with a remote
Bugzilla service. No code is included.
%files -n %{mainpkg}+bugzilla
%ghost %{python3_sitelib}/%{egginfo_name}-%{version}-py*.egg-info/

%changelog
* Sun Nov 28 2021 Chenxiong Qi <qcxhome@gmail.com> - 4.12-1
- Built for version 4.12

* Sun Mar 07 2021 Chenxiong Qi <qcxhome@gmail.com> - 4.11-1
- Built for version 4.11

* Thu Feb 11 2021 Chenxiong Qi <qcxhome@gmail.com> - 4.10-1
- Built for version 4.10

* Sun Dec 20 20:32:37 CST 2020 Chenxiong Qi <qcxhome@gmail.com> - 4.9.2-1
- Built for version 4.9.2

* Tue Dec 15 2020 Chenxiong Qi <qcxhome@gmail.com> - 4.9.1-1
- Built for version 4.9.1

* Sun Dec 13 2020 Chenxiong Qi <qcxhome@gmail.com> - 4.9-1
- Built for version 4.9

* Sun Aug 30 2020 Chenxiong Qi <qcxhome@gmail.com> - 4.8-1
- Built for version 4.8

* Sat Jun 27 2020 Chenxiong Qi <qcxhome@gmail.com> - 4.7.2-1
- Built for version 4.7.2

* Sat Jun 27 2020 Chenxiong Qi <qcxhome@gmail.com> - 4.7.1-1
- Built for version 4.7.1

* Sat Jun 27 2020 Chenxiong Qi <qcxhome@gmail.com> - 4.7-1
- Built for version 4.7

* Sat May 16 2020 Chenxiong Qi <qcxhome@gmail.com> - 4.6.1-1
- Built for version 4.6.1

* Sat May 16 2020 Chenxiong Qi <qcxhome@gmail.com> 4.6-1
- Built for version 4.6

* Fri Feb 16 2018 Chenxiong Qi <qcxhome@gmail.com> 4.0.0-2
- Clean up SPEC

* Thu Nov 23 2017 Chenxiong Qi <qcxhome@gmail.com> 4.0.0-1
- Upgrade django to 1.10.8
- Compatible with Python 3
- Update documentation
- Many fixes

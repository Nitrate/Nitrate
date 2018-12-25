.. _setup_devenv:

Setting up a development environment on Fedora
==============================================

Get source code
---------------

Nitrate source code is available at: https://github.com/Nitrate/Nitrate

You can get the latest changes with git easily::

    git clone https://github.com/Nitrate/Nitrate.git

Create virtualenv
-----------------

Install database and devel packages which are required to compile some of the
Python dependencies::

    sudo dnf install gcc python-devel mariadb mariadb-devel mariadb-server \
        krb5-devel libxml2-devel libxslt-devel

Start the db server::

    sudo systemctl start mariadb

Create a virtual environment::

    virtualenv ~/virtualenvs/nitrate

Install dependencies::

    . ~/virtualenvs/nitrate/bin/activate
    pip install -r requirements/devel.txt

.. note::

    ``devel.txt`` has the link to ``base.txt`` which includes required Python
    packages for running Nitrate.

Initialize database
-------------------

Create database::

    mysql -uroot
    create database nitrate character set utf8;

For convenience for development, user, password and database name are already
set in ``tcms/settings/devel.py`` with default value.

.. note::

    You may want to adjust the database and/or other configuration settings.
    Override them in ``./tcms/settings/devel.py`` if necessary. While MariaDB
    is supported currently, sqlite appears to work for development and some
    people have used PostgreSQL with varying success in production! At the
    moment Nitrate is not 100% portable between database backends due to some
    hard-coded SQL statements. If you use something other than MariaDB some
    parts of the application may not work correctly!

Load database schema and initial data::

    ./manage.py migrate

Final Step
----------

Nitrate is ready to run::

    ./manage.py runserver

Open http://127.0.0.1:8000/ and there should be brand new Nitrate homepage!

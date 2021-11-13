.. _setup_on_fedora:

==============================================
Setting up a development environment on Fedora
==============================================

This document describes the steps to set up a development environment by
creating and initializing a Python virtual environment. As an example,
Fedora 33 is used as the platform to develop Nitrate.

Get source code
---------------

Fork https://github.com/Nitrate/Nitrate to your own repository, then clone it
to your local system.

.. code-block:: shell

    git clone https://github.com/[your_github_name]/Nitrate.git

Create a virtual environment
----------------------------

Install database and devel packages. For development, SQLite is good enough as
a database backend, however this guide uses PostgreSQL to serve the database to
show more what Nitrate provides to help developers.

.. code-block:: shell

    sudo dnf install -y \
        python3 python3-devel python3-pip gcc postgresql-server \
        graphviz-devel krb5-devel postgresql-devel

Initialize the PostgreSQL database and start the server:

.. code-block:: shell

    sudo postgresql-setup --initdb
    sudo systemctl start postgresql

Create a virtual environment and install dependencies:

.. code-block:: shell

    cd path/to/code
    python3 -m venv .venv
    . .venv/bin/activate
    python3 -m pip install .[pgsql,krbauth,docs,tests,devtools,async,bugzilla,socialauth]

Initialize database
-------------------

Add this line to ``/var/lib/pgsql/data/pg_hba.conf``::

   local    all     all     trust

.. note::

   How the local PostgreSQL server instance is configured depends on how you
   want the Nitrate to connect to the server. Above line is just an example
   FYI. In practice, you are free to change it any value to fulfill your
   requirement.

   Note that, once you change it, please remember to also change the default
   values to ``NITRATE_DB_*`` environment variables accordingly. Refer to the
   Makefile target ``db_envs`` or the output from ``DB=pgsql make db_envs``.

Create database:

.. code-block:: shell

   psql -U postgres -c "create database nitrate"

Migrate database:

.. code-block:: shell

   . .venv/bin/activate
   eval "$(DB=pgsql make db_envs)"
   make migrate

Final Step
----------

.. code-block:: shell

   . .venv/bin/activate
   eval "$(DB=pgsql make db_envs)"

Before running the server, you may need to create a superuser in order to
manage the site during development:

.. code-block:: shell

   make createsuperuser

As of now, it is ready to run Nitrate:

.. code-block:: shell

   make runserver

Open http://127.0.0.1:8000/ and there should be brand new Nitrate homepage!

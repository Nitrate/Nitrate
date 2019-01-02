Running Nitrate as a Docker container
=====================================

Build Docker image
------------------

You can build a Docker image of Nitrate by running::

    make release-image

This will create a Docker image based on base image
``registry.fedoraproject.org/fedora:28`` from released version. By
default the image tag will be ``nitrate/nitrate:<release version>``.


Create Docker container
-----------------------

You can then start using Nitrate by executing::

    docker-compose -f docker-compose-venv.yml up -d

This will create two containers:

1) A web container based on the latest Nitrate image
2) A DB container based on the official mariadb image


``docker-compose`` will also create two volumes for persistent data storage:
``nitrate_db_data`` and ``nitrate_uploads``.


Initial configuration of running container
------------------------------------------

Nitrate development image has an entrypoint which tries to do database
migrations and create a superuser for initial use. However, you are
free to do it for yourself by executing::

    docker exec -it nitrate_web_1 /Nitrate/manage.py migrate
    docker exec -it nitrate_web_1 /Nitrate/manage.py createsuperuser


Upgrading
---------

To upgrade running Nitrate containers execute the following commands::

    git pull
    make dev-image
    docker-compose stop
    docker rm nitrate_web_1 nitrate_db_1
    docker-compose -f docker-compose-dev.yml up -d
    docker exec -it nitrate_web_1 /Nitrate/manage.py migrate

.. note::

    Uploads and database data should stay intact because they are split into
    separate volumes, which makes upgrading very easy. However you may want to
    back these up before upgrading!

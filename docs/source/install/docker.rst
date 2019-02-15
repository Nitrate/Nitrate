.. _running_in_container:

Running Nitrate as a Docker container
=====================================

Build Docker image
------------------

You can build a Docker image of Nitrate by running::

    make release-image

This will create a Docker image based on base image
``registry.fedoraproject.org/fedora:28`` from released version. By
default the image tag will be ``nitrate/nitrate:<release version>``.


Run Nitrate inside Container
----------------------------

You have two choices to run Nitrate inside container. One way is to use
`docker-compose`_::

    docker-compose -f docker-compose.yml up

Then, visit http://127.0.0.1:8001/

This will create two containers:

* A web container based on the specific version of Nitrate image specified in
  ``docker-compose.yml``.

* A MariaDB database container.

``docker-compose`` will also create two volumes for persistent data storage.
Refer to ``docker-compose.yml`` for available volumes.

Please note that, this requires you to have a copy (probable cloned from git
repository) of Nitrate source code. It is recommended for you to deploy Nitrate
into a container environment, e.g. OpenShift. This is the second way you should
choose for running Nitrate in production.

.. _docker-compose: https://docs.docker.com/compose/


Initial configuration of running container
------------------------------------------

Nitrate development image has an entrypoint which tries to do database
migrations and create a superuser for initial use. However, you are
free to do it for yourself by executing:

.. code-block:: shell

   # Do database migrations
   docker exec -it --env DJANGO_SETTINGS_MODULE=tcms.settings.product \
       nitrate_web_1 /prodenv/bin/django-admin migrate

   # Create a superuser in order to manage site
   docker exec -it --env DJANGO_SETTINGS_MODULE=tcms.settings.product \
       nitrate_web_1 /prodenv/bin/django-admin createsuperuser

   # Set permissions to default groups
   docker exec -it --env DJANGO_SETTINGS_MODULE=tcms.settings.product \
       nitrate_web_1 /prodenv/bin/django-admin setdefaultperms


Upgrading
---------

There should be no difference to update docker image. Each time when you run a
newer version of Nitrate, please ensure read the release notes to know what
must be done for upgrade.

Generally, running database migrations is a common task for upgrade. This can
be done inside the container:

.. code-block:: shell

   docker exec -it --env DJANGO_SETTINGS_MODULE=tcms.settings.product \
       nitrate_web_1 /prodenv/bin/django-admin migrate

.. note::

    Uploads and database data should stay intact because they are split into
    separate volumes, which makes upgrading very easy. However you may want to
    back these up before upgrading!

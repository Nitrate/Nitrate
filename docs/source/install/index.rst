.. _deployment:

==========
Deployment
==========

Get Nitrate
-----------

Nitrate ships with optional subpackages in addition to the main nitrate-tcms
package. They are available from either PyPI or the YUM repository. The
subpackages include:

* ``mysql``: needed when Nitrate works with MySQL or MariaDB database.

* ``pgsql``: needed when Nitrate works with PostgreSQL database.

* ``bugzilla``: needed when the ``BugzillaBackend`` authentication backend is
  enabled, or the issue tracker is configured to work with a Bugzilla
  instance.

* ``krbauth``: needed when the ``KerberosBackend`` authentication backend is
  enabled.

* ``socialauth``: needed when the social-based authentication backend is
  enabled.

* ``async``: needed when to run asynchronous tasks as Celery tasks.

PyPI
~~~~

.. code-block:: shell

  python3 -m pip install nitrate-tcms

  # Example: if Kerberos-based authentication is required
  python3 -m pip install nitrate-tcms[krbauth]

RPM
~~~

RPM packages are provided from a `Copr repository`_:

.. code-block:: shell

  sudo dnf copr enable cqi/python-nitrate-tcms
  sudo dnf install python3-nitrate-tcms

  # Example: if Celery is required and run with PostgreSQL
  sudo dnf install python3-nitrate-tcms+async python3-nitrate-tcms+pgsql

.. _Copr repository: https://copr.fedorainfracloud.org/coprs/cqi/python-nitrate-tcms/

Container Images
~~~~~~~~~~~~~~~~

Nitrate provides two container images:

* `quay.io/nitrate/nitrate`_

* `quay.io/nitrate/nitrate-worker`_

The ``nitrate-worker`` image is optional, that depends no whether there is
requirement to run asynchronous tasks by Celery.

For more information, please refer to the description of image
``quay.io/nitrate/nitrate``.

.. _quay.io/nitrate/nitrate: https://quay.io/repository/nitrate/nitrate
.. _quay.io/nitrate/nitrate-worker: https://quay.io/repository/nitrate/nitrate-worker

In this document, you are able to find out several ways to run Nitrate for your
use case.

Run locally
-----------

The Vagrant Way
~~~~~~~~~~~~~~~

Before you launch the VM, please ensure `Vagrant`_ and `VirtualBox`_ is
installed. A vagrant file ``Vagrantfile.example`` is ready-to-use, and it is
configured to work with ``virtualbox`` provider. If you are using other
virtualization technology, e.g. libvirt, it is possible to edit a copy from the
default file. Following these steps:

* Copy ``contrib/Vagrantfile.example`` to project root directory and rename it
  to ``Vagrantfile``.

* ``vagrant up``

.. _Vagrant: https://www.vagrantup.com/
.. _VirtualBox: https://www.virtualbox.org/

Run inside Container
~~~~~~~~~~~~~~~~~~~~

Deploy a released version
^^^^^^^^^^^^^^^^^^^^^^^^^

Each released version has a docker image which is available in Quay.io.
Essentially, you could get a specific version of Nitrate by ``podman pull``,
for example to get version ``4.4`` image:

.. code-block:: shell

    podman pull quay.io/nitrate/nitrate:4.4

To deploy a Nitrate image, you need an orchestration tool to organize Nitrate
image and database image and volumes to store data.

For running a specific version quickly in local system, you could run:

.. code-block:: shell

    IMAGE_VERSION=4.4 podman-compose up

Run a development instance locally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Simply run:

.. code-block:: shell

    podman-compose up

Then, visit URL http://127.0.0.1:8001/

Installation Guides
-------------------

Here are a few of various installation documents. Choose one for your
environment. Feel free to report issue if you find out anything that does not
work.

.. warning::
   These documentation were contributed by contributors in the past. Some of
   them might be out-dated. Please read them and apply the steps carefully.
   Welcome patches to update these documents.

.. toctree::
   :maxdepth: 1

   gce
   gunicorn
   in_rhel
   in_virtualenv
   docker

.. _how_to_run:

How to Run
==========

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
Essentially, you could get a specific version of Nitrate by ``docker pull``,
for example to get version ``4.4`` image::

    docker pull quay.io/nitrate/nitrate:4.4

To deploy a Nitrate image, you need an orchestration tool to organize Nitrate
image and database image and volumes to store data.

For running a specific version quickly in local system, you could run::

    IMAGE_VERSION=4.4 docker-compose up

Run a development instance locally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Running inside container requires ``docker-compose`` and ``docker`` to be
installed firstly. Then, simply run::

    docker-compose -f docker-compose-dev.yml up

Then, visit URL http://127.0.0.1:8000/

Installation Guides
-------------------

Here are a few of various installation documents. Choose one for your
environment. Feel free to report issue if you find out anything that does not
work.

.. toctree::
   :maxdepth: 1

   gce
   gunicorn
   in_rhel
   in_virtualenv
   docker

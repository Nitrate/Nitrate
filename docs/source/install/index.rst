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

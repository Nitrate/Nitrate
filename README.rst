Nitrate - Test Case Management System
=====================================

.. image:: https://img.shields.io/pypi/v/nitrate-tcms
   :alt: PyPI
   :target: https://pypi.python.org/pypi/nitrate-tcms
.. image:: https://img.shields.io/pypi/pyversions/nitrate-tcms
   :alt: Python Versions
   :target: https://pypi.python.org/pypi/nitrate-tcms
.. image:: https://img.shields.io/pypi/djversions/nitrate-tcms?label=django
   :alt: Django Versions
   :target: https://pypi.python.org/pypi/nitrate-tcms
.. image:: https://quay.io/repository/nitrate/nitrate/status
   :target: https://quay.io/repository/nitrate/nitrate/
.. image::  https://readthedocs.org/projects/nitrate/badge/?version=latest
   :target: http://nitrate.readthedocs.io/en/latest/
.. image:: https://img.shields.io/pypi/l/nitrate-tcms
   :alt: PyPI - License
   :target: https://pypi.org/project/nitrate-tcms/
.. image:: https://img.shields.io/github/issues-raw/Nitrate/Nitrate
   :alt: GitHub issues
   :target: https://github.com/Nitrate/Nitrate/issues/
.. image:: https://img.shields.io/github/workflow/status/Nitrate/Nitrate/Unit%20Tests
   :alt: GitHub Workflow Status
   :target: https://github.com/Nitrate/Nitrate/
.. image:: https://coveralls.io/repos/github/Nitrate/Nitrate/badge.svg?branch=develop
   :target: https://coveralls.io/github/Nitrate/Nitrate?branch=develop
.. image:: https://copr.fedorainfracloud.org/coprs/cqi/python-nitrate-tcms/package/python-nitrate-tcms/status_image/last_build.png
   :alt: Package in Fedora Copr
   :target: https://copr.fedorainfracloud.org/coprs/cqi/python-nitrate-tcms/

Nitrate is a new test plan, test run and test case management system,
which is written in `Python`_ and `Django`_ (the Python web framework).
It has a lot of great features, such as:

* Ease of use in creating and managing test life cycles with plans,
  cases and runs.
* Multiple and configurable authentication backends, e.g.
  Bugzilla and Kerberos.
* Fast search for plans, cases and runs.
* Powerful access control for each plan, run and case.
* Ready-to-use and extensible issue tracker that allows to track external
  issues with test cases and test case runs.
* Accessibility with regards to XMLRPC APIs.

Nitrate works with:

* Python: ``3.9``, ``3.10``.
* Django: ``3.2``.

What's more, Nitrate is tested with the following database versions in the
testenv:

* MariaDB: ``10.4.14``.
* MySQL: ``8.0.22``.
* PostgreSQL: ``12.4``.

.. _Python: https://www.python.org/
.. _Django: https://docs.djangoproject.com/

Brief History
-------------

Nitrate was created by Red Hat originally back to the year 2009. A small group
of engineers, who were working at Red Hat (Beijing), initiated the project to
develop a Django-based test case management system being compatible with the
Testopia from database level. After that, more engineers got involved into the
development. TCMS is the project name, and Nitrate is the code name which has
been being used as the name in open source community all the time to this day.

The project was hosted in fedorahosted.org at the very early age to build the
community. The site had various artifacts of Nitrate, including the source
code, kinds of development and project management documentations, roadmaps,
mailing list, etc. The source code was managed by SVN in the beginning. Along
with more contributors started to contribute to Nitrate, the team decided to
migrate to Git eventually.

Since 2009, there were three major version releases, that were version 1.0
released in October 2009, version 2.0 released in January 2010, and version
3.0 released in April 2010. After version 3.0, the team had been adding new
features, fixing bugs, improving performance and user experience continuously
in a series of minor releases. As of year 2014, Nitrate was open sourced to
community and hosted in GitHub based on the version 3.18, and new journey had
began.

Up to this day, at the moment of writing this brief history review, Nitrate
has been 11 years old and it still has strong vitality.

Get Nitrate
-----------

Nitrate ships with optional subpackages in addition to the main nitrate-tcms
package. They are available from PyPI. The subpackages include:

* ``mysql``: needed when Nitrate works with MySQL or MariaDB database.
* ``pgsql``: needed when Nitrate works with PostgreSQL database.
* ``bugzilla``: needed when the ``BugzillaBackend`` authentication backend is
  enabled, or the issue tracker is configured to work with a Bugzilla
  instance.
* ``krbauth``: needed when the ``KerberosBackend`` authentication backend is
  enabled.
* ``socialauth``: needed when the social-based authentication backend
  is enabled.
* ``async``: needed when to run asynchronous tasks as Celery tasks.

Example of installation from PyPI::

  python3 -m pip install nitrate-tcms
  # To enable Kerberos-based authentication and asynchronous task in Celery
  python3 -m pip install nitrate-tcms[krbauth,async]

Container Images
~~~~~~~~~~~~~~~~

Nitrate provides three pre-built container images that can run in the
cloud or a local container environment.

Generally, you should require ``quay.io/nitrate/web`` and
``quay.io/nitrate/worker``. ``quay.io/nitrate/base`` is the base image
used to build web and worker image, which should not be used directly
in most cases unless you would like to build a custom image base on
it.

The worker image is optional if there is no requirement to run
asynchronous tasks by Celery.

For more information, please refer to `Nitrate/containers`_

.. _Nitrate/containers: https://github.com/Nitrate/containers

Run Nitrate
-----------

A quick way to run Nitrate from the latest container image:

    podman-compose -f container-compose.yml up

There are a series of instructions for running Nitrate. Please refer to
`Deployment`_.

Skim through the documentation and choose the installation instructions
that are appropriate for your case. And please, if you identify any issues
with the installation guide, kindly bring it to our attention. You can either
report the issue on the github repo, or submit a PR with a fix for it.

.. _Deployment: https://nitrate.readthedocs.io/en/latest/install/index.html

Documentation
-------------

For full documentation, including user guide, deployment, development guide and
APIs, please refer to https://nitrate.readthedocs.org/.

Contribution
------------

Welcome contributions in various fields. The `Contribution`_ document describes
those fields in more details.

.. _Contribution: https://nitrate.readthedocs.io/en/latest/contribution.html

Write Code
----------

If you would like to write some code, the `Development`_ document is the right
place for you to get reference and started.

.. _Development: https://nitrate.readthedocs.io/en/latest/contribution.html#development

Report Issues
-------------

If you've stumbled upon an issue in Nitrate, please refer to `Report an Issue`_
to create one `here`_.

.. _here: https://github.com/Nitrate/Nitrate/issues/new
.. _Report an Issue: http://nitrate.readthedocs.org/en/latest/bug_reporting.html

Contact
-------

There are various ways to get in touch. Choose one you like.

* Mailing List: `nitrate-devel at lists.fedorahosted.org`_
* IRC: nitrate-tcms on `irc.libera.chat`_

.. _nitrate-devel at lists.fedorahosted.org: mailto:nitrate-devel@lists.fedorahosted.org
.. _irc.libera.chat: https://web.libera.chat/

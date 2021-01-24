Nitrate - Test Case Management System
=====================================

.. image:: https://img.shields.io/pypi/v/nitrate-tcms
   :alt: PyPI
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
.. image:: https://badges.gitter.im/Nitrate/Nitrate.svg
   :alt: Gitter
   :target: https://gitter.im/Nitrate/Nitrate?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge
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

* Python: ``3.6``, ``3.7``, ``3.8``, ``3.9``.
* Django: ``2.2``, ``3.0``, ``3.1``.

What's more, Nitrate is tested with the following database versions:

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
community. The site had vaiours artifacts of Nitrate, including the source
code, kinds of development and project management documentations, roadmaps,
mailing list, etc. The source code was managed by SVN in the beginning. Along
with more contributors started to contribute to Nitrate, the team decided to
migrate to Git eventually.

Since 2009, there were three major version releases, that were version 1.0
released in October 2009, version 2.0 released in January 2010, and version
3.0 released in April 2010. After version 3.0, the team had been adding new
features, fixing bugs, improving performance and user experience continously
in a series of minor releases. As of year 2014, Nitrate was open sourced to
community and hosted in GitHub based on the version 3.18, and new journey had
began.

Up to this day, at the moment of writing this brief history review, Nitrate
has been 11 years old and it still has strong vitality.

How to run
----------

There are a series of instructions for installing Nitrate in the
`The Deployment Guide`_.

Skim through the documentation and choose the installation instructions
that are appropriate for your case. And please, if you identify any issues
with the installation guide, kindly bring it to our attention. You can either
report the issue on the github repo, or submit a PR with a fix for it.

Documentation
-------------

For full documentation, including user guide, deployment, development guide and
APIs, please refer to https://nitrate.readthedocs.org/.

Contribution
------------

Any kind of contribution is highly welcome and welcome, whether to the
documentation or the source code itself. We also greatly appreciate
contributions in the form of ideas to make Nitrate better.

Please refer to `The Development Guide`_ for more information on how to contribute.

.. _The Development Guide: https://nitrate.readthedocs.io/en/latest/index.html#the-development-guide

Contributing Code
-----------------

If you would like to write some code, the Vagrant machine would be a
good choice for you to setup a development environment quickly, where you
can run tests and debug issues.

Please refer to the `The Deployment Guide`_ for more information on
how to run locally, the Vagrant way.

.. _The Deployment Guide: https://nitrate.readthedocs.io/en/latest/index.html#the-deployment-guide

Bug Reports
-----------

If you've stumbled upon a bug in Nitrate, you can create an issue for that bug
`here`_.

However, before creating the issue, please refer to `Report an Issue`_
for details on how to report a bug in Nitrate.

.. _here: https://github.com/Nitrate/Nitrate/issues/new
.. _Report an Issue: http://nitrate.readthedocs.org/en/latest/bug_reporting.html

Contact
-------

There are various ways to get in touch. Choose one you like.

* Mailing List: `nitrate-devel at lists.fedorahosted.org`_
* IRC: `nitrate`_ on irc.freenode.org
* Gitter: https://gitter.im/Nitrate/Nitrate

.. _nitrate-devel at lists.fedorahosted.org: mailto:nitrate-devel@lists.fedorahosted.org
.. _nitrate: irc://irc.freenode.org/nitrate

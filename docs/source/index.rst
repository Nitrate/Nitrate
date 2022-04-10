.. nitrate documentation master file, created by
   sphinx-quickstart on Tue Nov 26 22:58:55 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====================================
Nitrate - Test Case Management System
=====================================

.. image:: https://img.shields.io/pypi/v/nitrate-tcms
   :alt: PyPI
   :target: https://pypi.python.org/pypi/nitrate-tcms

.. image:: https://img.shields.io/pypi/dm/nitrate-tcms
   :alt: PyPI - Downloads

.. image:: https://quay.io/repository/nitrate/nitrate/status
   :target: https://quay.io/repository/nitrate/nitrate/

.. image::  https://readthedocs.org/projects/nitrate/badge/?version=latest
   :target: http://nitrate.readthedocs.io/en/latest/

.. image:: https://img.shields.io/pypi/l/nitrate-tcms
   :alt: PyPI - License

.. image:: https://img.shields.io/github/issues-raw/Nitrate/Nitrate
   :alt: GitHub issues
   :target: https://github.com/Nitrate/Nitrate/issues/

.. image:: https://travis-ci.org/Nitrate/Nitrate.svg?branch=develop
   :target: https://travis-ci.org/Nitrate/Nitrate

.. image:: https://coveralls.io/repos/github/Nitrate/Nitrate/badge.svg?branch=develop
   :target: https://coveralls.io/github/Nitrate/Nitrate?branch=develop

.. image:: https://badges.gitter.im/Nitrate/Nitrate.svg
   :alt: Gitter
   :target: https://gitter.im/Nitrate/Nitrate?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge

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

* Python: ``3.6`` and ``3.7``.
* Django: ``3.2``.

What's more, Nitrate is tested with the following database versions:

* MariaDB: ``10.4.12``.
* MySQL: ``8.0.20``.
* PostgreSQL: ``12.2``.

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

Useful Links
------------

* `Container Images <https://quay.io/repository/nitrate/nitrate>`_
* `Issue Tracker <https://github.com/Nitrate/Nitrate/issues/>`_
* `Nitrate @ GitHub <https://github.com/Nitrate/Nitrate>`_
* `Nitrate @ PyPI <https://pypi.python.org/pypi/nitrate-tcms>`_
* `Talk @ Gitter <https://gitter.im/Nitrate/Nitrate>`_
* `Nitrate @ Gitee <https://gitee.com/Nitrate/Nitrate>`_: A mirror repo of GitHub. GitHub的镜像，定期更新。

Contact
-------

* Mailing list: nitrate-devel@lists.fedorahosted.org
* IRC: #nitrate at freenode.net
* Gitter: https://gitter.im/Nitrate/Nitrate

Table of Content
----------------

.. toctree::
   :maxdepth: 2

   license
   authors
   report_issue
   contribution
   install/index
   configuration
   api/index
   releases/index

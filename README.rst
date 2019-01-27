Nitrate - Test Case Management System
=====================================

.. image:: https://travis-ci.org/Nitrate/Nitrate.svg?branch=develop
    :target: https://travis-ci.org/Nitrate/Nitrate

.. image:: https://coveralls.io/repos/github/Nitrate/Nitrate/badge.svg?branch=develop
   :target: https://coveralls.io/github/Nitrate/Nitrate?branch=develop

.. image::  https://readthedocs.org/projects/nitrate/badge/?version=latest
   :target: http://nitrate.readthedocs.io/en/latest/


Nitrate is a new test plan, test run and test case management system, which is
written in `Python`_ and `Django`_ web framework. It has a lot of great features,
such as:

* Easy to use to create and manage testing life cycle with plans, cases and runs.
* Multiple and configurable authentication backend, e.g. Bugzilla and Kerberos.
* Fast search for plans, cases and runs.
* powerful access control for each plan, run and case
* Ready-to-use and extensible issue tracker that allows to track external issues
  with test cases and test case runs.
* Accessible with XMLRPC APIs.

Nitrate works with:

* Python: ``2.7``, ``3.6`` and ``3.7``.
* Django: ``1.11``, ``2.0`` and ``2.1``.
* Following database versions are tested with:

  * MariaDB: ``10.2.21``.
  * MySQL: ``5.7``.
  * PostgreSQL: ``10.6``.

Python 3 is strongly recommended.

.. _Python: https://www.python.org/
.. _Django: https://docs.djangoproject.com/

Dependencies
------------

Dependencies are listed in ``setup.py``. ``requirements.txt`` file is also
provided for provision a local virtualenv for a consistent development
environment.

Documentation
-------------

http://nitrate.readthedocs.org/

Installation
------------

There are a series of documentation for installing Nitrate in
`Installation Guide`_. Choose one for your case. It is appreciated to catch any
issues of the documentation, report it or fix it.

.. _Installation Guide: https://nitrate.readthedocs.io/en/latest/install/index.html

Contribution
------------

Any kind of contribution is welcome, whatever to the documentation, code or
even just ideas to make Nitrate better. Please refer to Contribution_ for more
information on how to contribute.

If you would like to write some code, the ``conf/Vagrantfile.example`` would be
a good choice for you to setup a development environment quickly, where you can
run tests and debug issues. What you need to do is:

* First, please ensure ``vagrant`` is installed and usable.

* Copy ``conf/Vagrantfile.example`` to project root directory and name it
  ``Vagrantfile``.

* ``vagrant up``.

.. _Contribution: http://nitrate.readthedocs.org/en/latest/contribution.html

Bug Reports
-----------

File an issue `here`_.

Refer to `File a New Bug Report`_ for details to report an issue.

.. _here: https://github.com/Nitrate/Nitrate/issues/new
.. _File a New Bug Report: http://nitrate.readthedocs.org/en/latest/bug_reporting.html

Contact
-------

* Mailing List: `nitrate-devel at lists.fedorahosted.org`_
* IRC: `#nitrate on irc.freenode.org`_

.. _nitrate-devel at lists.fedorahosted.org: mailto:nitrate-devel@lists.fedorahosted.org
.. _#nitrate on irc.freenode.org: irc://irc.freenode.org/nitrate

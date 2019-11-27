Nitrate - Test Case Management System
=====================================

.. image:: https://travis-ci.org/Nitrate/Nitrate.svg?branch=develop
    :target: https://travis-ci.org/Nitrate/Nitrate

.. image:: https://coveralls.io/repos/github/Nitrate/Nitrate/badge.svg?branch=develop
   :target: https://coveralls.io/github/Nitrate/Nitrate?branch=develop

.. image::  https://readthedocs.org/projects/nitrate/badge/?version=latest
   :target: http://nitrate.readthedocs.io/en/latest/

.. image:: https://quay.io/repository/nitrate/nitrate/status
   :target: https://quay.io/repository/nitrate/nitrate/

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
* Django: ``2.x``.

What's more, Nitrate is tested with the following database versions:

* MariaDB: ``10.2.21``.
* MySQL: ``5.7``.
* PostgreSQL: ``10.6``.

.. _Python: https://www.python.org/
.. _Django: https://docs.djangoproject.com/

Dependencies
------------

The dependencies required by Nitrate are listed in ``setup.py``.

A ``requirements.txt`` file is also provided to help setup and maintain a
consistent virtual environment for development.

Documentation
-------------

http://nitrate.readthedocs.org/

How to run
----------

There are a series of instructions for installing Nitrate in the
`Installation Guide`_.

Skim through the documentation and choose the installation instructions
that are appropriate for your case. And please, if you identify any issues
with the installation guide, kindly bring it to our attention. You can either
report the issue on the github repo, or submit a PR with a fix for it.

.. _Installation Guide: https://nitrate.readthedocs.io/en/latest/install/index.html

Contribution
------------

Any kind of contribution is highly welcome and welcome, whether to the
documentation or the source code itself. We also greatly appreciate
contributions in the form of ideas to make Nitrate better.

Please refer to Contribution_ for more information on how to contribute.

Contributing Code
-----------------

If you would like to write some code, the Vagrant machine would be a
good choice for you to setup a development environment quickly, where you
can run tests and debug issues.

Please refer to the `Installation Guide`_ for more information on
how to run locally, the Vagrant way.

Bug Reports
-----------

If you've stumbled upon a bug in Nitrate, you can create an issue for that bug
`here`_.

However, before creating the issue, please refer to `File a New Bug Report`_
for details on how to report a bug in Nitrate.

.. _here: https://github.com/Nitrate/Nitrate/issues/new
.. _File a New Bug Report: http://nitrate.readthedocs.org/en/latest/bug_reporting.html

Contact
-------

* Mailing List: `nitrate-devel at lists.fedorahosted.org`_
* IRC: `#nitrate on irc.freenode.org`_

.. _nitrate-devel at lists.fedorahosted.org: mailto:nitrate-devel@lists.fedorahosted.org
.. _#nitrate on irc.freenode.org: irc://irc.freenode.org/nitrate

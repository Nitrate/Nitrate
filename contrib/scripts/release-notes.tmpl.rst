.. _{doc_ref}:

{title_marker}
{new_version}
{title_marker}

*{release_date}*

I’m pleased to announce a new release {new_version} is available now.

Highlights
==========

Bugfixes
--------

.. todo::

Distribution
------------

.. todo::

Dependencies
------------

.. todo::

Infrastructure Improvements
---------------------------

.. todo::

Get Nitrate
===========

From PyPI
---------

.. code-block:: shell

   python3 -m pip install nitrate-tcms

Container Images
----------------

* ``quay.io/nitrate/nitrate:{new_version}``: the main image including Nitrate Web
  application.

* ``quay.io/nitrate/nitrate-worker:{new_version}``: an optional worker image if the
  asynchronous tasks scheduled and run by Celery are required.

Refer to :ref:`deployment` for detailed information.

Database Migration
==================

.. todo::

Change Logs
===========

{change_logs}

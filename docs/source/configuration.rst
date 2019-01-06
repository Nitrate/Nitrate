.. _configuration:

Configuration
=============

Default Permissions
-------------------

There are three groups created after ``migrate``, which are ``Tester``,
``System Admin`` and ``Administrator``. Nitrate provides a script to set
permissions for these default groups in order to be ready-for-use out of
box. Run script, for example with production settings module:

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=tcms.settings.product
    python /path/to/nitrate/contrib/scripts/default-permissions.py

Settings
--------

Asynchronous Task
~~~~~~~~~~~~~~~~~

ASYNC_TASK
^^^^^^^^^^

By default, Nitrate runs registered tasks in a synchronous way. It would be
good for development, running tests, or even in a deployed server at most
cases. On the other hand, Nitrate also allows to run tasks in asynchronous way.
There are three choices for ``ASYNC_TASK``:

* ``DISABLED``: run tasks in synchronous way. This is the default.

* ``THREADING``: run tasks in a separate thread using Python ``threading``
  module. The created thread for tasks is set to run in daemon mode by setting
  ``Thread.daemon`` to True.

* ``CELERY``: Nitrate works with Celery together to run tasks. Tasks are
  scheduled in a queue and configured Celery workers will handle those
  separately.

Celery settings
^^^^^^^^^^^^^^^

Nitrate has a group of Celery settings in ``common`` settings module. Each of
them could be changed according to requirement of concrete environment. Any
other necessary Celery settings can be set in settings module as well.

* ``CELERY_BROKER_URL``
* ``CELERY_TASK_RESULT_EXPIRES``
* ``CELERY_RESULT_BACKEND``
* ``CELERYD_TIMER_PRECISION``
* ``CELERY_IGNORE_RESULT``
* ``CELERY_MAX_CACHED_RESULTS``
* ``CELERY_DEFAULT_RATE_LIMIT``

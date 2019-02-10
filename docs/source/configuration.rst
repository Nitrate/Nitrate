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

    python path/to/manage.py --settings=tcms.settings.product setdefaultperms

If running Nitrate during development, just omit ``--settings`` option as
``tcms.settings.devel`` is already set in ``manage.py``.

Multiple authentication backends
--------------------------------

Nitrate supports to enable multiple authentication backends via config in
settings module.

Nitrate provides a few builtin authentication backends.

BugzillaBackend
~~~~~~~~~~~~~~~

``BugzillaBackend`` allows to verify username and password by a configured
remote Bugzilla instance. Setting ``BUGZILLA_XMLRPC_URL`` to a valid XMLRPC
URL. After logging into the remote Bugzilla instance successfully, Nitrate
ensures to logout so that no user-specific session remains in server.

KerberosBackend
~~~~~~~~~~~~~~~

``KerberosBackend`` checks username and password with KDC. Two things have to
be configured properly.

* ``krb5.conf`` must be configured with valid KDC hostnames.
* ``KRB5_REALM`` in settings must have valid realm in the KDC.

ModAuthKerbBackend
~~~~~~~~~~~~~~~~~~

``ModAuthKerbBackend`` works with any frontend Web servers that is delegated to
complete the actual Kerberos authentication in the negotiation way, that is the
`Simple and Protected GSSAPI Negotiation Mechanism (SPNEGO)`_.
``ModAuthKerbBackend`` actually does not do anything to authenticate user who
is trying to login. Instead, user is treated as authenticated as long as he or
she passes the authentication by Web server.

.. hint::

   If Apache web server is used to serve Nitrate, it is recommended to enable
   `mod_auth_gssapi`_ for SPNEGO. Refer to its `README`_ for details.

.. _Simple and Protected GSSAPI Negotiation Mechanism (SPNEGO): https://en.wikipedia.org/wiki/SPNEGO
.. _README: https://github.com/modauthgssapi/mod_auth_gssapi/blob/master/README
.. _mod_auth_gssapi: https://github.com/modauthgssapi/mod_auth_gssapi/

Social backends
~~~~~~~~~~~~~~~

In addition to builtin backends, Nitrate also works with a set of social
authentication backends by integrating with 3rd party package `Python Social
Auth - Django`_. To enable some social authentication backends, it is
recommended to read that package's documentation to get familiar with the basic
configuration steps. Then, administrator has to make some changes to settings
manually.

* Install dependent packages: ``pip install path/to/Nitrate[multiauth]``

* Add ``social_django`` to ``INSTALLED_APPS``.

* Add enabled authentication backends to ``AUTHENTICATION_BACKENDS``. For
  example to enable Fedora OpenID connect, add
  ``social_core.backends.fedora.FedoraOpenId``.

For more information, please refer to `Django Framework`_ section in Social
Auth documentation. Please also note that, Nitrate does not use MongoDB and
the template context processors.

.. _Python Social Auth - Django: https://github.com/python-social-auth/social-app-django
.. _Django Framework: https://python-social-auth.readthedocs.io/en/latest/configuration/django.html

Configure enabled backends
~~~~~~~~~~~~~~~~~~~~~~~~~~

Enabled authentication backends have to be configured so that login web page
could display UI elements correctly. To configure backends, define a mapping in
settings, which is called ``ENABLED_AUTH_BACKENDS``.

ENABLED_AUTH_BACKENDS
^^^^^^^^^^^^^^^^^^^^^

``ENABLED_AUTH_BACKENDS`` is a mapping containing key/value pairs for two kinds
of authentication backends. One requires to provide username and password from
Web page. Key ``USERPWD`` is used for this type. Another one is the social
backends that 3rd party services is responsible for authentication. Key
``SOCIAL`` is for that.

* ``USERPWD`` is a mapping containing one config ``ALLOW_REGISTER``. Setting it
  to True, a link will be shown under username and password input box in login
  web page to allow user to registering a new user for himself/herself.
  Otherwise, someone else with specific responsibility could have to create one
  for that user.

* ``SOCIAL`` is list of mappings for each enabled social authentication
  backends. Each mapping could have three key/value pairs.

  * ``backend``: the backend name enabled. For example, ``fedora`` or
    ``google-oauth2``.

  * ``label``: the text of A HTML element shown in login web page.

  * ``title``: an optional text shown in ``title`` attribute of A HTML element.

This is an example to configure a ``ModelBackend`` and a social backend to
shown a Fedora login URL in login web page.

.. code-block:: python

   ENABLED_AUTH_BACKENDS = {
       'USERPWD': {
           'ALLOW_REGISTER': True,
       },
       'SOCIAL': [
           {
               'backend': 'fedora',
               'label': 'Fedora',
               'title': 'Login with Fedora account',
           }
       ]
   }

It allows user to register a new account, and alternatively, user could also
login with his/her Fedora account by clicking a link showing text "Fedora".

Asynchronous Task
-----------------

ASYNC_TASK
~~~~~~~~~~

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
~~~~~~~~~~~~~~~

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

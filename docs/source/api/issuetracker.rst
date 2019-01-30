.. _api_issuetracker:

Issue Tracker
=============

.. toctree::
   :maxdepth: 2


.. autoclass:: tcms.issuetracker.models.CredentialTypes
   :members:

Models
------

.. autoclass:: tcms.issuetracker.models.IssueTrackerProduct
   :members:

.. autoclass:: tcms.issuetracker.models.IssueTracker
   :members:

.. autoclass:: tcms.issuetracker.models.ProductIssueTrackerRelationship
   :members:

.. autoclass:: tcms.issuetracker.models.Issue
   :members:

.. autoclass:: tcms.issuetracker.models.Credential
   :members:

.. autoclass:: tcms.issuetracker.models.UserPwdCredential
   :members:

.. autoclass:: tcms.issuetracker.models.TokenCredential
   :members:

Services
--------

A Service class is created for a specific issue tracker added to model
:class:`IssueTracker`, which is responsible for producing issue and tracker
related information, for example, issue report URL.

By default, Nitrate defines three service classes for different possible issue
tracker trackers, a general Bugzilla instance, the Red Hat Bugzilla, and JIRA
instance. See below for more information. It is free for users to change
settings to make it work with user's environment.

.. autofunction:: tcms.issuetracker.services.find_service

.. autoclass:: tcms.issuetracker.services.IssueTrackerService
   :members:

.. autoclass:: tcms.issuetracker.services.Bugzilla
   :members:

.. autoclass:: tcms.issuetracker.services.RHBugzilla
   :members:

.. autoclass:: tcms.issuetracker.services.JIRA
   :members:

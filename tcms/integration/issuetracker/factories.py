# -*- coding: utf-8 -*-

import factory

from factory.django import DjangoModelFactory

from tcms.integration.issuetracker.models import CredentialTypes
from tcms.tests.factories import ProductFactory
from tcms.tests.factories import TestCaseFactory
from tcms.tests.factories import TestCaseRunFactory


class IssueTrackerProductFactory(DjangoModelFactory):
    """Factory to create model IssueTrackerProduct"""

    name = factory.Sequence(lambda n: 'tracker_product_{}'.format(n))

    class Meta:
        model = 'issuetracker.IssueTrackerProduct'


class IssueTrackerFactory(DjangoModelFactory):
    """Factory to create model IssueTracker"""

    name = factory.Sequence(lambda n: 'Cool Issue Tracker {}'.format(n))
    issue_url_fmt = 'http://localhost/%{issue_key}s'
    validate_regex = r'^\d+$'
    credential_type = CredentialTypes.NoNeed.name
    issue_report_endpoint = '/enter.cgi'
    # product = factory.SubFactory(f.ProductFactory)
    tracker_product = factory.SubFactory(IssueTrackerProductFactory)

    class Meta:
        model = 'issuetracker.IssueTracker'


class ProductIssueTrackerRelationshipFactory(DjangoModelFactory):
    """Factory to create model ProductIssueTrackerRelationship"""

    product = factory.SubFactory(ProductFactory)
    issue_tracker = factory.SubFactory(IssueTrackerFactory)

    class Meta:
        model = 'issuetracker.ProductIssueTrackerRelationship'


class IssueFactory(DjangoModelFactory):
    """Factory to create model Issue"""

    class Meta:
        model = 'issuetracker.Issue'

    tracker = factory.SubFactory(IssueTrackerFactory)
    case = factory.SubFactory(TestCaseFactory)
    case_run = factory.SubFactory(TestCaseRunFactory)


class UserPwdCredentialFactory(DjangoModelFactory):
    """Factory to create UserPwdCredentialFactory"""

    class Meta:
        model = 'issuetracker.UserPwdCredential'

    issue_tracker = factory.SubFactory(IssueTrackerFactory)


class TokenCredentialFactory(DjangoModelFactory):
    """Factory to create model UserPwdCredential"""

    class Meta:
        model = 'issuetracker.TokenCredential'

    issue_tracker = factory.SubFactory(IssueTrackerFactory)

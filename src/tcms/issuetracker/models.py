# -*- coding: utf-8 -*-

import configparser
import importlib
import logging
import os
import re
import enum

from datetime import datetime
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.db.models import Count

from tcms.core.models import TCMSActionModel
from tcms.issuetracker import validators

logger = logging.getLogger(__name__)

TOKEN_EXPIRATION_DATE_FORMAT = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d',
]


def parse_token_expiration_date(value):
    for fmt in TOKEN_EXPIRATION_DATE_FORMAT:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            logger.warning(
                'Date %s is not in a known format %s. Skip it and '
                'try next format.')
    return None


@enum.unique
class CredentialTypes(enum.Enum):
    NoNeed = 'No need to login'
    UserPwd = 'Username/Password authentication'
    Token = 'Token based'


class IssueTrackerProduct(TCMSActionModel):
    """Representing a specific issue tracker product

    In real world, there are lots of issue tracker products, e.g. Bugzilla,
    JIRA, GitHub, GitLab, etc. This model represents one of them before adding
    an issue tracker to model :class:`IssueTracker`, which could represent a
    specific deployed instance, for example, the KDE Bugzilla and the GNOME
    Bugzilla.
    """

    name = models.CharField(
        max_length=30,
        unique=True,
        help_text='Name of issue tracker product.')

    class Meta:
        db_table = 'issue_tracker_products'

    def __str__(self):
        return self.name

    def import_service_class(self):
        module_path, _, class_name = importlib.import_module(self.klass_path)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)


class ProductIssueTrackerRelationship(TCMSActionModel):
    """Many-to-many relationship between Product and IssueTracker

    Before adding issues to case or case run, an issue tracker must be
    associated with a product added to Nitrate.
    """

    product = models.ForeignKey('management.Product', on_delete=models.CASCADE)
    issue_tracker = models.ForeignKey('issuetracker.IssueTracker', on_delete=models.CASCADE)

    alias = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='The corresponding product name in issue tracker.')

    namespace = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text='A name which the issues reported for product should '
                  'belong to in issue tracker. Different issue tracker '
                  'services will use this namespace to construct '
                  'specific URL for issue report. Namespace could be '
                  'empty, if product is not under a namespace in issue '
                  'tracker, or is the top level product with its own '
                  'components. For example, in a Bugzilla instance, product '
                  'A is a component of a product X, namespace should be the '
                  'name of X.',
        validators=[MaxLengthValidator(30)])

    def __str__(self):
        return f'Rel {self.product} - {self.issue_tracker}'

    class Meta:
        db_table = 'product_issue_tracker_relationship'
        unique_together = ('product', 'issue_tracker')


class IssueTracker(TCMSActionModel):
    """Represent a deployed issue tracker instance"""

    enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether to enable this issue tracker in system wide.')
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text='Issue tracker name.',
        validators=[
            MaxLengthValidator(50, message='Issue tracker name is too long.'),
            RegexValidator(
                r'^[a-zA-Z0-9 ]+$',
                message='Name contains invalid characters. Name could contain'
                        ' lower and upper case letters, digit or space.')
        ]
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='A short description to this issue tracker.')
    service_url = models.URLField(
        default='',
        blank=True,
        help_text='URL of this issue tracker.')
    api_url = models.URLField(
        default='',
        blank=True,
        help_text='API URL of this issue tracker.')

    issues_display_url_fmt = models.URLField(
        help_text='URL format to construct a display URL used to open in Web '
                  'browse to display issues. For example, '
                  'http://bugzilla.example.com/buglist.cgi?bug_id={issue_keys}'
    )

    issue_url_fmt = models.URLField(
        help_text='Formatter string used to construct a specific issue\'s URL.'
                  ' Format arguments: issue_key, product. For example,'
                  ' https://bugzilla.domain/show_bug.cgi?id=%(issue_key)s')

    validate_regex = models.CharField(
        max_length=100,
        help_text='Regular expression in Python Regular Expression syntax, '
                  'which is used to validate issue ID. This regex will be '
                  'used in both JavaScript code and Python code. So, please '
                  'write it carefully.',
        validators=[validators.validate_reg_exp])

    allow_add_case_to_issue = models.BooleanField(
        default=False,
        help_text='Allow to add associated test case link to issue.')

    credential_type = models.CharField(
        max_length=10,
        choices=[(item.name, item.value) for item in list(CredentialTypes)],
        help_text='Type of credential')

    tracker_product = models.ForeignKey(
        IssueTrackerProduct,
        related_name='tracker_instances',
        on_delete=models.CASCADE)

    products = models.ManyToManyField(
        'management.Product',
        through=ProductIssueTrackerRelationship,
        related_name='issue_trackers')

    # Field for loading corresponding Python class to do specific actions
    class_path = models.CharField(
        max_length=100,
        default='tcms.issuetracker.services.IssueTrackerService',
        help_text='Importable path to the implementation for this issue '
                  'tracker. Default is '
                  '<code>tcms.issuetracker.models.IssueTrackerService</code>, '
                  'which provides basic functionalities for general purpose. '
                  'Set to a custom path for specific class inherited from '
                  '<code>IssueTrackerService</code>',
        validators=[validators.validate_class_path])

    # Fields for implementing filing issue in an issue tracker.

    issue_report_endpoint = models.CharField(
        max_length=50,
        help_text='The endpoint of this issue tracker service to file an '
                  'issue.')

    issue_report_params = models.TextField(
        max_length=255,
        blank=True,
        default='',
        help_text='Parameters used to format URL for reporting issue. '
                  'Each line is a <code>key:value</code> pair of parameters. '
                  'Nitrate provides a few parameters to format URL and '
                  'additional parameters could be provided by system '
                  'administrator as well.',
        validators=[validators.validate_issue_report_params])

    issue_report_templ = models.TextField(
        max_length=255,
        blank=True,
        default='',
        help_text='The issue content template, which could be arbitrary text '
                  'with format arguments. Nitrate provides these format '
                  'arguments: <code>TestBuild.name</code>, '
                  '<code>setup</code>, <code>action</code> and '
                  '<code>effect</code>. The text is formatted with keyward '
                  'arguments.')

    class Meta:
        db_table = 'issue_trackers'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Get URL linking to this issue tracker

        :return: the URL.
        :rtype: str
        """
        return self.service_url

    @property
    def code_name(self):
        """Return a useful issue tracker name for programmatic purpose

        Several characters are replaced. Space in name is replaced with
        underscore.

        :return: a formatted name.
        :rtype: str
        """
        return self.name.replace(' ', '_')

    @classmethod
    def get_by_case(cls, case, enabled=True):
        """Find out issue trackers for a case

        :param case: to get related issue trackers for this test case.
        :type case: :class:`TestCase`
        :param bool enabled: whether to get enabled issue trackers. If omitted, defaults to True.
        :return: a queryset of matched issue trackers
        :rtype: QuerySet
        """
        criteria = {'products__in': case.plan.values('product')}
        if enabled is not None:
            criteria['enabled'] = enabled
        return cls.objects.filter(**criteria)

    @property
    def credential(self):
        """Get login credential

        The returned credential could contain different login credential data
        which depends on what credential type is configured for this issue
        tracker, and how corresponding credential is created.
        """
        if self.credential_type == CredentialTypes.NoNeed.name:
            return {}
        elif self.credential_type == CredentialTypes.UserPwd.name:
            cred = UserPwdCredential.objects.filter(issue_tracker=self).first()
            if cred is None:
                raise ValueError(
                    'Username/password credential is not set for issue tracker {}.'
                    .format(self.name))
            else:
                if cred.secret_file:
                    content = cred.read_secret_file(cred.secret_file)
                    return {
                        'username': content.get('issuetracker', 'username'),
                        'password': content.get('issuetracker', 'password'),
                    }
                else:
                    return {
                        'username': cred.username, 'password': cred.password,
                    }
        elif self.credential_type == CredentialTypes.Token.name:
            cred = TokenCredential.objects.filter(issue_tracker=self).first()
            if cred is None:
                raise ValueError('Token credential is not set for issue tracker {}.'
                                 .format(self.name))
            else:
                if cred.secret_file:
                    content = cred.read_secret_file(cred.secret_file)
                    return {'token': content.get('issuetracker', 'token')}
                else:
                    return {'token': cred.token}


class Credential(TCMSActionModel):
    """Base class providing general functions for credentials"""

    secret_file = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Alternative secret file in INI format including username '
                  'and password.')

    class Meta:
        abstract = True

    @staticmethod
    def read_secret_file(filename):
        config = configparser.ConfigParser()
        config.read([filename])
        return config

    def check_secret_file(self, filename):
        """Check if secret file is valid for reading credential

        :param str filename: the file name of secret file.
        :raises ValidationError: if cannot read credential from specified
            secret file.
        """
        if not os.access(filename, os.F_OK):
            raise ValidationError({
                'secret_file': 'Secret file {} does not exist.'
                .format(filename)
            })
        if not os.path.isfile(filename):
            raise ValidationError({
                'secret_file': f'{filename} is not a file.'
            })
        if not os.access(filename, os.R_OK):
            raise ValidationError({
                'secret_file': 'Secret file {} cannot be read.'
                .format(filename)
            })

        config = self.read_secret_file(filename)
        config_section = 'issuetracker'
        if not config.has_section(config_section):
            raise ValidationError({
                'secret_file': 'Secret file does not have section "issuetracker".'
            })
        if isinstance(self, TokenCredential):
            if not config.has_option(config_section, 'token'):
                raise ValidationError({
                    'secret_file': 'Token is not set in secret file.'
                })
            if config.has_option(config_section, 'until'):
                expiration_date = parse_token_expiration_date(
                    config.get(config_section, 'until'))
                today = datetime.utcnow()
                if expiration_date < today:
                    raise ValidationError({
                        'secret_file': 'Is token expired? The expiration date is '
                                       'older than today.'
                    })
        if (isinstance(self, UserPwdCredential) and
                not (config.has_option('issuetracker', 'username') and
                     config.has_option('issuetracker', 'password'))):
            raise ValidationError({
                'secret_file': 'Neither Username nor password is set in secrete file.'
            })

    def clean(self):
        """General validation for a concrete credential model

        Each concrete credential model derived from :class:`Credential` should
        call parent's ``clean`` before other validation steps.
        """
        super().clean()

        cred_type = self.issue_tracker.credential_type

        if cred_type == CredentialTypes.NoNeed.name:
            raise ValidationError({
                'issue_tracker': 'Is credential really required? '
                                 'Credential type "{}" is selected.'.format(
                                     CredentialTypes[cred_type].value)
            })

        if (isinstance(self, UserPwdCredential) and
                cred_type != CredentialTypes.UserPwd.name):
            raise ValidationError({
                'issue_tracker':
                    'Cannot create a username/password credential. '
                    'Credential type "{}" is selected.'.format(
                        CredentialTypes[cred_type].value)
            })

        if (isinstance(self, TokenCredential) and
                cred_type != CredentialTypes.Token.name):
            raise ValidationError({
                'issue_tracker':
                    'Cannot create a token based credential. '
                    'Credential type "{}" is selected.'.format(
                        CredentialTypes[cred_type].value)
            })

        if self.secret_file:
            self.check_secret_file(self.secret_file)


class UserPwdCredential(Credential):
    """Username/password credential for logging into issue tracker"""

    username = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Username to log into remote issue tracker.')
    password = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Password used with username together to log into remote '
                  'issue tracker.')

    issue_tracker = models.OneToOneField(
        IssueTracker,
        related_name='user_pwd_credential',
        on_delete=models.CASCADE)

    def __str__(self):
        return 'Username/Password Credential'

    class Meta:
        db_table = 'issue_tracker_user_pwd_credential'

    def clean(self):
        """Validate username/password credential"""
        super().clean()

        if not self.secret_file and not self.username and not self.password:
            raise ValidationError({
                'username': 'Username and password are not set yet. '
                            'Please consider setting them in database or '
                            'a secret file in filesystem.'
            })

        if self.username and self.secret_file:
            raise ValidationError({
                'username': 'Both username and secret file are specified. '
                            'Please consider using one of them.'
            })

        if self.username or self.password:
            if not self.username:
                raise ValidationError({'username': 'Missing username.'})
            if not self.password:
                raise ValidationError({'password': 'Missing password.'})


class TokenCredential(Credential):
    """Token based authentication for logging into issue tracker"""

    token = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Token used to log into remote issue tracker.')
    until = models.DateField(
        null=True,
        blank=True,
        help_text='Optional expiration date. This is useful for Nitrate to '
                  'determine whether the token has been expired before '
                  'request. If omitted, request will be sent without checking '
                  'the expiration date.')

    issue_tracker = models.OneToOneField(
        IssueTracker,
        related_name='token_credential',
        on_delete=models.CASCADE)

    def __str__(self):
        return 'Token credential'

    class Meta:
        db_table = 'issue_tracker_token_credential'

    def clean(self):
        """Validate token credential"""
        super().clean()

        if not self.secret_file and not self.token:
            raise ValidationError({
                'token': 'Token is not set yet. A token can be set in database'
                         ' or a secret file in filesystem.'
            })

        if self.token and self.secret_file:
            raise ValidationError({
                'token': 'Token is set in database as well as a secret file. '
                         'Please consider using one of them.'
            })

        if self.until:
            today = datetime.utcnow()
            if self.until < today:
                raise ValidationError('Expiration date is prior to today.')


class Issue(TCMSActionModel):
    """This is the issue which could be added to case or case run

    The meaning of issue in issue tracker represents a general concept. In
    different concrete issue tracker products, it has different name to call,
    e.g. bug in Bugzilla and issue in JIRA and GitHub.
    """

    issue_key = models.CharField(
        max_length=50,
        help_text='Actual issue ID corresponding issue tracker. Different '
                  'issue tracker may have issue IDs in different type or '
                  'format. For example, in Bugzilla, it could be an integer, '
                  'or in JIRA, it could be a string in format '
                  'PROJECTNAME-number, e.g. PROJECT-1000.',
        validators=[
            MaxLengthValidator(
                50,
                'Issue key has too many characters. '
                'It should have 50 characters at most.')
        ])

    summary = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Summary of issue.')

    description = models.TextField(
        null=True,
        blank=True,
        help_text='Description of issue.')

    tracker = models.ForeignKey(
        IssueTracker,
        related_name='issues',
        help_text='Which issue tracker this issue belongs to.',
        on_delete=models.CASCADE
    )
    case = models.ForeignKey(
        'testcases.TestCase',
        related_name='issues',
        help_text='A test case this issue is associated with.',
        error_messages={
            'required': 'Case is missed.'
        },
        on_delete=models.CASCADE
    )
    case_run = models.ForeignKey(
        'testruns.TestCaseRun',
        null=True,
        blank=True,
        related_name='issues',
        help_text='A test case run this issue is associated with optionally.',
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.issue_key

    class Meta:
        db_table = 'issue_tracker_issues'
        unique_together = (
            ('tracker', 'issue_key', 'case'),
            ('tracker', 'issue_key', 'case', 'case_run'),
        )

    def get_absolute_url(self):
        return self.tracker.issue_url_fmt.format(
            product=self.tracker.name,
            issue_key=self.issue_key)

    def clean(self):
        """Validate issue"""
        super().clean()

        issue_key_re = re.compile(self.tracker.validate_regex)
        if not issue_key_re.match(self.issue_key):
            raise ValidationError({
                'issue_key':
                    'Issue key {} is in wrong format for issue tracker "{}".'
                    .format(self.issue_key, self.tracker)
            })

    @staticmethod
    def count_by_case_run(case_run_ids=None):
        """Subtotal issues and optionally by specified case runs

        :param case_run_ids: list of test case run IDs to just return subtotal
            for them.
        :type case_run_ids: list[int]
        :return: a mapping from case run id to the number of issues belong to
            that case run.
        :rtype: dict
        """
        if case_run_ids is not None:
            assert isinstance(case_run_ids, list)
            assert all(isinstance(item, int)
                       for item in case_run_ids)
            criteria = {'case_run__in': case_run_ids}
        else:
            criteria = {'case_run__isnull': False}
        return {
            item['case_run']: item['issues_count']
            for item in (Issue.objects.filter(**criteria)
                                      .values('case_run')
                                      .annotate(issues_count=Count('pk')))
        }

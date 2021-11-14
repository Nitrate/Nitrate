# -*- coding: utf-8 -*-

import configparser
import enum
import logging
import os
import re
from datetime import datetime
from typing import Dict

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from tcms.core.models import TCMSActionModel
from tcms.issuetracker import validators

logger = logging.getLogger(__name__)

TOKEN_EXPIRATION_DATE_FORMAT = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def parse_token_expiration_date(value):
    for fmt in TOKEN_EXPIRATION_DATE_FORMAT:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            logger.warning("Date %s is not in a known format %s. Skip it and try next format.")
    return None


@enum.unique
class CredentialTypes(enum.Enum):
    NoNeed = "No need to login"
    UserPwd = "Username/Password authentication"
    Token = "Token based"


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
        help_text=_("Name of the issue tracker product."),
    )

    class Meta:
        db_table = "issue_tracker_products"

    def __str__(self):
        return self.name


class ProductIssueTrackerRelationship(TCMSActionModel):
    """Many-to-many relationship between Product and IssueTracker

    Before adding issues to case or case run, an issue tracker must be
    associated with a product added to Nitrate.
    """

    product = models.ForeignKey(
        "management.Product",
        on_delete=models.CASCADE,
        help_text=_("Select which project the issue tracker is associated with."),
    )
    issue_tracker = models.ForeignKey(
        "issuetracker.IssueTracker",
        on_delete=models.CASCADE,
        help_text=_("Select an issue tracker to be associated with a product."),
    )

    alias = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text=_("The corresponding product name in issue tracker."),
    )

    namespace = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text=_(
            "A name which the issues reported for product should belong to in "
            "issue tracker. Different issue tracker services will use this "
            "namespace to construct specific URL for issue report. Namespace "
            "could be empty, if product is not under a namespace in issue "
            "tracker, or is the top level product with its own components. "
            "For example, in a Bugzilla instance, product A is a component of "
            "a product X, namespace should be the name of X.",
        ),
        validators=[MaxLengthValidator(30)],
    )

    def __str__(self):
        return f"Rel {self.product} - {self.issue_tracker}"

    class Meta:
        db_table = "product_issue_tracker_relationship"
        unique_together = ("product", "issue_tracker")
        verbose_name = _("Relationship between Issue Tracker and Product")


class IssueTracker(TCMSActionModel):
    """Represent a deployed issue tracker instance"""

    enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether to enable this issue tracker in system wide. Default: true."),
    )
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Issue tracker name."),
        validators=[
            MaxLengthValidator(
                50, message=_("Issue tracker name is too long. 50 characters at most.")
            ),
            RegexValidator(
                r"^[a-zA-Z0-9 ]+$",
                message=_(
                    "Name contains invalid characters. Name could contain "
                    "lower and upper case letters, digit or space."
                ),
            ),
        ],
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("A short description to this issue tracker. 255 characters at most."),
    )
    service_url = models.URLField(
        default="",
        blank=True,
        verbose_name=_("Service URL"),
        help_text=_(
            "URL of this issue tracker. Example: https://issues.example.com/. "
            'The trailing slash "/" is optional.',
        ),
    )
    api_url = models.URLField(
        default="",
        blank=True,
        verbose_name=_("API URL"),
        help_text=_(
            "API URL of this issue tracker, that is used by the corresponding "
            "service object implementation to complete specific action. A "
            "typical use case would be, a service object of a Bugzilla may use"
            " this URL to associate a case with a specific bug as an external "
            "link. Example: https://bz.example.com/xmlrpc.cgi"
        ),
    )

    issues_display_url_fmt = models.URLField(
        default="",
        blank=True,
        verbose_name=_("Issues Display URL Format"),
        help_text=_(
            "URL format to construct a display URL used to open in Web browse "
            "to display issues. This should probably only apply to Bugzilla. "
            "Example: http://bz.example.com/buglist.cgi?bug_id={issue_keys}"
        ),
    )

    issue_url_fmt = models.URLField(
        verbose_name=_("Issue URL Format"),
        help_text=_(
            "Formatter string used to construct a specific issue's URL. "
            "Format arguments: issue_key, product. Example: "
            "https://bugzilla.domain/show_bug.cgi?id=%(issue_key)s"
        ),
    )

    validate_regex = models.CharField(
        max_length=100,
        help_text=_(
            "Regular expression in Python Regular Expression syntax, which is "
            "used to validate issue ID. This regex will be used in both "
            "JavaScript code and Python code. So, please write it carefully."
        ),
        validators=[validators.validate_reg_exp],
    )

    allow_add_case_to_issue = models.BooleanField(
        default=False,
        help_text=_("Allow to add associated test case link to issue."),
    )

    credential_type = models.CharField(
        max_length=10,
        choices=[(item.name, item.value) for item in list(CredentialTypes)],
        help_text=_(
            "Select a credential type. The corresponding service "
            "implementation will use it to log into the remote issue tracker "
            "service. Please remember to create a specific user/pwd or token "
            "credential if you select one of these two types."
        ),
    )

    tracker_product = models.ForeignKey(
        IssueTrackerProduct,
        related_name="tracker_instances",
        on_delete=models.CASCADE,
        verbose_name=_("Tracker Product"),
    )

    products = models.ManyToManyField(
        "management.Product",
        through=ProductIssueTrackerRelationship,
        related_name="issue_trackers",
    )

    # Field for loading corresponding Python class to do specific actions
    class_path = models.CharField(
        max_length=100,
        default="tcms.issuetracker.services.IssueTrackerService",
        verbose_name=_("Custom service class path"),
        help_text=_(
            "Importable path to the implementation for this issue tracker. "
            "Default is <code>tcms.issuetracker.models.IssueTrackerService</code>, "
            "which provides basic functionalities for general purpose. "
            "Set to a custom path for specific service implementation "
            "inherited from <code>IssueTrackerService</code>"
        ),
        validators=[validators.validate_class_path],
    )

    # Fields for implementing filing issue in an issue tracker.

    issue_report_endpoint = models.CharField(
        max_length=50,
        verbose_name=_("Issue Report Endpoint"),
        help_text=_(
            "The endpoint for filing an issue. Used in the serivce "
            "implementation to construct final full URL. Example: "
            "/secure/CreateIssue!default.jspa"
        ),
    )

    issue_report_params = models.TextField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Issue Report Parameters"),
        help_text=_(
            "Parameters used to format URL for reporting issue. Each line is a"
            " <code>key:value</code> pair of parameters. Nitrate provides a "
            "few parameters to format URL and additional parameters could be "
            "provided by system administrator as well."
        ),
        validators=[validators.validate_issue_report_params],
    )

    issue_report_templ = models.TextField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Issue Report Template"),
        help_text=_(
            "The issue content template, which could be arbitrary text with "
            "format arguments. Nitrate provides these format arguments: "
            "<code>TestBuild.name</code>, <code>setup</code>, <code>action</code> "
            "and <code>effect</code>. The text is formatted with keyward arguments."
        ),
    )

    class Meta:
        db_table = "issue_trackers"
        verbose_name = _("Issue Tracker")

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
        return self.name.replace(" ", "_")

    @classmethod
    def get_by_case(cls, case, enabled=True):
        """Find out issue trackers for a case

        :param case: to get related issue trackers for this test case.
        :type case: :class:`TestCase`
        :param bool enabled: whether to get enabled issue trackers. If omitted, defaults to True.
        :return: a queryset of matched issue trackers
        :rtype: QuerySet
        """
        criteria = {"products__in": case.plan.values("product")}
        if enabled is not None:
            criteria["enabled"] = enabled
        return cls.objects.filter(**criteria)

    @property
    def credential(self) -> Dict[str, str]:
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
                    f"Username/password credential is not set for issue tracker {self.name}."
                )
            else:
                if cred.secret_file:
                    content = cred.read_secret_file(cred.secret_file)
                    return {
                        "username": content.get("issuetracker", "username"),
                        "password": content.get("issuetracker", "password"),
                    }
                else:
                    return {
                        "username": cred.username,
                        "password": cred.password,
                    }
        elif self.credential_type == CredentialTypes.Token.name:
            cred = TokenCredential.objects.filter(issue_tracker=self).first()
            if cred is None:
                raise ValueError(f"Token credential is not set for issue tracker {self.name}.")
            else:
                if cred.secret_file:
                    content = cred.read_secret_file(cred.secret_file)
                    return {"token": content.get("issuetracker", "token")}
                else:
                    return {"token": cred.token}


class Credential(TCMSActionModel):
    """Base class providing general functions for credentials"""

    secret_file = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_(
            "An absolute path to an alternative secret file to provide the "
            "credential. The file must be in INI format."
        ),
    )

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
            raise ValidationError(
                {"secret_file": "Secret file {} does not exist.".format(filename)}
            )
        if not os.path.isfile(filename):
            raise ValidationError({"secret_file": f"{filename} is not a file."})
        if not os.access(filename, os.R_OK):
            raise ValidationError(
                {"secret_file": "Secret file {} cannot be read.".format(filename)}
            )

        config = self.read_secret_file(filename)
        config_section = "issuetracker"
        if not config.has_section(config_section):
            # Translators: validation error is shown in Admin WebUI
            raise ValidationError(
                {
                    "secret_file": _('Secret file does not have section "issuetracker".'),
                }
            )
        if isinstance(self, TokenCredential):
            if not config.has_option(config_section, "token"):
                # Translators: validation error is shown in Admin WebUI
                raise ValidationError(
                    {
                        "secret_file": _("Token is not set in secret file."),
                    }
                )
            if config.has_option(config_section, "until"):
                expiration_date = parse_token_expiration_date(config.get(config_section, "until"))
                today = datetime.utcnow()
                if expiration_date < today:
                    # Translators: validation error is shown in Admin WebUI
                    raise ValidationError(
                        {
                            "secret_file": _(
                                "Is token expired? The expiration date is older than today."
                            ),
                        }
                    )
        if isinstance(self, UserPwdCredential) and not (
            config.has_option("issuetracker", "username")
            and config.has_option("issuetracker", "password")
        ):
            # Translators: validation error is shown in Admin WebUI
            raise ValidationError(
                {
                    "secret_file": _("Neither Username nor password is set in secrete file."),
                }
            )

    def clean(self):
        """General validation for a concrete credential model

        Each concrete credential model derived from :class:`Credential` should
        call parent's ``clean`` before other validation steps.
        """
        super().clean()

        cred_type = self.issue_tracker.credential_type

        if cred_type == CredentialTypes.NoNeed.name:
            cred_type = CredentialTypes[cred_type].value
            raise ValidationError(
                {
                    "issue_tracker": f"Is credential really required? "
                    f'Credential type "{cred_type}" is selected.'
                }
            )

        if isinstance(self, UserPwdCredential) and cred_type != CredentialTypes.UserPwd.name:
            cred_type = CredentialTypes[cred_type].value
            raise ValidationError(
                {
                    "issue_tracker": f"Cannot create a username/password credential. "
                    f'Credential type "{cred_type}" is selected.'
                }
            )

        if isinstance(self, TokenCredential) and cred_type != CredentialTypes.Token.name:
            cred_type = CredentialTypes[cred_type].value
            raise ValidationError(
                {
                    "issue_tracker": f"Cannot create a token based credential. "
                    f'Credential type "{cred_type}" is selected.'
                }
            )

        if self.secret_file:
            self.check_secret_file(self.secret_file)


class UserPwdCredential(Credential):
    """Username/password credential for logging into issue tracker"""

    username = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_("Username used to log into remote issue tracker service."),
    )
    password = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_(
            "Password used with username together to log into remote issue tracker service."
        ),
    )

    issue_tracker = models.OneToOneField(
        IssueTracker,
        related_name="user_pwd_credential",
        on_delete=models.CASCADE,
        help_text=_("The issue tracker this credential is applied to."),
    )

    def __str__(self):
        return "Username/Password Credential"

    class Meta:
        db_table = "issue_tracker_user_pwd_credential"
        verbose_name = _("Username/Password Credential")

    def clean(self):
        """Validate username/password credential"""
        super().clean()

        if not self.secret_file and not self.username and not self.password:
            raise ValidationError(
                {
                    "username": _(
                        "Username and password are not set yet. Please consider "
                        "setting them in database or a secret file in filesystem."
                    ),
                }
            )

        if self.username and self.secret_file:
            raise ValidationError(
                {
                    "username": _(
                        "Both username and secret file are specified. "
                        "Please consider using one of them."
                    ),
                }
            )

        if self.username or self.password:
            if not self.username:
                raise ValidationError({"username": _("Missing username.")})
            if not self.password:
                raise ValidationError({"password": _("Missing password.")})


class TokenCredential(Credential):
    """Token based authentication for logging into issue tracker"""

    token = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Token used to log into remote issue tracker."),
    )
    until = models.DateField(
        null=True,
        blank=True,
        help_text=_(
            "Optional expiration date. This is useful for Nitrate to determine"
            " whether the token has been expired before request. If omitted, "
            "request will be sent without checking the expiration date."
        ),
    )

    issue_tracker = models.OneToOneField(
        IssueTracker,
        related_name="token_credential",
        on_delete=models.CASCADE,
        help_text=_("The issue tracker this credential is applied to."),
    )

    def __str__(self):
        return "Token credential"

    class Meta:
        db_table = "issue_tracker_token_credential"
        verbose_name = _("Token Credential")

    def clean(self):
        """Validate token credential"""
        super().clean()

        if not self.secret_file and not self.token:
            raise ValidationError(
                {
                    "token": _(
                        "Token is not set yet. A token can be set in database or a"
                        " secret file in filesystem."
                    ),
                }
            )

        if self.token and self.secret_file:
            raise ValidationError(
                {
                    "token": _(
                        "Token is set in database as well as a secret file. "
                        "Please consider using one of them."
                    ),
                }
            )

        if self.until:
            today = datetime.utcnow()
            if self.until < today:
                raise ValidationError(_("Expiration date is prior to today."))


class Issue(TCMSActionModel):
    """This is the issue which could be added to case or case run

    The meaning of issue in issue tracker represents a general concept. In
    different concrete issue tracker products, it has different name to call,
    e.g. bug in Bugzilla and issue in JIRA and GitHub.
    """

    issue_key = models.CharField(
        max_length=50,
        help_text=_(
            "Actual issue ID corresponding issue tracker. Different issue "
            "tracker may have issue IDs in different type or format. For "
            "example, in Bugzilla, it could be an integer, or in JIRA, it "
            "could be a string in format PROJECTNAME-number, e.g. PROJECT-1."
        ),
        validators=[
            MaxLengthValidator(50, _("Issue key has too many characters. 50 characters at most."))
        ],
    )

    summary = models.CharField(
        max_length=255, null=True, blank=True, help_text=_("Summary of issue.")
    )

    description = models.TextField(null=True, blank=True, help_text=_("Description of issue."))

    tracker = models.ForeignKey(
        IssueTracker,
        related_name="issues",
        on_delete=models.CASCADE,
        help_text=_("Which issue tracker this issue belongs to."),
    )
    case = models.ForeignKey(
        "testcases.TestCase",
        related_name="issues",
        help_text="A test case this issue is associated with.",
        error_messages={
            "required": _("Case is missed."),
        },
        on_delete=models.CASCADE,
    )
    case_run = models.ForeignKey(
        "testruns.TestCaseRun",
        null=True,
        blank=True,
        related_name="issues",
        help_text=_("Optionally associate this issue to this case run."),
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return self.issue_key

    class Meta:
        db_table = "issue_tracker_issues"
        unique_together = (
            ("tracker", "issue_key", "case"),
            ("tracker", "issue_key", "case", "case_run"),
        )

    def get_absolute_url(self):
        return self.tracker.issue_url_fmt.format(
            product=self.tracker.name, issue_key=self.issue_key
        )

    def clean(self):
        """Validate issue"""
        super().clean()

        issue_key_re = re.compile(self.tracker.validate_regex)
        if not issue_key_re.match(self.issue_key):
            raise ValidationError({"issue_key": f"Issue key {self.issue_key} is in wrong format."})

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
            assert all(isinstance(item, int) for item in case_run_ids)
            criteria = {"case_run__in": case_run_ids}
        else:
            criteria = {"case_run__isnull": False}
        return {
            item["case_run"]: item["issues_count"]
            for item in (
                Issue.objects.filter(**criteria)
                .values("case_run")
                .annotate(issues_count=Count("pk"))
            )
        }

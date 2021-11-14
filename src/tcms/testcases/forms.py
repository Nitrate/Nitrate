# -*- coding: utf-8 -*-

import re
from typing import List, Optional

from django import forms
from django.core.validators import MaxLengthValidator
from django.db.models import QuerySet
from tinymce.widgets import TinyMCE

from tcms.core.forms import DurationField, ModelChoiceField, StripURLField, UserField
from tcms.core.utils import string_to_list
from tcms.issuetracker.models import IssueTracker
from tcms.management.models import Component, Priority, Product, TestTag
from tcms.testplans.models import TestPlan
from tcms.testruns.models import TestCaseRun

from .fields import MultipleEmailField
from .models import AUTOMATED_CHOICES as FULL_AUTOMATED_CHOICES
from .models import TestCase, TestCaseCategory, TestCaseStatus

AUTOMATED_CHOICES = (
    (0, "Manual"),
    (1, "Auto"),
)

AUTOMATED_SERCH_CHOICES = (
    ("", "----------"),
    (0, "Manual"),
    (1, "Auto"),
    (2, "Both"),
)

ITEMS_PER_PAGE_CHOICES = (("20", "20"), ("50", "50"), ("100", "100"))


class IssueKeyField(forms.CharField):
    """
    Customizing forms CharFiled validation.
    Issue key could be seperated by comma.
    """

    def validate(self, value):
        super().validate(value)
        issue_key_regex = [
            re.compile(regex)
            for regex in IssueTracker.objects.values_list("validate_regex", flat=True)
        ]
        for issue_key in string_to_list(value):
            if not any(regex.match(issue_key) is not None for regex in issue_key_regex):
                raise forms.ValidationError(
                    "{} is not a valid issue key of configured issue trackers."
                )


# =========== Forms for create/update ==============


class BaseCaseForm(forms.Form):
    summary = forms.CharField(
        label="Summary",
    )
    default_tester = UserField(label="Default tester", required=False)
    requirement = forms.CharField(label="Requirement", required=False)
    is_automated = forms.MultipleChoiceField(
        choices=AUTOMATED_CHOICES,
        widget=forms.CheckboxSelectMultiple(),
    )
    is_automated_proposed = forms.BooleanField(label="Autoproposed", required=False)
    script = forms.CharField(label="Script", required=False)
    arguments = forms.CharField(label="Arguments", required=False)
    alias = forms.CharField(label="Alias", required=False)
    extra_link = StripURLField(label="Extra link", max_length=1024, required=False)
    # sortkey = forms.IntegerField(label = 'Sortkey', required = False)
    case_status = forms.ModelChoiceField(
        label="Case status",
        queryset=TestCaseStatus.objects.all(),
        empty_label=None,
        required=False,
    )
    priority = forms.ModelChoiceField(
        label="Priority",
        queryset=Priority.objects.all(),
        empty_label=None,
    )
    product = forms.ModelChoiceField(
        label="Product",
        queryset=Product.objects.all(),
        empty_label=None,
    )
    category = forms.ModelChoiceField(
        label="Category",
        queryset=TestCaseCategory.objects.none(),
        empty_label=None,
    )
    component = forms.ModelMultipleChoiceField(
        label="Components",
        queryset=Component.objects.none(),
        required=False,
    )
    notes = forms.CharField(label="Notes", widget=forms.Textarea, required=False)
    estimated_time = DurationField(label="Estimated Time", initial="0m", required=False)
    setup = forms.CharField(label="Setup", widget=TinyMCE(), required=False)
    action = forms.CharField(label="Actions", widget=TinyMCE(), required=False)
    effect = forms.CharField(label="Expect results", widget=TinyMCE(), required=False)
    breakdown = forms.CharField(label="Breakdown", widget=TinyMCE(), required=False)

    tag = forms.CharField(label="Tag", required=False)

    def clean_is_automated(self):
        data = self.cleaned_data["is_automated"]
        if len(data) == 2:
            return 2

        if len(data):
            # FIXME: Should data always be a list?
            try:
                return int(data[0])
            except ValueError:
                return data[0]

        return data

    def clean_tag(self):
        tags = []
        if self.cleaned_data["tag"]:
            tag_names = TestTag.string_to_list(self.cleaned_data["tag"])
            tags = TestTag.get_or_create_many_by_name(tag_names)
        return tags

    def populate(self, product_id=None):
        if product_id:
            self.fields["category"].queryset = TestCaseCategory.objects.filter(
                product__id=product_id
            )
            self.fields["component"].queryset = Component.objects.filter(product__id=product_id)
        else:
            self.fields["category"].queryset = TestCaseCategory.objects.all()
            self.fields["component"].queryset = Component.objects.all()


class NewCaseForm(BaseCaseForm):
    def clean_case_status(self):
        if not self.cleaned_data["case_status"]:
            return TestCaseStatus.get("PROPOSED")

        return self.cleaned_data["case_status"]


class EditCaseForm(BaseCaseForm):
    pass


class CaseNotifyForm(forms.Form):
    author = forms.BooleanField(required=False)
    default_tester_of_case = forms.BooleanField(required=False)
    managers_of_runs = forms.BooleanField(required=False)
    default_testers_of_runs = forms.BooleanField(required=False)
    assignees_of_case_runs = forms.BooleanField(required=False)
    notify_on_case_update = forms.BooleanField(required=False)
    notify_on_case_delete = forms.BooleanField(required=False)

    cc_list = MultipleEmailField(
        required=False,
        label="CC to",
        help_text="""It will send notification email to each Email address
            within CC list. Email addresses within CC list are
            separated by comma.""",
        widget=forms.Textarea(
            attrs={
                "rows": 1,
            }
        ),
    )


# =========== Forms for  XML-RPC functions ==============


class XMLRPCBaseCaseForm(BaseCaseForm):
    estimated_time = DurationField(required=False)
    is_automated = forms.ChoiceField(
        choices=FULL_AUTOMATED_CHOICES,
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )


class XMLRPCNewCaseForm(XMLRPCBaseCaseForm):
    plan = forms.ModelMultipleChoiceField(
        label="Test Plan",
        queryset=TestPlan.objects.all(),
        required=False,
    )

    def clean_case_status(self):
        if not self.cleaned_data["case_status"]:
            return TestCaseStatus.get("PROPOSED")

        return self.cleaned_data["case_status"]

    def clean_is_automated(self):
        if self.cleaned_data["is_automated"] == "":
            return 0

        return self.cleaned_data["is_automated"]


class XMLRPCUpdateCaseForm(XMLRPCBaseCaseForm):
    summary = forms.CharField(
        label="Summary",
        required=False,
    )
    priority = forms.ModelChoiceField(
        label="Priority",
        queryset=Priority.objects.all(),
        empty_label=None,
        required=False,
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        empty_label=None,
        required=False,
    )
    category = forms.ModelChoiceField(
        queryset=TestCaseCategory.objects.none(),
        empty_label=None,
        required=False,
    )


# =========== Forms for search/filter ==============


class BaseCaseSearchForm(forms.Form):
    summary = forms.CharField(required=False)
    author = forms.CharField(required=False)
    default_tester = forms.CharField(required=False)
    tag__name__in = forms.CharField(required=False)
    category = forms.ModelChoiceField(
        label="Category", queryset=TestCaseCategory.objects.none(), required=False
    )
    priority = forms.ModelMultipleChoiceField(
        label="Priority",
        queryset=Priority.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
    case_status = forms.ModelMultipleChoiceField(
        label="Case status",
        queryset=TestCaseStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
    component = forms.ModelChoiceField(
        label="Components", queryset=Component.objects.none(), required=False
    )
    issue_key = IssueKeyField(label="Issue Key", required=False)
    is_automated = forms.ChoiceField(
        choices=AUTOMATED_SERCH_CHOICES,
        required=False,
    )
    is_automated_proposed = forms.BooleanField(label="Autoproposed", required=False)

    def clean_tag__name__in(self):
        return TestTag.string_to_list(self.cleaned_data["tag__name__in"])

    def populate(self, product_id=None):
        """Limit the query to fit the plan"""
        if product_id:
            self.fields["category"].queryset = TestCaseCategory.objects.filter(
                product__id=product_id
            )
            self.fields["component"].queryset = Component.objects.filter(product__id=product_id)


class CaseFilterForm(BaseCaseSearchForm):
    pass


class SearchCaseForm(BaseCaseSearchForm):
    search = forms.CharField(required=False)
    plan = forms.CharField(required=False)
    product = forms.ModelChoiceField(
        label="Product", queryset=Product.objects.all(), required=False
    )

    def clean_case_status(self):
        return list(self.cleaned_data["case_status"])

    def clean_priority(self):
        return list(self.cleaned_data["priority"])


class QuickSearchCaseForm(forms.Form):
    case_id_set = forms.CharField(required=False)

    def clean_case_id_set(self):
        case_id_set = self.cleaned_data["case_id_set"]
        if case_id_set:
            try:
                return [int(cid) for cid in set(case_id_set.split(","))]
            except ValueError:
                raise forms.ValidationError(
                    "Please input valid case id(s). "
                    "use comma to split more than one "
                    'case id. e.g. "111, 222"'
                )
        else:
            raise forms.ValidationError(
                "Please input valid case id(s). "
                "use comma to split more than one "
                'case id. e.g. "111, 222"'
            )


# =========== Mist Forms ==============


class CloneCaseForm(forms.Form):
    case = forms.ModelMultipleChoiceField(
        label="Test Case",
        queryset=TestCase.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
    )
    plan = forms.ModelMultipleChoiceField(
        label="Test Plan",
        queryset=TestPlan.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
    )
    copy_case = forms.BooleanField(
        label="Create a copy",
        help_text="Create a copy (Unchecking will create a link to selected case)",
        required=False,
    )
    maintain_case_orignal_author = forms.BooleanField(
        label="Keep original author",
        help_text="Keep original author (Unchecking will make me as author "
        "of the copied test case)",
        required=False,
    )
    maintain_case_orignal_default_tester = forms.BooleanField(
        label="Keep original default tester",
        help_text="Keep original default tester (Unchecking will make me as "
        "default tester of the copied test case)",
        required=False,
    )
    copy_component = forms.BooleanField(
        label="Copy test case components to the product of selected Test Plan",
        help_text="Copy test case components to the product of selected Test Plan ("
        "Unchecking will remove components from copied test case)",
        required=False,
    )
    copy_attachment = forms.BooleanField(
        label="Copy the attachments",
        help_text="Copy test case attachments ("
        "Unchecking will remove attachments of copied test case)",
        required=False,
    )

    def populate(self, case_ids, plan=None):
        self.fields["case"].queryset = TestCase.objects.filter(case_id__in=case_ids)


class CaseAutomatedForm(forms.Form):
    a = forms.ChoiceField(
        choices=(("change", "Change"),),
        widget=forms.HiddenInput(),
    )
    o_is_automated = forms.BooleanField(
        label="Automated",
        required=False,
        help_text="This is an automated test case.",
    )
    o_is_manual = forms.BooleanField(
        label="Manual",
        required=False,
        help_text="This is a manual test case.",
    )
    o_is_automated_proposed = forms.BooleanField(
        label="Autoproposed",
        required=False,
        help_text="This test case is planned to be automated.",
    )

    def clean(self):
        super().clean()
        cdata = self.cleaned_data.copy()  # Cleanen data

        cdata["is_automated"] = None
        cdata["is_automated_proposed"] = None

        if cdata["o_is_manual"] and cdata["o_is_automated"]:
            cdata["is_automated"] = 2
        else:
            if cdata["o_is_manual"]:
                cdata["is_automated"] = 0

            if cdata["o_is_automated"]:
                cdata["is_automated"] = 1

        cdata["is_automated_proposed"] = cdata["o_is_automated_proposed"]

        return cdata

    def populate(self):
        self.fields["case"] = forms.ModelMultipleChoiceField(
            queryset=TestCase.objects.all(),
            error_messages={
                "required": "Missing test case ID. At least one should be given.",
                "invalid_choice": "Test case ID(s) %(value)s do not exist.",
            },
            help_text="Test cases whose is_automated property will be updated.",
        )


class BaseAddIssueForm(forms.Form):
    """Base form for adding an issue

    Case app has a URL to add an issue to a test case, which has case ID inside
    URL, for example, /case/id/issue/. Hence, adding an issue from Webpage does
    not need to pass case ID via request data.

    However, XMLRPC call does not have such a URL, instead, case ID must be
    passed via arguments. This is the major reason why form is separated into
    different forms for different use cases. Refer to following form subclasses
    derived from this base form.
    """

    issue_key = forms.CharField(error_messages={"required": "Issue key is missed."})
    summary = forms.CharField(
        required=False,
        validators=[
            MaxLengthValidator(
                255, "Summary is too long. Only 255 characters are accepted at most."
            )
        ],
    )
    description = forms.CharField(
        required=False,
        validators=[
            MaxLengthValidator(
                255,
                "Description is too long. Only 255 characters are accepted at most.",
            )
        ],
    )
    tracker = forms.ModelChoiceField(
        queryset=IssueTracker.objects.only("pk", "enabled", "name"),
        error_messages={
            "required": "Issue tracker is missed.",
            "invalid_choice": "Invalid issue tracker that does not exist.",
        },
    )


class CaseIssueForm(BaseAddIssueForm):
    """
    Form for adding an issue to a case especially used for validating XMLRPC
    arguments.

    When call XMLRPC API to add an issue to a case, case ID must be passed via
    argument.
    """

    case = ModelChoiceField(
        queryset=TestCase.objects.all(),
        error_messages={
            "required": "Case ID is missed.",
            "invalid_pk_value": "Test case %(pk)s does not exist.",
        },
    )


class CaseRunIssueForm(BaseAddIssueForm):
    """Form for adding an issue to a case run"""

    case_run = forms.ModelMultipleChoiceField(
        queryset=TestCaseRun.objects.all(),
        error_messages={
            "required": "Case run ID is missed.",
            "invalid_pk_value": "Invalid test case run %(pk)s that does not exist.",
        },
    )
    link_external_tracker = forms.BooleanField(required=False)

    def validate_issue_tracker(self) -> None:
        if "tracker" not in self.cleaned_data:
            return
        if "case_run" not in self.cleaned_data:
            return

        tracker: IssueTracker = self.cleaned_data["tracker"]

        if not tracker.enabled:
            raise forms.ValidationError(
                'Issue tracker "%(tracker_name)s" is not enabled.',
                params={"tracker_name": tracker.name},
                code="invalid",
            )

        case_runs: List[TestCaseRun] = self.cleaned_data["case_run"]

        for case_run in case_runs:
            is_tracker_relative = case_run.run.get_issue_trackers().filter(pk=tracker.pk).exists()
            if not is_tracker_relative:
                raise forms.ValidationError(
                    'Issue tracker "%(tracker_name)s" is not relative to the case run via product "%(product_name)s".',
                    params={
                        "tracker_name": tracker.name,
                        "product_name": case_run.run.plan.product,
                    },
                    code="invalid",
                )

    def clean(self):
        super().clean()
        self.validate_issue_tracker()


class CaseRemoveIssueForm(forms.Form):
    issue_key = forms.CharField(
        min_length=1,
        max_length=50,
        error_messages={"required": "Missing issue key to delete."},
    )
    case = ModelChoiceField(
        queryset=TestCase.objects.all(),
        error_messages={
            "required": "Case ID is missed.",
            "invalid_pk_value": "Test case %(pk)s does not exist.",
        },
    )
    case_run = forms.ModelChoiceField(
        required=False,
        queryset=TestCaseRun.objects.all(),
        error_messages={"invalid_choice": "Test case run does not exists."},
    )


class CaseComponentForm(forms.Form):
    """Form used to validate product and associated components"""

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        empty_label=None,
        required=False,
        error_messages={"invalid_choice": "Nonexistent product id."},
    )
    o_component = forms.ModelMultipleChoiceField(
        label="Components",
        queryset=Component.objects.all(),
        required=False,
        error_messages={
            "invalid_choice": "Nonexistent component id(s) %(value)s.",
            "invalid_pk_value": "Invalid component id(s) %(pk)s.",
        },
    )

    def populate(self, product_id=None):
        component_field = self.fields["o_component"]
        if product_id:
            component_field.queryset = Component.objects.filter(product__id=product_id).order_by(
                "pk"
            )
        else:
            component_field.queryset = Component.objects.order_by("pk")


class CaseCategoryForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        empty_label=None,
        required=False,
    )
    o_category = forms.ModelMultipleChoiceField(
        label="Categorys",
        queryset=TestCaseCategory.objects.none(),
        required=False,
    )

    def populate(self, product_id=None):
        field = self.fields["o_category"]
        manager = TestCaseCategory.objects
        if product_id:
            field.queryset = manager.filter(product__id=product_id)
        else:
            field.queryset = manager.all()


class CaseTagForm(forms.Form):
    tags = forms.ModelMultipleChoiceField(
        label="Tags",
        queryset=TestTag.objects.none(),
        required=False,
    )

    def populate(self, cases: Optional[QuerySet] = None):
        if cases is not None:
            # note: backwards relationship filter. TestCaseTag -> TestTag
            self.fields["tags"].queryset = (
                TestTag.objects.filter(cases__in=cases).order_by("name").distinct()
            )


class CasePlansForm(forms.Form):
    """
    Used for the plans tab inside a case page to add and remove plans
    """

    plan = forms.ModelMultipleChoiceField(
        queryset=TestPlan.objects.only("pk"),
        error_messages={
            "required": "Missing plan ids.",
            "invalid_choice": "Nonexistent plan ids %(value)s",
        },
    )
    case = forms.ModelChoiceField(
        queryset=TestCase.objects.only("pk"),
        error_messages={
            "required": "Missing case id.",
            "invalid_choice": "Case with id %(value)s does not exist.",
        },
    )

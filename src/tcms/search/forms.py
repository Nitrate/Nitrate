# -*- coding: utf-8 -*-

from functools import partial
from typing import Callable, Optional, TypeVar, cast

from django import forms
from django.http import QueryDict

from tcms.management.models import Component, Priority, Product, TestBuild, Version
from tcms.testcases.forms import IssueKeyField
from tcms.testcases.models import TestCaseCategory, TestCaseStatus
from tcms.testplans.models import TestPlanType

# template-functions creating form field with required = False
LooseCF = partial(forms.CharField, required=False, max_length=200)
LooseIF = partial(forms.IntegerField, required=False)
LooseIssueF = partial(IssueKeyField, required=False, max_length=200)
LooseDF = partial(forms.DateField, required=False)
LooseBF = partial(forms.BooleanField, required=False)
LooseMF = partial(forms.MultipleChoiceField, required=False, choices=())
PlanTypeF = partial(
    forms.ModelMultipleChoiceField, required=False, queryset=TestPlanType.objects.all()
)
ProductF = partial(forms.ModelMultipleChoiceField, required=False, queryset=Product.objects.none())
BuildF = partial(forms.ModelMultipleChoiceField, required=False, queryset=TestBuild.objects.none())
CategoryF = partial(
    forms.ModelMultipleChoiceField,
    required=False,
    queryset=TestCaseCategory.objects.none(),
)
ComponentF = partial(
    forms.ModelMultipleChoiceField, required=False, queryset=Component.objects.none()
)
VersionF = partial(forms.ModelMultipleChoiceField, required=False, queryset=Version.objects.none())

ChoiceT = TypeVar("ChoiceT")


def get_choice(
    value: str, _type: Optional[Callable[[str], ChoiceT]] = None, deli: str = ","
) -> list[ChoiceT]:
    """
    Used to clean a form field where multiple choices are seperated using a
    delimiter such as comma. Removing the empty value.
    """
    conv_func = str if _type is None else int
    try:
        results = value.split(deli)
        return [conv_func(r.strip()) for r in results if r]
    except Exception as e:
        raise forms.ValidationError(str(e))


def get_boolean_choice(value: str) -> Optional[bool]:
    return {"yes": True, "no": False}.get(value, None)


class PlanForm(forms.Form):
    pl_type = PlanTypeF()
    pl_summary = LooseCF()
    pl_id = LooseCF()
    pl_authors = LooseCF()
    pl_owners = LooseCF()
    pl_tags = LooseCF()
    pl_tags_exclude = LooseBF()
    pl_active = LooseCF()
    pl_created_since = LooseDF()
    pl_created_before = LooseDF()
    pl_product = ProductF()
    pl_component = ComponentF()
    pl_version = VersionF()

    def clean_pl_active(self) -> Optional[bool]:
        return get_boolean_choice(self.cleaned_data["pl_active"])

    def clean_pl_id(self) -> list[int]:
        return get_choice(self.cleaned_data["pl_id"], _type=int)

    def clean_pl_tags(self) -> list[str]:
        return get_choice(self.cleaned_data["pl_tags"])

    def clean_pl_authors(self) -> list[str]:
        return get_choice(self.cleaned_data["pl_authors"])

    def clean_pl_owners(self) -> list[str]:
        return get_choice(self.cleaned_data["pl_owners"])

    def populate(self, data: QueryDict):
        prod_pks = data.getlist("pl_product")
        prod_pks = [k for k in prod_pks if k]
        if prod_pks:
            pl_product_f = cast(forms.ModelMultipleChoiceField, self.fields["pl_product"])
            pl_product_f.queryset = Product.objects.filter(pk__in=prod_pks)
        comp_pks = data.getlist("pl_component")
        comp_pks = [k for k in comp_pks if k]
        if comp_pks:
            pl_component_f = cast(forms.ModelMultipleChoiceField, self.fields["pl_component"])
            pl_component_f.queryset = Component.objects.filter(pk__in=comp_pks)
        ver_pks = data.getlist("pl_version")
        ver_pks = [k for k in ver_pks if k]
        if ver_pks:
            pl_version_f = cast(forms.ModelMultipleChoiceField, self.fields["pl_version"])
            pl_version_f.queryset = Version.objects.filter(pk__in=ver_pks)


class CaseForm(forms.Form):
    cs_id = LooseCF()
    cs_summary = LooseCF()
    cs_authors = LooseCF()
    cs_tester = LooseCF()
    cs_tags = LooseCF()
    cs_issues = LooseIssueF()
    cs_status = LooseMF()
    cs_priority = LooseMF()
    cs_auto = LooseCF()
    cs_proposed = LooseCF()
    cs_script = LooseCF()
    cs_created_since = LooseDF()
    cs_created_before = LooseDF()
    cs_tags_exclude = LooseBF()
    cs_product = ProductF()
    cs_component = ComponentF()
    cs_category = CategoryF()

    def clean_cs_auto(self):
        return get_boolean_choice(self.cleaned_data["cs_auto"])

    def clean_cs_proposed(self):
        return get_boolean_choice(self.cleaned_data["cs_proposed"])

    def clean_cs_id(self):
        return get_choice(self.cleaned_data["cs_id"], _type=int)

    def clean_cs_authors(self):
        return get_choice(self.cleaned_data["cs_authors"])

    def clean_cs_issues(self):
        return get_choice(self.cleaned_data["cs_issues"], int)

    def clean_cs_tags(self):
        return get_choice(self.cleaned_data["cs_tags"])

    def clean_cs_tester(self):
        return get_choice(self.cleaned_data["cs_tester"])

    def populate(self, data: QueryDict):
        status_choice = list(TestCaseStatus.objects.order_by("pk").values_list("pk", "name"))
        cs_status_f = cast(forms.MultipleChoiceField, self.fields["cs_status"])
        cs_status_f.choices = status_choice

        priority_choice = list(Priority.objects.order_by("pk").values_list("pk", "value"))
        cs_priority_f = cast(forms.MultipleChoiceField, self.fields["cs_priority"])
        cs_priority_f.choices = priority_choice

        prod_pks = data.getlist("cs_product")
        prod_pks = [k for k in prod_pks if k]
        if prod_pks:
            cs_product_f = cast(forms.ModelMultipleChoiceField, self.fields["cs_product"])
            cs_product_f.queryset = Product.objects.filter(pk__in=prod_pks)
        comp_pks = data.getlist("cs_component")
        comp_pks = [k for k in comp_pks if k]
        if comp_pks:
            cs_component_f = cast(forms.ModelMultipleChoiceField, self.fields["cs_component"])
            cs_component_f.queryset = Component.objects.filter(pk__in=comp_pks)
        cat_pks = data.getlist("cs_category")
        cat_pks = [k for k in cat_pks if k]
        if cat_pks:
            cs_category_f = cast(forms.ModelMultipleChoiceField, self.fields["cs_category"])
            cs_category_f.queryset = TestCaseCategory.objects.filter(pk__in=cat_pks)


class RunForm(forms.Form):
    r_id = LooseCF()
    r_summary = LooseCF()
    r_manager = LooseCF()
    r_tester = LooseCF()
    r_tags = LooseCF()
    r_running = LooseCF()
    r_begin = LooseDF()
    r_finished = LooseDF()
    r_created_since = LooseDF()
    r_created_before = LooseDF()
    r_tags_exclude = LooseBF()
    r_real_tester = LooseCF()
    r_build = BuildF()
    r_product = ProductF()
    r_version = VersionF()

    def clean_r_running(self) -> Optional[bool]:
        return get_boolean_choice(self.cleaned_data["r_running"])

    def clean_r_id(self) -> list[int]:
        return get_choice(self.cleaned_data["r_id"], _type=int)

    def clean_r_tags(self) -> list[str]:
        return get_choice(self.cleaned_data["r_tags"])

    def clean_r_tester(self) -> list[str]:
        return get_choice(self.cleaned_data["r_tester"])

    def clean_r_real_tester(self) -> list[str]:
        return get_choice(self.cleaned_data["r_real_tester"])

    def clean_r_manager(self) -> list[str]:
        return get_choice(self.cleaned_data["r_manager"])

    def populate(self, data: QueryDict):
        prod_pks = data.getlist("r_product")
        prod_pks = [k for k in prod_pks if k]
        if prod_pks:
            r_product_f = cast(forms.ModelMultipleChoiceField, self.fields["r_product"])
            r_product_f.queryset = Product.objects.filter(pk__in=prod_pks).only("name")
        build_pks = data.getlist("r_build")
        build_pks = [k for k in build_pks if k]
        if build_pks:
            r_build_f = cast(forms.ModelMultipleChoiceField, self.fields["r_build"])
            r_build_f.queryset = TestBuild.objects.filter(pk__in=build_pks).only("name")
        ver_pks = data.getlist("r_version")
        ver_pks = [k for k in ver_pks if k]
        if ver_pks:
            r_version_f = cast(forms.ModelMultipleChoiceField, self.fields["r_version"])
            r_version_f.queryset = Version.objects.filter(pk__in=ver_pks).only("value")

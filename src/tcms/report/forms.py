# -*- coding: utf-8 -*-
from django import forms

from tcms.core.forms.fields import ModelChoiceField
from tcms.management.models import Component, Product, TestBuild, Version
from tcms.testcases.models import TestCaseCategory
from django.forms.widgets import ChoiceWidget
from django.utils.safestring import mark_safe


class ReportTypeSelect(ChoiceWidget):
    """Radio group for report type choise for testing report"""

    template_name = None

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        lines = []
        selected_values = context['widget']['value']
        for item in context['widget']['optgroups']:
            opt = item[1][0]
            name = opt['name']
            value = opt['value']
            label = opt['label']
            checked = 'checked' if value in selected_values else ''
            lines.append('<div class="form-check">')
            lines.append('<input class="form-check-input" type="radio" '
                         'name="{0}" id="id_{1}" value="{1}" {2}>'
                         .format(name, value, checked))
            lines.append('<label class="form-check-label" for="id_{}">{}</label>'
                         .format(value, label))
            lines.append('</div>')
        return mark_safe('\n'.join(lines))


class CustomSearchForm(forms.Form):
    pk__in = forms.ModelMultipleChoiceField(
        label='Build',
        queryset=TestBuild.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
    )
    product = ModelChoiceField(
        label='Product',
        queryset=Product.objects.only('name').order_by('name'),
        empty_label=None,
        error_messages={
            'required': 'Product is required to generate this report.',
            'invalid_choice': '%(value)s is not a valid product ID for '
                              'generating this report.',
        },
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    build_run__product_version = forms.ModelChoiceField(
        label='Product version',
        queryset=Version.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    build_run__plan__name__icontains = forms.CharField(
        label='Plan name',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    testcaserun__case__category = forms.ModelChoiceField(
        label='Case category',
        queryset=TestCaseCategory.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    testcaserun__case__component = forms.ModelChoiceField(
        label='Case component',
        queryset=Component.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def populate(self, product_id):
        if product_id:
            self.fields['build_run__product_version'].queryset = \
                Version.objects.filter(product__id=product_id).only('value')
            self.fields['pk__in'].queryset = TestBuild.objects.filter(
                product__id=product_id).only('name')
            self.fields['testcaserun__case__category'].queryset = \
                TestCaseCategory.objects.filter(product__id=product_id).only(
                    'name')
            self.fields['testcaserun__case__component'].queryset = \
                Component.objects.filter(product__id=product_id).only('name')
        else:
            # FIXME: is this branch necessary? when I notice this, I'm
            # optimizing custom report here. If product_id is None, it's an
            # critical error for the search operation and everything should be
            # stopped. Therefor, in my opinion, following 4 lines of code
            # waste time and resources.
            self.fields['build_run__product_version'].queryset = \
                Version.objects.only('value')
            self.fields['pk__in'].queryset = TestBuild.objects.only('name')
            self.fields['testcaserun__case__category'].queryset = \
                TestCaseCategory.objects.only('name')
            self.fields['testcaserun__case__component'].queryset = \
                Component.objects.only('name')


class CustomSearchDetailsForm(CustomSearchForm):
    pk__in = ModelChoiceField(
        label='Build',
        queryset=TestBuild.objects.none(),
        error_messages={
            'required': 'A build is required to generate this report.',
            'invalid_choice': '%(value)s is not a valid test build ID for '
                              'generating this report.',
        },
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def clean_build_run__product_version(self):
        return None


REPORT_TYPES = (
    ('per_build_report', 'By Case-Run Tester'),
    ('per_priority_report', 'By Case Priority'),
    ('runs_with_rates_per_plan_tag', 'By Plan\'s Tag'),
    ('per_plan_tag_report', 'By Plan\'s Tag Per Tag View'),
    ('runs_with_rates_per_plan_build', 'By Plan & Build'),
    ('per_plan_build_report', 'By Plan & Build Per Plan View'),
)


class BasicTestingReportFormFields(forms.Form):
    """Testing report form with basic necessary fields"""

    r_product = ModelChoiceField(
        required=True,
        label='Product',
        empty_label=None,
        queryset=Product.objects.only('name').order_by('name'),
        error_messages={
            'required': 'You have to select a product to generate this '
                        'testing report.',
            'invalid_choice': '%(value)s is not a valid product.',
        },
        widget=forms.Select(attrs={
            'id': 'r_product',
            'class': 'form-control',
        }))

    r_build = forms.ModelMultipleChoiceField(
        required=False,
        label='Build',
        queryset=TestBuild.objects.none(),
        error_messages={
            'invalid_pk_value': '%s is not a valid test build ID.',
            'invalid_choice': 'Test build ID %s does not exist.',
        },
        widget=forms.SelectMultiple(attrs={
            'id': 'r_build',
            'size': '5',
            'class': 'form-control',
        }))

    r_version = forms.ModelMultipleChoiceField(
        required=False,
        label='Version',
        queryset=Version.objects.none(),
        error_messages={
            'invalid_choice': 'Version ID %s does not exist.',
            'invalid_pk_value': '%s is not a valid version ID.',
        },
        widget=forms.SelectMultiple(attrs={
            'id': 'r_version',
            'size': '5',
            'class': 'form-control',
        }))

    r_created_since = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        error_messages={
            'invalid': 'The start execute date is invalid. The valid format'
                       ' is YYYY-MM-DD.',
        },
        widget=forms.TextInput(attrs={
            'id': 'r_created_since',
            'style': 'width:130px;',
            'class': 'form-control bootstrap-datepicker',
        }))

    r_created_before = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        error_messages={
            'invalid': 'The end execute date is invalid. The valid format '
                       'is YYYY-MM-DD.',
        },
        widget=forms.TextInput(attrs={
            'id': 'r_created_before',
            'style': 'width:130px;',
            'class': 'form-control bootstrap-datepicker',
        }))

    def populate(self, product_id):
        if product_id:
            self.fields['r_build'].queryset = TestBuild.objects.filter(
                product=product_id).only('name')
            self.fields['r_version'].queryset = Version.objects.filter(
                product=product_id).only('value')
        else:
            self.fields['r_build'].queryset = TestBuild.objects.none()
            self.fields['r_version'].queryset = Version.objects.none()


class TestingReportCaseRunsListForm(BasicTestingReportFormFields):
    """Form validation for viewing case runs from tesing report"""

    run = forms.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            'invalid': 'Run ID is not valid.',
            'min_value': '%(limit_value)s is not valid. Run ID should be an '
                         'integer that is greater than 0.',
        })

    priority = forms.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            'invalid': 'Priority ID is not valid.',
            'min_value': '%(limit_value)s is not valid. Priority ID should '
                         'be an integer that is greater than 0.',
        })

    tester = forms.IntegerField(
        required=False,
        min_value=0,
        error_messages={
            'invalid': 'User ID is not valid.',
            'min_value': '%(limit_value)s is not valid. User ID should be an'
                         ' integer that is greater than and equal to 0',
        })

    # Whatever the status name is passed from client, it doesn't matter. When
    # pass an invalid status name, no data will be queried.
    status = forms.CharField(
        required=False,
        max_length=30,
        error_messages={
            'max_length': 'Are you sure this is the status name you want?',
        })

    plan_tag = forms.CharField(
        required=False,
        max_length=30,
        error_messages={
            'max_length': 'Are your sure this is the tag you want?',
        })


class TestingReportForm(BasicTestingReportFormFields):
    """Criteria for generating testing report"""

    report_type = forms.ChoiceField(
        required=True,
        choices=REPORT_TYPES,
        initial='per_build_report',
        error_messages={
            'invalid_choice': '%(value)s is not a valid report type.',
        },
        widget=ReportTypeSelect(attrs={
            'class': 'form-control',
        })
    )

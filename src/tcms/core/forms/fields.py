# -*- coding: utf-8 -*-

import re

from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from tcms.core.utils import string_to_list, timedelta2int


class UserField(forms.CharField):
    """
    Custom field type.
    Will eventually support user selection
    """

    def clean(self, value):
        """
        Form-validation:  accept a string/integer.
        Looks at both email address and real name.
        """
        if value == '' or value is None:
            if self.required:
                raise ValidationError('A user name or user ID is required.')
            else:
                return None
        if isinstance(value, int):
            try:
                return User.objects.get(pk=value)
            except User.DoesNotExist:
                raise ValidationError('Unknown user_id: "%s"' % value)
        else:
            value = value.strip()
            if value.isdigit():
                try:
                    return User.objects.get(pk=value)
                except User.DoesNotExist:
                    raise ValidationError('Unknown user_id: "%s"' % value)
            else:
                try:
                    return User.objects.get(
                        (Q(email=value) | Q(username=value)))
                except User.DoesNotExist:
                    raise ValidationError('Unknown user: "%s"' % value)


class DurationField(forms.CharField):
    """
    Customizing forms CharFiled validation.
    estimated_time using integer mix with d(ay), h(our), m(inute)
    """
    default_error_messages = {
        'invalid': _('Enter a valid estimated time. e.g. 12h45m'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, value):
        super().validate(value)
        estimated_time_regex = re.compile(r'^(\d+[d])?(\d+[h])?(\d+[m])?(\d+[s])?$')
        match = estimated_time_regex.match(value.replace(' ', ''))

        if not match:
            raise forms.ValidationError(self.error_messages['invalid'])

    def clean(self, value):
        value = super().clean(value)
        return timedelta2int(value)


class MultipleEmailField(forms.EmailField):
    def clean(self, value):
        """
        Validates that the input matches the regular expression. Returns a
        Unicode object.
        """
        value = super(forms.CharField, self).clean(value)
        if value == '':
            return value

        return [v for v in string_to_list(strs=value) if self.regex.search(v)]


class StripURLField(forms.URLField):
    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip()
        return super().to_python(value)


class ModelChoiceField(forms.ModelChoiceField):
    """Custom field to include invalid choice in error message"""

    def to_python(self, value):
        try:
            return super().to_python(value)
        except ValidationError:
            if not self.to_field_name:
                # pk is used to query the model object
                raise ValidationError(
                    self.error_messages['invalid_pk_value'],
                    code='invalid_pk_value', params={'pk': value}
                )
            raise

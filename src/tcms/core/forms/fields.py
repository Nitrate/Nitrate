# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

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
        if value == "" or value is None:
            if self.required:
                raise ValidationError("A user name or user ID is required.")
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
                    return User.objects.get((Q(email=value) | Q(username=value)))
                except User.DoesNotExist:
                    raise ValidationError('Unknown user: "%s"' % value)


class DurationField(forms.CharField):
    """
    Customizing forms CharFiled validation.
    estimated_time using integer mix with d(ay), h(our), m(inute)
    """

    def clean(self, value):
        value = super().clean(value)
        try:
            return timedelta2int(value)
        except ValueError as e:
            raise forms.ValidationError(str(e)) from e


class MultipleEmailField(forms.CharField):
    def clean(self, value):
        """
        Validates that the input matches the regular expression. Returns a
        Unicode object.
        """
        value = super().clean(value)
        if value == "":
            return value
        result = []
        for mail_addr in string_to_list(value):
            validate_email(mail_addr)
            result.append(mail_addr)
        return result


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
                    self.error_messages["invalid_pk_value"],
                    code="invalid_pk_value",
                    params={"pk": value},
                )
            raise

# -*- coding: utf-8 -*-
import datetime

from django.core.exceptions import ValidationError
from django.db.models.fields import BooleanField, IntegerField

from tcms.core.forms.fields import DurationField as DurationFormField

try:
    from MySQLdb.constants import FIELD_TYPE
except ImportError:
    # Refer to tcms/__init__.py for details.
    pass
else:
    from django.db.backends.mysql.base import django_conversions

    django_conversions.update({FIELD_TYPE.TIME: None})


class DurationField(IntegerField):
    """Duration field for test run

    Value is stored as number of seconds in database and presents in Nitrate in
    timedelta type.

    Value should also be able to be serialized to integer as seconds, and then
    deserialized from value of seconds.
    """

    def to_python(self, value):
        if isinstance(value, int):
            return datetime.timedelta(seconds=value)
        elif isinstance(value, datetime.timedelta):
            return value
        else:
            raise TypeError("Unable to convert %s to timedelta." % value)

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return value
        return datetime.timedelta(seconds=value)

    def get_db_prep_value(self, value, connection, prepared=True):
        """convert datetime.timedelta to seconds.

        1 day equal to 86400 seconds
        """
        if isinstance(value, datetime.timedelta):
            return value.seconds + (86400 * value.days)
        else:
            value = super().get_db_prep_value(value, connection, prepared)
            return value

    def formfield(self, form_class=DurationFormField, **kwargs):
        defaults = {"help_text": "Enter duration in the format: DDHHMM"}
        defaults.update(kwargs)
        return form_class(**defaults)


class NitrateBooleanField(BooleanField):
    """Custom boolean field to allow accepting arbitrary bool values"""

    def to_python(self, value):
        if value in (1, "1", "true", "True", True):
            return True
        if value in (0, "0", "false", "False", False):
            return False
        raise ValidationError(f"{value} is not recognized as a bool value.")

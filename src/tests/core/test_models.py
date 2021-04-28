from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError

from tcms.core.models.fields import NitrateBooleanField


@pytest.mark.parametrize(
    "value,expected",
    [
        [0, False],
        ["0", False],
        ["false", False],
        ["False", False],
        [False, False],
        [1, True],
        ["1", True],
        ["true", True],
        ["True", True],
        [True, True],
        ["xx", None],
    ],
)
def test_nitrate_boolean_field(value, expected):
    field = NitrateBooleanField()
    if expected is None:
        with pytest.raises(ValidationError):
            field.clean(value, Mock())
    else:
        assert expected == field.clean(value, Mock())

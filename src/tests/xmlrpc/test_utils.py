# -*- coding: utf-8 -*-

import pytest
from django.db.models import ObjectDoesNotExist

import tcms.xmlrpc.utils as U
from tcms.management.models import Classification, Product
from tests import no_raised_error


@pytest.mark.parametrize(
    "input_value,expected",
    [
        [3, ValueError],
        [-1, ValueError],
        ["", ValueError],
        ["True", ValueError],
        ["False", ValueError],
        ["yes", ValueError],
        ["no", ValueError],
        ["33", ValueError],
        [[], ValueError],
        [(), ValueError],
        [{}, ValueError],
        [None, ValueError],
        [0, False],
        ["0", False],
        [False, False],
        [1, True],
        ["1", True],
        [True, True],
    ],
)
def test_parse_tool_value(input_value, expected):
    if expected == ValueError:
        with pytest.raises(expected, match="Unacceptable bool value."):
            U.parse_bool_value(input_value)
    else:
        U.parse_bool_value(input_value)


@pytest.mark.parametrize(
    "input_value,expected",
    [
        [1, no_raised_error()],
        ["World Of Warcraft", no_raised_error()],
        [{"product": "World Of Warcraft"}, no_raised_error()],
        [{"product": 1}, no_raised_error()],
        # invalid input value
        ["1", pytest.raises(ObjectDoesNotExist)],
        [{"product": 9999}, pytest.raises(ObjectDoesNotExist)],
        [{"product": "unknown name"}, pytest.raises(ObjectDoesNotExist)],
        [(), pytest.raises(ValueError, match="product is not recognizable")],
        [[], pytest.raises(ValueError, match="product is not recognizable")],
        [True, pytest.raises(ValueError, match="product is not recognizable")],
        [False, pytest.raises(ValueError, match="product is not recognizable")],
        [object(), pytest.raises(ValueError, match="product is not recognizable")],
        [{}, pytest.raises(ValueError)],
    ],
)
@pytest.mark.django_db()
def test_pre_check_product(input_value, expected):
    product = Product.objects.create(
        pk=1,
        name="World Of Warcraft",
        classification=Classification.objects.create(name="web"),
    )

    with expected:
        assert product == U.pre_check_product(input_value)


@pytest.mark.parametrize(
    "input_value,expected,raised_error",
    [
        [["1", "2", "3"], [1, 2, 3], no_raised_error()],
        ["1", [1], no_raised_error()],
        ["1,2,3,4", [1, 2, 3, 4], no_raised_error()],
        [1, [1], no_raised_error()],
        [(1,), None, pytest.raises(TypeError, match="Unrecognizable type of ids")],
        [{"a": 1}, None, pytest.raises(TypeError, match="Unrecognizable type of ids")],
        [["a", "b"], None, pytest.raises(ValueError)],
        ["1@2@3@4", None, pytest.raises(ValueError)],
    ],
)
def test_pre_process_ids(input_value, expected, raised_error):
    with raised_error:
        assert expected == U.pre_process_ids(input_value)


@pytest.mark.parametrize(
    "input_value,expected,raised_error",
    [
        ["", "", no_raised_error()],
        ["13:22:54", "13h22m54s", no_raised_error()],
        ["1d13h22m54s", "1d13h22m54s", no_raised_error()],
        # invalid input value
        ["aa@bb@cc", None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        ["ambhcs", None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        ["aa:bb:cc", None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        ["1D13H22M54S", None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        ["aaaaaa", None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        [[], None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        [(), None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        [{}, None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        [True, None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        [False, None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        [0, None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        [1, None, pytest.raises(ValueError, match="Invaild estimated_time format")],
        [-1, None, pytest.raises(ValueError, match="Invaild estimated_time format")],
    ],
)
def test_pre_process_estimated_time(input_value, expected, raised_error):
    with raised_error:
        U.pre_process_estimated_time(input_value)

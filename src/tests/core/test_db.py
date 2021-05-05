import operator
from typing import Dict, List, Optional, Tuple, Union

import pytest

from tcms.core.db import SQLExecution, get_groupby_result
from tcms.management.models import Priority
from tests import factories as f


@pytest.mark.parametrize(
    "with_field_name,sql,params,expected_result,expected_scalar",
    [
        [
            True,
            "SELECT summary FROM test_cases",
            None,
            [{"summary": "case 1"}, {"summary": "case 2"}],
            "case 1",
        ],
        [
            False,
            "SELECT summary, script FROM test_cases",
            None,
            [("case 1", "echo hello"), ("case 2", "find /tmp")],
            "case 1",
        ],
        [
            False,
            "SELECT summary FROM test_cases WHERE summary = %s",
            ("case 2",),
            [("case 2",)],
            "case 2",
        ],
    ],
)
@pytest.mark.django_db()
def test_execute_sql(
    with_field_name: bool,
    sql: str,
    params: Optional[Tuple[str]],
    expected_result: Union[List[Dict[str, str]], Tuple[str]],
    expected_scalar: str,
):
    """Test SQLExecution"""
    f.TestCaseFactory(summary="case 1", script="echo hello")
    f.TestCaseFactory(summary="case 2", script="find /tmp")

    exec_result = SQLExecution(sql, params=params, with_field_name=with_field_name)
    assert expected_result == sorted(
        exec_result.rows, key=operator.itemgetter("summary" if with_field_name else 0)
    )

    exec_result = SQLExecution(sql, params=params, with_field_name=with_field_name)
    assert expected_scalar == exec_result.scalar


@pytest.mark.parametrize(
    "sql,params,key_name,value_name,expected_result",
    [
        # Test default argument key_name
        [
            "SELECT priority.value AS groupby_field, COUNT(test_cases.case_id) AS total_count "
            "FROM priority JOIN test_cases on priority.id = test_cases.priority_id "
            "GROUP BY priority.id",
            [],
            None,
            None,
            (2, 2, 1, 5),
        ],
        # Test argument key_name
        [
            "SELECT priority.value, COUNT(test_cases.case_id) AS total_count "
            "FROM priority JOIN test_cases on priority.id = test_cases.priority_id "
            "GROUP BY priority.id",
            [],
            "value",
            None,
            (2, 2, 1, 5),
        ],
        # Test SQL params
        [
            "SELECT priority.value, COUNT(test_cases.case_id) AS total_count "
            "FROM priority JOIN test_cases on priority.id = test_cases.priority_id "
            "GROUP BY priority.id HAVING priority.value = %s",
            ["P1"],
            "value",
            None,
            (2, 0, 0, 2),
        ],
        # Test argument value_name
        [
            "SELECT priority.value, COUNT(test_cases.case_id) AS case_count "
            "FROM priority JOIN test_cases on priority.id = test_cases.priority_id "
            "GROUP BY priority.id",
            [],
            "value",
            "case_count",
            (2, 2, 1, 5),
        ],
    ],
)
@pytest.mark.django_db()
def test_get_groupby_result(
    sql: str,
    params: List[Union[int, str]],
    key_name: Union[str, None],
    value_name: Optional[str],
    expected_result: Tuple[int, int, int, int],
    django_user_model,
):
    p1 = Priority.objects.get(value="P1")
    p2 = Priority.objects.get(value="P2")
    p3 = Priority.objects.get(value="P3")

    tester = django_user_model.objects.create(username="tester", email="tester@example.com")
    plan = f.TestPlanFactory(author=tester)
    f.TestCaseFactory(plan=[plan], priority=p1, author=tester)
    f.TestCaseFactory(plan=[plan], priority=p1, author=tester)
    f.TestCaseFactory(plan=[plan], priority=p2, author=tester)
    f.TestCaseFactory(plan=[plan], priority=p2, author=tester)
    f.TestCaseFactory(plan=[plan], priority=p3, author=tester)

    result = get_groupby_result(sql, params, key_name=key_name, value_name=value_name)

    p1_cnt = result.get("P1", 0)
    p2_cnt = result.get("P2", 0)
    p3_cnt = result.get("P3", 0)
    total = result.total
    assert expected_result == (p1_cnt, p2_cnt, p3_cnt, total)

# -*- coding: utf-8 -*-

from collections.abc import Iterator
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from tcms.core.tcms_router import connection

__all__ = (
    "SQLExecution",
    "get_groupby_result",
    "GroupByResult",
    "workaround_single_value_for_in_clause",
)


def workaround_single_value_for_in_clause(build_ids):
    """Workaround for using MySQL-python 1.2.4

    This workaround is not necessary after upgrading MySQL-python to 1.2.5
    """
    return build_ids * 2 if len(build_ids) == 1 else build_ids


class SQLExecution:
    """Cursor.execute proxy class

    This proxy class provides two major abilities.

    1. iteration of visiting each row selected by SELECT statement from db
    server.

    2. get the affected rows' count. This will benefit developers to avoid
    issuing extra SQL to count the number of rows current SELECT statement is
    retrieving.

    Compatibility: the second item above relies on cursor.rowcount attribute
    described in PEP-0249. Cannot guarantee all database backends supports this
    by following 249 specification. But, at least, MySQLdb and psycopg2 does.

    :param str sql: the SQL query to execute
    :param params: optional, parameters for the SQL.
    :type params: list or tuple
    :param bool with_field_name: whether the generated rows are mappings from
        field name to value, otherwise a row is just a simple tuple returned
        from underlying DBAPI ``fetchone``.
    """

    def __init__(
        self,
        sql: str,
        params: Optional[Union[List[Any], Tuple[Any]]] = None,
        with_field_name: bool = True,
    ):
        """Initialize and execute SQL query"""
        self.cursor = connection.reader_cursor
        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)
        self.field_names = [field[0] for field in self.cursor.description]

        self._with_field_name = with_field_name
        if with_field_name:
            self.rows = self._rows_with_field_name
        else:
            self.rows = self._raw_rows

    @property
    def _rows_with_field_name(self):
        while 1:
            row = self.cursor.fetchone()
            if row is None:
                break
            yield dict(zip(self.field_names, row))

    @property
    def _raw_rows(self):
        while 1:
            row = self.cursor.fetchone()
            if row is None:
                break
            yield row

    @property
    def scalar(self):
        row = next(self.rows)
        if self._with_field_name:
            for _, value in row.items():
                return value
        else:
            return row[0]


# TODO: redesign GroupByResult, major goal is to distiguish level node and
# value node.


class GroupByResult:
    """Group By result

    This object can be used as a normal dict object with less support of stock
    dictionary methods. Consumers can do:

    * get a subtotal associated with a name.
    * get a subtotal's percentage.
    * know whether it's empty. Empty means no data from database of the
      ``GROUP BY`` query.
    * how many subtotals there.

    The main purpose of GroupByResult is to get specific subtotal(s) and the
    percentage of each of them. Rules to get such values:

    * each subtotal is associated with a name. If name you give does not exist,
      0 is returned, otherwise proper value is returned.
    * percentage of each subtotal has a special name with format of subtotal
      name plus '_percent'.

    Examples:

    Suppose, a GroupByResult object named gbr is ``{'A': 100, 'B': 200}``.

    * To get subtotal of A, ``gbr.A``.
    * To get percentage of B, ``gbr.B_percent``.

    :param data: subtotal result represented as a mapping whose key is field
        grouped by and value is the subtotal count, or a iterable of
        ``(key, value)``.
    :type data: dict or iterable
    """

    def __init__(self, data: Optional[Dict[Any, Any]] = None, total_name: Optional[str] = None):
        self._total_name = total_name
        self._data: Dict[Any, Any] = {} if data is None else dict(data)
        self._total_result = self._get_total()

        self._meta = {}

    # ## proxy method ###

    def __contains__(self, item):
        return self._data.__contains__(item)

    def __getitem__(self, key):
        # Behave like what collections.defaultdict does. If a key does not exist
        # yet, just return 0. This is based on the assumption of the value type
        # within GroupByResult could be integer or a nested GroupByResult.
        if key in self._data:
            return self._data.__getitem__(key)
        raise KeyError(f"Unknown key {key} inside the group by result.")

    def __setitem__(self, key, value):
        r = self._data.__setitem__(key, value)
        self._update_total_result()
        return r

    def __delitem__(self, key):
        r = self._data.__delitem__(key)
        self._update_total_result()
        return r

    def __len__(self):
        return self._data.__len__()

    def __str__(self):
        return self._data.__str__()

    def __repr__(self):
        return self._data.__repr__()

    def get(self, key: str, default: Optional[int] = None) -> Optional[int]:
        return self._data.get(key, default)

    def iteritems(self):
        return self._data.items()

    def setdefault(self, key, default=None):
        return self._data.setdefault(key, default)

    def keys(self):
        return self._data.keys()

    # ## end of proxy methods ###

    @property
    def empty(self):
        return len(self._data) == 0

    @property
    def total(self) -> int:
        return self._total_result

    def _update_total_result(self):
        self._total_result = self._get_total()

    def _get_total(self) -> int:
        """Get the total value of this GROUP BY result

        Total value comes from two situations. One is that there is no total
        value computed in database side by issuing GROUP BY with ROLLUP. In
        this case, total value will be calculated from all subtotal values.
        Inversely, the total value will be returned directly.
        """
        if self.empty:
            return 0

        if self._total_name is not None:
            # Hey, GROUP BY ... WITH ROLLUP is already used to get the total
            # result.
            total = self[self._total_name]
        else:
            total = 0
            for name, subtotal in self._data.items():
                # NOTE: is it possible do such judgement in advance when adding
                # element
                if isinstance(subtotal, int):
                    total += subtotal
                elif isinstance(subtotal, GroupByResult):
                    total += subtotal.total
                else:
                    raise TypeError(f"Value {subtotal} is neither in type int nor GroupByResult.")

        return total

    def _get_percent(self, key) -> float:
        """Percentage of a subtotal

        :param str key: name of subtotal whose percentage will be calculated
        :return: a float number representing the percentage
        :rtype: float
        """
        total = self._total_result
        if total == 0:
            return 0.0
        subtotal = self[key]
        return round(subtotal * 100.0 / total, 1)

    def __getattr__(self, name: str) -> Union[int, float]:
        if name.endswith("_percent"):
            key, _ = name.split("_")
            if key in self._data:
                return self._get_percent(key)
        return 0

    def leaf_values_count(self, value_in_row=False, refresh=False):
        """Calculate the total number of leaf values under this level

        After the first time this method gets call, the result will be cached
        as meta data of this level node. So, any number of subsequent
        invocations of this method will return result by reading self._meta
        directly without repeating calculation. Unless, pass True to argument
        refresh.

        :param bool value_in_row: whether leaf value should be treated as a row,
            in such way, leaf value will be displayed in one row.
        :param bool refresh: whether force to recalculate
        :return: the total number of leaf values under this level
        :rtype: int
        """
        if refresh:
            necessary_to_count = True
        else:
            necessary_to_count = "value_leaf_count" not in self._meta
        if not necessary_to_count:
            return self._meta["value_leaf_count"]

        count = 0
        for key, value in self.iteritems():
            if isinstance(value, GroupByResult):
                count += value.leaf_values_count(value_in_row)
            else:
                count = 1 if value_in_row else count + 1
        self._meta["value_leaf_count"] = count
        return count


# TODO: enhance method get_groupby_result to support multiple fields in GROUP
# BY clause.

# TODO: key_conv and value_name are not used, maybe the rest as well.
# we should probably remove them
def get_groupby_result(
    sql: str,
    params: List[Union[int, str]],
    key_name: Optional[str] = None,
    key_conv: Optional[Callable[[Any], Any]] = None,
    value_name: Optional[str] = None,
    with_rollup: bool = False,
    rollup_name: Optional[str] = None,
):
    """Get mapping between GROUP BY field and total count

    Example, to execute SQL `SELECT objtype, count(*) from t1 GROUP by name`.

    Possible values of objtype are plan, case, run. Then, the result of this
    method would be a dictionary object like this

    {'plan': 100, 'case': 50, 'run': 300}

    If use WITH ROLLUP like
    `SELECT objtype, count(*) from t1 GROUP by name WITH ROLLUP`. Result of
    this query would be

    {'plan': 100, 'case': 50, 'run': 300, 'TOTAL': 450}

    :param str sql: the GROUP BY SQL statement.
    :param params: parameters of the GROUP BY SQL statement.
    :type params: list or tuple
    :param str key_name: the GROUP BY field name, that will be the key in
        result mapping object. Default to groupby_field if not specified.
    :param key_conv: method call applied to the value of GROUP BY field while
        constructing the result mapping.
    :type key_conv: callable object
    :param value_name: the field name of total count. Default to total_count if
        not specified.
    :type value_name: str or None
    :param bool with_rollup: whether ``WITH ROLLUP`` is used in ``GROUP BY`` in
        a raw SQL. Default to ``False``.
    :param str rollup_name: name associated with ROLLUP field. Default to
        ``TOTAL``.
    :return: mapping between GROUP BY field and the total count.
    :rtype: dict
    """

    def _key_conv(value: Any) -> Any:
        if key_conv is not None:
            if not hasattr(key_conv, "__call__"):
                raise ValueError("key_conv is not a callable object")
            return key_conv(value)
        else:
            return value

    _key_name = "groupby_field" if key_name is None else str(key_name)
    _value_name = "total_count" if value_name is None else str(value_name)

    _rollup_name = None
    if with_rollup:
        _rollup_name = "TOTAL" if rollup_name is None else rollup_name

    def _rows_generator() -> Iterator:
        sql_executor = SQLExecution(sql, params)
        for row in sql_executor.rows:
            key, value = row[_key_name], row[_value_name]
            if with_rollup:
                yield _key_conv(_rollup_name if key is None else key), value
            else:
                yield _key_conv(key), value

    return GroupByResult(_rows_generator(), total_name=_rollup_name)


class CaseRunStatusGroupByResult(GroupByResult):
    """Specific for group by result from TestCaseRun"""

    @property
    def complete_count(self):
        return (
            self.get("PASSED", 0)
            + self.get("ERROR", 0)
            + self.get("FAILED", 0)
            + self.get("WAIVED", 0)
        )

    @property
    def failure_count(self):
        return self.get("ERROR", 0) + self.get("FAILED", 0)

    @property
    def complete_percent(self):
        if self.total:
            return self.complete_count * 100.0 / self.total
        else:
            return 0.0

    @property
    def failure_percent_in_complete(self):
        if self.complete_count:
            return self.failure_count * 100.0 / self.complete_count
        else:
            return 0.0

    @property
    def failure_percent_in_total(self):
        if self.total:
            return self.failure_count * 100.0 / self.total
        else:
            return 0.0

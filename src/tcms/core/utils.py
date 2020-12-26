# -*- coding: utf-8 -*-

import functools
import hashlib
import operator
import re
from typing import List, Dict, Any, Union

from django.apps import apps
from django.db.models import QuerySet
from django.http import QueryDict


def string_to_list(strs, spliter=','):
    """Convert the string to list"""
    if isinstance(strs, list):
        str_list = (
            item.strip() if isinstance(item, bytes) else item
            for item in strs
        )
    elif strs.find(spliter):
        str_list = (
            item.strip() if isinstance(item, bytes) else item
            for item in strs.split(spliter)
        )
    else:
        str_list = (strs,)
    return [s for s in str_list if s]


def form_errors_to_list(form):
    """
    Convert errors of form to list
    Use for Ajax.Request response
    """
    return [(k, v[0]) for k, v in form.errors.items()]


def form_error_messages_to_list(form):
    return list(functools.reduce(operator.add, form.errors.values()))


def get_string_combinations(s):
    """Get the lower, upper, capitalized version of the given string

    :param str s: string
    :return: a list containing s and the lowercase, uppercase
            & first letter uppercase form of s.
    :rtype: list[str]
    """
    return s, s.lower(), s.upper(), s.capitalize()


def calc_percent(x, y):
    if not x or not y:
        return 0

    return float(x) / y * 100


def request_host_link(request, domain_name=None):
    if request.is_secure():
        protocol = 'https://'
    else:
        protocol = 'http://'

    if not domain_name:
        domain_name = request.get_host()

    return protocol + domain_name


def clean_request(request, keys=None):
    """
    Clean the request strings
    """
    request_contents = request.GET.copy()
    if not keys:
        keys = request_contents.keys()
    rt = {}
    for k in keys:
        k = str(k)
        if request_contents.get(k):
            if k == 'order_by' or k == 'from_plan':
                continue

            v = request.GET[k]
            # Convert the value to be list if it's __in filter.
            if k.endswith('__in') and isinstance(v, str):
                v = string_to_list(v)
            rt[k] = v
    return rt


class QuerySetIterationProxy:
    """Iterate a series of object and its associated objects at once

    This iteration proxy applies to this kind of structure especially.

    Group       Properties          Logs
    -------------------------------------------------
    group 1     property 1          log at Mon.
                property 2          log at Tue.
                property 3          log at Wed.
    -------------------------------------------------
    group 2     property 4          log at Mon.
                property 5          log at Tue.
                property 6          log at Wed.
    -------------------------------------------------
    group 3     property 7          log at Mon.
                property 8          log at Tue.
                property 9          log at Wed.

    where, in each row of the table, one or more than one properties and logs
    to be shown along with the group.
    """

    def __init__(self, iterable, associate_name=None, **associated_data):
        """Initialize proxy

        Arguments:
        - iterable: an iterable object representing the main set of objects.
        - associate_name: the attribute name of each object within iterable,
          from which value is retrieve to get associated data from
          associate_data. Default is 'pk'.
        - associate_data: the associated data, that contains all data for each
          item in the set referenced by iterable. You can pass mulitple
          associated data as the way of Python **kwargs. The associated data
          must be grouped by the value of associate_name.
        """
        self._iterable = iter(iterable)
        self._associate_name = associate_name
        if self._associate_name is None:
            self._associate_name = 'pk'
        self._associated_data = associated_data

    def __iter__(self):
        return self

    def next(self):
        next_one = next(self._iterable)
        for name, lookup_table in self._associated_data.items():
            setattr(next_one,
                    name,
                    lookup_table.get(
                        getattr(next_one, self._associate_name, None),
                        ()))
        return next_one

    __next__ = next


class DataTableResult:
    """Paginate and order queryset for rendering DataTable response"""

    DEFAULT_PAGE_SIZE = 20

    def __init__(self,
                 request_data: QueryDict,
                 queryset: QuerySet,
                 column_names: List[str],
                 default_order_key: str = 'pk'):
        self.queryset = queryset
        self.request_data = request_data
        self.column_names = column_names
        self._default_order_key = default_order_key

    def _iter_sorting_columns(self):
        number_of_sorting_cols = int(self.request_data.get('iSortingCols', 0))
        for idx_which_column in range(number_of_sorting_cols):
            sorting_col_index = int(
                self.request_data.get(f'iSortCol_{idx_which_column}', 0))

            sortable_key = f'bSortable_{sorting_col_index}'
            sort_dir_key = f'sSortDir_{idx_which_column}'

            sortable = self.request_data.get(sortable_key, 'false')
            if sortable == 'false':
                continue

            sorting_col_name = self.column_names[sorting_col_index]
            sorting_direction = self.request_data.get(sort_dir_key, 'asc')
            yield sorting_col_name, sorting_direction

    def _sort_result(self):
        sorting_columns = self._iter_sorting_columns()
        order_fields = [f'-{col_name}' if direction == 'desc' else col_name
                        for col_name, direction in sorting_columns]
        if order_fields:
            self.queryset = self.queryset.order_by(*order_fields)
        else:
            # If no order key is specified, sort by pk by default.
            self.queryset = self.queryset.order_by(self._default_order_key)

    def _paginate_result(self):
        display_length = min(
            int(self.request_data.get('iDisplayLength', self.DEFAULT_PAGE_SIZE)),
            100)
        display_start = int(self.request_data.get('iDisplayStart', 0))
        display_end = display_start + display_length
        self.queryset = self.queryset[display_start:display_end]

    def get_response_data(self) -> Dict[str, Any]:
        total_records = total_display_records = self.queryset.count()

        self._sort_result()
        self._paginate_result()

        return {
            'sEcho': int(self.request_data.get('sEcho', 0)),
            'iTotalRecords': total_records,
            'iTotalDisplayRecords': total_display_records,
            'querySet': self.queryset,
        }


def get_model(content_type):
    """Get model class from content type

    :param str content_type: content type in format ``app_label.model_name``.
    :return: model class
    """
    app_label, model_name = content_type.split('.')
    app_config = apps.get_app_config(app_label)
    return app_config.get_model(model_name)


class EnumLike:

    NAME_FIELD = 'name'

    @classmethod
    def get(cls, name):
        criteria = {cls.NAME_FIELD: name}
        return cls.objects.get(**criteria)

    @classmethod
    def as_dict(cls):
        return {
            pk: name for pk, name in cls.objects.values_list('pk', cls.NAME_FIELD)
        }

    @classmethod
    def name_to_id(cls, name):
        criteria = {cls.NAME_FIELD: name}
        obj = cls.objects.filter(**criteria).only('pk').first()
        if obj is None:
            raise ValueError(f'{name} does not exist in model {cls.__name__}')
        return obj.pk

    @classmethod
    def id_to_name(cls, obj_id):
        obj = cls.objects.filter(pk=obj_id).first()
        if obj is None:
            return ValueError('ID {} does not exist in model {}.'.format(
                obj_id, cls.__name__))
        return obj.name


def checksum(value: Union[str, bytes]) -> str:
    if not value:
        return ''
    md5 = hashlib.md5()
    if type(value) == bytes:
        md5.update(value)
    else:
        md5.update(value.encode())
    return md5.hexdigest()


def format_timedelta(timedelta):
    """convert instance of datetime.timedelta to d(ay), h(our), m(inute)"""
    m, s = divmod(timedelta.seconds, 60)
    h, m = divmod(m, 60)
    d = timedelta.days
    day = '%dd' % d if d else ''
    hour = '%dh' % h if h else ''
    minute = '%dm' % m if m else ''
    second = '%ds' % s if s else ''
    timedelta_str = day + hour + minute + second
    return timedelta_str if timedelta_str else '0m'


def timedelta2int(value):
    """convert string nh(ay):nh(our):nm(inute) to integer seconds."""
    value = value.replace(' ', '')
    second_regex = re.compile(r'\d+s')
    minute_regex = re.compile(r'\d+m')
    hour_regex = re.compile(r'\d+h')
    day_regex = re.compile(r'\d+d')

    second = second_regex.findall(value)
    seconds = int(second[0][:-1]) if second else 0

    minute = minute_regex.findall(value)
    minutes = int(minute[0][:-1]) if minute else 0

    hour = hour_regex.findall(value)
    hours = int(hour[0][:-1]) if hour else 0

    day = day_regex.findall(value)
    days = int(day[0][:-1]) if day else 0

    return seconds + minutes * 60 + hours * 3600 + days * 86400

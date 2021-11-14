# -*- coding: utf-8 -*-

from datetime import timedelta

from django import template

register = template.Library()


@register.filter
def timedelta2string(value: timedelta):
    from tcms.core.utils import format_timedelta

    return format_timedelta(value)


@register.filter
def timedelta2seconds(value: timedelta):
    return int(value.seconds + value.days * 86400)

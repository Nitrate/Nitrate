# -*- coding: utf-8 -*-

from django import template

register = template.Library()


@register.simple_tag
def groupby_result_percent(groupby_result, group_item):
    return getattr(groupby_result, f"{group_item}_percent")

# -*- coding: utf-8 -*-
from django.contrib import admin

from tcms import BaseModelAdmin
from tcms.testplans.models import TestPlanType
from tcms.testplans.models import TestPlan


class TestPlanTypeAdmin(BaseModelAdmin):
    search_fields = (('name',))
    list_display = ('id', 'name', 'description')


class TestPlanAdmin(BaseModelAdmin):
    search_fields = (('name',))
    list_filter = ['owner', 'create_date']
    list_display = ('name', 'create_date', 'owner', 'author', 'type')
    list_per_page = 50


admin.site.register(TestPlanType, TestPlanTypeAdmin)
admin.site.register(TestPlan, TestPlanAdmin)

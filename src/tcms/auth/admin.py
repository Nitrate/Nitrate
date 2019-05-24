# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.sites.models import Site
from django.contrib.sites.admin import SiteAdmin
from tcms import BaseModelAdmin


class CustomUserAdmin(BaseModelAdmin, UserAdmin):
    """Customize widgets in User admin change page"""


class CustomGroupAdmin(BaseModelAdmin, GroupAdmin):
    """Customize widgets in Group admin change page"""


class CustomSiteAdmin(BaseModelAdmin, SiteAdmin):
    """Customize widgets in Site admin change page"""


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
admin.site.unregister(Site)
admin.site.register(Site, CustomSiteAdmin)

# -*- coding: utf-8 -*-

from django.contrib import admin
from kobo.django.xmlrpc.models import XmlRpcLog


class NitrateXmlRpcLogAdmin(admin.ModelAdmin):
    list_display = ("happened_on", "user_username", "method")
    list_per_page = 50
    list_filter = ("dt_inserted",)

    user_cache: dict[int, str] = {}

    def __init__(self, *args, **kwargs):
        NitrateXmlRpcLogAdmin.user_cache.clear()
        NitrateXmlRpcLogAdmin.user_cache = {}

        super().__init__(*args, **kwargs)

    @admin.display(description="username")
    def user_username(self, obj) -> str:
        username = NitrateXmlRpcLogAdmin.user_cache.get(obj.user_id)
        if username is None:
            username = obj.user.username
            NitrateXmlRpcLogAdmin.user_cache[obj.user_id] = username
        return username

    @admin.display(description="Happened On")
    def happened_on(self, obj):
        return obj.dt_inserted


admin.site.unregister(XmlRpcLog)
admin.site.register(XmlRpcLog, NitrateXmlRpcLogAdmin)

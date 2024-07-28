# -*- coding: utf-8 -*-

from django.apps import AppConfig as DjangoAppConfig
from django.utils.translation import gettext_lazy as _


class AppConfig(DjangoAppConfig):
    label = "tcms_core"
    name = "tcms.core"
    verbose_name = _("Core App")

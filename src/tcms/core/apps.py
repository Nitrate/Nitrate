# -*- coding: utf-8 -*-

import logging

from django.apps import AppConfig as DjangoAppConfig
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    label = 'core'
    name = 'tcms.core'
    verbose_name = _("Core App")

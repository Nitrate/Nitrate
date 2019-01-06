from django.apps import AppConfig as DjangoAppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(DjangoAppConfig):
    label = 'core'
    name = 'tcms.core'
    verbose_name = _("Core App")

from django.apps import AppConfig as DjangoAppConfig
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def user_klass_clean(self):
    """Add additional validation to avoid using same email address"""
    from django.contrib.auth.models import User

    # Repeat the real work in User.clean
    super(User, self).clean()
    self.email = self.__class__.objects.normalize_email(self.email)

    # Additional checks to validate
    if self.email and User.objects.filter(email=self.email).exists():
        raise ValidationError(f"There is already an existing user with email {self.email}")


def patch_user_model_clean():
    from django.contrib.auth.models import User

    User.clean = user_klass_clean


class AppConfig(DjangoAppConfig):
    name = "tcms.auth"
    label = "tcms_auth"
    verbose_name = _("Core auth")

    def ready(self):
        patch_user_model_clean()

# -*- coding: utf-8 -*-
# FIXME: Use signal to handle log
from tcms.testplans.helpers import email


def notify_on_plan_is_updated(sender, instance, created=False, **kwargs):
    # email changes
    if not created:
        if instance.email_settings.notify_on_plan_update:
            email.email_plan_update(instance)


def load_email_settings_for_later_deletion(sender, instance, **kwargs):
    # Load email settings to ensure it will still be available after this plan
    # is deleted.
    instance.email_settings


def notify_deletion_of_plan(sender, instance, **kwargs):
    # email this deletion
    if instance.email_settings.notify_on_plan_delete:
        email.email_plan_deletion(instance)


def pre_save_clean(sender, **kwargs):
    instance = kwargs["instance"]
    instance.clean()

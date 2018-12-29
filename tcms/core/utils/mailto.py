# -*- coding: utf-8 -*-

import smtplib
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template import loader

from tcms.core.task import Task

logger = logging.getLogger(__name__)


@Task
def mailto(template_name, subject, recipients=None,
           context=None, sender=settings.EMAIL_FROM,
           cc=None, request=None):
    t = loader.get_template(template_name)
    body = t.render(context=context, request=request)

    if settings.DEBUG and settings.EMAILS_FOR_DEBUG:
        recipients = settings.EMAILS_FOR_DEBUG

    if not isinstance(recipients, (list, tuple)):
        recipients = [recipients]

    email_msg = EmailMessage(subject=subject, body=body,
                             from_email=sender, to=recipients, bcc=cc)
    try:
        email_msg.send()
    except smtplib.SMTPException as e:
        logger.exception('Cannot send email. Error: %s', str(e))

# -*- coding: utf-8 -*-

import smtplib
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template import loader
from tcms.core.task import Task
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


def mail_notify(instance, template: str, subject: str, context: Dict[str, str],
                cc: Optional[List[str]] = None):
    recipients = instance.get_notification_recipients()
    if recipients == 0:
        logger.info('No recipient is found. Skip sending mail to notify.')
        return

    log = 'Sending mail "%s" to notify %r.'
    args = [subject, recipients]
    if cc:
        log += ' Also cc %r.'
        args.append(cc)
    logger.info(log, *args)

    mailto(template, subject, recipients, context, cc=cc)


@Task
def mailto(template_name, subject, recipients=None,
           context=None, sender=settings.EMAIL_FROM,
           cc=None, request=None):
    t = loader.get_template(template_name)
    body = t.render(context=context, request=request)

    _recipients = []
    if settings.DEBUG and settings.EMAILS_FOR_DEBUG:
        _recipients.extend(settings.EMAILS_FOR_DEBUG)
    if isinstance(recipients, (list, tuple)):
        _recipients.extend(recipients)
    else:
        _recipients.append(recipients)

    email_msg = EmailMessage(subject=subject, body=body,
                             from_email=sender, to=_recipients, bcc=cc)
    try:
        email_msg.send()
    except smtplib.SMTPException as e:
        logger.exception('Cannot send email. Error: %s', str(e))

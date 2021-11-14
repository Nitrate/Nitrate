# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.sites.models import Site
from django.db import models

logger = logging.getLogger(__name__)


class UrlMixin:
    """Mixin class for getting full URL"""

    def get_full_url(self):
        site_http_scheme = getattr(settings, "SITE_HTTP_SCHEME", None)
        if not site_http_scheme:
            logger.warning(
                "SITE_HTTP_SCHEME is not configured in settings. Use http by default instead."
            )
            site_http_scheme = "http"
        site = Site.objects.get_current()
        return "{}://{}/{}".format(site_http_scheme, site.domain, self.get_absolute_url())


class TCMSContentTypeBaseModel(models.Model):
    """
    TCMS log models.
    The code is from comments contrib from Django
    """

    # Content-object field
    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        verbose_name="content type",
        related_name="content_type_set_for_%(class)s",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    object_pk = models.PositiveIntegerField("object ID", blank=True, null=True)
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    # Metadata about the comment
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE)

    class Meta:
        abstract = True

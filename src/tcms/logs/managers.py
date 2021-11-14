# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.db import models


class TCMSLogManager(models.Manager):
    def for_model(self, model):
        """
        QuerySet for all comments for a particular model (either an instance or
        a class).
        """
        ct = ContentType.objects.get_for_model(model)
        qs = self.get_queryset().filter(content_type=ct)
        if isinstance(model, models.Model):
            qs = qs.filter(object_pk=model.pk)
        return qs

# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_str

from .models import TCMSLogModel


class TCMSLog:
    """TCMS Log"""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def get_new_log_object(self):
        elements = ["who", "field", "original_value", "new_value"]

        for element in elements:
            if not hasattr(self, element):
                raise NotImplementedError(f"Log does not have attribute {element}")

        model = self.get_log_model()
        new = model(**self.get_log_create_data())

        return new

    def get_log_model(self):
        """
        Get the log model to create with this class.
        """
        return TCMSLogModel

    def get_log_create_data(self):
        return {
            "content_object": self.model,
            "site_id": settings.SITE_ID,
            "who": self.who,
            "field": self.field,
            "original_value": self.original_value,
            "new_value": self.new_value,
        }

    def make(self, who, new_value, field=None, original_value=None):
        """Create new log"""
        self.who = who
        self.field = field or ""
        self.original_value = original_value or ""
        self.new_value = new_value

        model = self.get_new_log_object()
        model.save()

    def lookup_content_type(self):
        return ContentType.objects.get_for_model(self.model)

    def get_query_set(self):
        ctype = self.lookup_content_type()
        model = self.get_log_model()

        qs = model.objects.filter(
            content_type=ctype,
            object_pk=smart_str(self.model.pk),
            site=settings.SITE_ID,
        )
        qs = qs.select_related("who")
        return qs

    def list(self):
        """List the logs"""
        return self.get_query_set().all()

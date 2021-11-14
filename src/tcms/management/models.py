# -*- coding: utf-8 -*-

import os.path
from typing import List

from django.conf import settings
from django.core.cache import cache
from django.db import models

from tcms.core.models import TCMSActionModel
from tcms.core.models.fields import NitrateBooleanField
from tcms.core.utils import calc_percent

# FIXME: plugins_support is no longer available. dead code here.
try:
    from tcms.plugins_support.signals import register_model
except ImportError:
    register_model = None

# Products zone


def get_as_choices(iterable, allow_blank):
    # Generate a list of (id, string) pairs suitable
    # for a ChoiceField's "choices".
    #
    # Prepend with a blank entry if "allow_blank" is True
    #
    # Turn each object in the list into a choice
    # using its "as_choice" method
    if allow_blank:
        result = [("", "")]
    else:
        result = []
    result += [obj.as_choice() for obj in iterable]
    return result


def get_all_choices(cls, allow_blank=True):
    # Generate a list of (id, string) pairs suitable
    # for a ChoiceField's "choices", based on all instances of a class:
    return get_as_choices(cls.objects.all(), allow_blank)


class Classification(TCMSActionModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=64)
    description = models.TextField(blank=True)
    sortkey = models.IntegerField(default=0)

    class Meta:
        db_table = "classifications"

    def __str__(self):
        return self.name


class Product(TCMSActionModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=64)
    classification = models.ForeignKey(Classification, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    milestone_url = models.CharField(db_column="milestoneurl", max_length=128, default="---")
    disallow_new = models.BooleanField(db_column="disallownew", default=False)
    vote_super_user = models.IntegerField(db_column="votesperuser", null=True, default=True)
    max_vote_super_bug = models.IntegerField(db_column="maxvotesperbug", default=10000)
    votes_to_confirm = models.BooleanField(db_column="votestoconfirm", default=False)
    default_milestone = models.CharField(db_column="defaultmilestone", max_length=20, default="---")

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name

    @classmethod
    def to_xmlrpc(cls, query=None):
        from tcms.xmlrpc.serializer import ProductXMLRPCSerializer

        _query = query or {}
        qs = cls.objects.filter(**_query).order_by("pk")
        s = ProductXMLRPCSerializer(model_class=cls, queryset=qs)
        return s.serialize_queryset()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.category.get_or_create(name="--default--")
        self.version.get_or_create(value="unspecified")
        self.build.get_or_create(name="unspecified")

    def get_version_choices(self, allow_blank):
        # Generate a list of (id, string) pairs suitable
        # for a ChoiceField's "choices":
        return get_as_choices(self.version.all(), allow_blank)

    def get_build_choices(self, allow_blank, only_active):
        # Generate a list of (id, string) pairs suitable
        # for a ChoiceField's "choices"
        #
        # @only_active: restrict to only show builds flagged as "active"
        q = self.build
        if only_active:
            q = q.filter(is_active=True)
        return get_as_choices(q.all(), allow_blank)

    def get_environment_choices(self, allow_blank):
        # Generate a list of (id, string) pairs suitable
        # for a ChoiceField's "choices":
        return get_as_choices(self.environments.all(), allow_blank)

    @classmethod
    def get_choices(cls, allow_blank):
        # Generate a list of (id, string) pairs suitable
        # for a ChoiceField's "choices":
        return get_as_choices(cls.objects.order_by("name").all(), allow_blank)

    def as_choice(self):
        return (self.id, self.name)


class Priority(TCMSActionModel):
    id = models.AutoField(primary_key=True)
    value = models.CharField(unique=True, max_length=64)
    sortkey = models.IntegerField(default=0)
    is_active = models.BooleanField(db_column="isactive", default=True)

    class Meta:
        db_table = "priority"
        verbose_name_plural = "priorities"

    def __str__(self):
        return self.value

    cache_key_values = "priority__value"

    @classmethod
    def get_values(cls):
        values = cache.get(cls.cache_key_values)
        if values is None:
            values = dict(cls.objects.values_list("pk", "value").iterator())
            cache.set(cls.cache_key_values, values)
        return values

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        cache.delete(self.cache_key_values)
        return result


class Milestone(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    value = models.CharField(unique=True, max_length=60)
    sortkey = models.IntegerField(default=0)

    class Meta:
        db_table = "milestones"

    def __str__(self):
        return self.value


class Component(TCMSActionModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=64)
    product = models.ForeignKey(Product, related_name="component", on_delete=models.CASCADE)
    initial_owner = models.ForeignKey(
        "auth.User",
        null=True,
        db_column="initialowner",
        related_name="initialowner",
        on_delete=models.CASCADE,
    )
    initial_qa_contact = models.ForeignKey(
        "auth.User",
        blank=True,
        null=True,
        db_column="initialqacontact",
        related_name="initialqacontact",
        on_delete=models.CASCADE,
    )
    description = models.TextField()

    # Auto-generated attributes from back-references:
    #   'cases' : list of TestCases (from TestCases.components)

    class Meta:
        db_table = "components"
        unique_together = ("product", "name")

    def __str__(self):
        return self.name


class Version(TCMSActionModel):
    id = models.AutoField(primary_key=True)
    value = models.CharField(max_length=192)
    product = models.ForeignKey(Product, related_name="version", on_delete=models.CASCADE)

    class Meta:
        db_table = "versions"
        unique_together = ("product", "value")

    def __str__(self):
        return self.value

    @classmethod
    def string_to_id(cls, product_id, value):
        try:
            return cls.objects.get(product__id=product_id, value=value).pk
        except cls.DoesNotExist:
            return None

    def as_choice(self):
        return (self.id, self.value)


#  Test builds zone
class TestBuildManager(models.Manager):

    pass


#    def get_plans_count(self):
#        return sum(self.values_list('plans_count', flat=True))


class TestBuild(TCMSActionModel):
    build_id = models.AutoField(unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    milestone = models.CharField(max_length=20, default="---")
    description = models.TextField(blank=True)
    is_active = NitrateBooleanField(db_column="isactive", default=True)
    objects = TestBuildManager()

    product = models.ForeignKey(Product, related_name="build", on_delete=models.CASCADE)

    class Meta:
        db_table = "test_builds"
        unique_together = ("product", "name")
        verbose_name = "build"
        verbose_name_plural = "builds"

    @classmethod
    def to_xmlrpc(cls, query=None):
        from tcms.xmlrpc.serializer import TestBuildXMLRPCSerializer

        _query = query or {}
        qs = cls.objects.filter(**_query).order_by("pk")
        s = TestBuildXMLRPCSerializer(model_class=cls, queryset=qs)
        return s.serialize_queryset()

    @classmethod
    def list(cls, query):
        q = cls.objects

        if query.get("build_id"):
            q = q.filter(build_id=query["build_id"])
        if query.get("name"):
            q = q.filter(name=query["name"])
        if query.get("product"):
            q = q.filter(product=query["product"])
        if query.get("milestone"):
            q = q.filter(milestone=query["milestone"])
        if query.get("is_active"):
            q = q.filter(is_active=query["is_active"])

        product_ids = query.get("product_ids")
        if product_ids is not None:
            assert isinstance(product_ids, list)
            q = q.filter(product__in=product_ids)

        return q.all()

    @classmethod
    def list_active(cls, query={}):
        if isinstance(query, dict):
            query["is_active"] = True
        return cls.list(query)

    def __str__(self):
        return self.name

    def as_choice(self):
        return (self.build_id, self.name)

    def get_case_runs_failed_percent(self):
        if hasattr(self, "case_runs_failed_count"):
            return calc_percent(self.case_runs_failed_count, self.case_runs_count)
        else:
            return None

    def get_case_runs_passed_percent(self):
        if hasattr(self, "case_runs_passed_count"):
            return calc_percent(self.case_runs_passed_count, self.case_runs_count)
        else:
            return None


# Test environments zone


class TestEnvironment(TCMSActionModel):
    environment_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(db_column="isactive", default=True)

    product = models.ForeignKey(Product, related_name="environments", on_delete=models.CASCADE)

    class Meta:
        db_table = "test_environments"

    def __str__(self):
        return self.name

    def as_choice(self):
        return (self.environment_id, self.name)


class TestEnvironmentCategory(models.Model):
    env_category_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=255, blank=True)

    product = models.ForeignKey(
        Product, related_name="environment_categories", on_delete=models.CASCADE
    )

    class Meta:
        db_table = "test_environment_category"
        index_together = (("env_category_id", "product"), ("product", "name"))

    def __str__(self):
        return self.name


class TestEnvironmentElement(models.Model):
    element_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=255, blank=True)
    is_private = models.BooleanField(db_column="isprivate", default=False)

    env_category = models.ForeignKey(TestEnvironmentCategory, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        "self", null=True, related_name="parent_set", on_delete=models.SET_NULL
    )

    class Meta:
        db_table = "test_environment_element"

    def __str__(self):
        return self.name


class TestEnvironmentProperty(models.Model):
    property_id = models.IntegerField(primary_key=True)
    name = models.CharField(unique=True, max_length=255, blank=True)
    valid_express = models.TextField(db_column="validexp", blank=True)

    element = models.ForeignKey(TestEnvironmentElement, on_delete=models.CASCADE)

    class Meta:
        db_table = "test_environment_property"

    def __str__(self):
        return self.name


class TestEnvironmentMap(models.Model):
    value_selected = models.TextField(blank=True)

    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE)
    property = models.ForeignKey(TestEnvironmentProperty, on_delete=models.CASCADE)
    element = models.ForeignKey(TestEnvironmentElement, on_delete=models.CASCADE)

    class Meta:
        db_table = "test_environment_map"
        # FIXME: is unique_together against environment and property necessary?

    def __str__(self):
        return self.value_selected


# Test tag zone


class TestTag(TCMSActionModel):
    id = models.AutoField(db_column="tag_id", primary_key=True)
    name = models.CharField(db_column="tag_name", max_length=255)

    class Meta:
        db_table = "test_tags"
        verbose_name = "tag"
        verbose_name_plural = "tags"

    def __str__(self):
        return self.name

    @classmethod
    def string_to_list(cls, string) -> List[str]:
        from tcms.core.utils import string_to_list

        return string_to_list(string)

    @classmethod
    def get_or_create_many_by_name(cls, names):
        tags = []
        for name in names:
            new_tag = cls.objects.get_or_create(name=name)[0]
            tags.append(new_tag)
        return tags


# Test attachements file zone


def attachment_stored_filename(stored_name: str) -> str:
    return os.path.join(settings.FILE_UPLOAD_DIR, stored_name).replace("\\", "/")


class TestAttachment(models.Model):
    attachment_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=1024, blank=True, null=True)
    file_name = models.CharField(db_column="filename", max_length=255, unique=True, blank=True)
    stored_name = models.CharField(max_length=128, unique=True, blank=True, null=True)
    create_date = models.DateTimeField(db_column="creation_ts", auto_now_add=True)
    mime_type = models.CharField(max_length=100)
    checksum = models.CharField(
        max_length=32, unique=True, help_text="MD5 checksum of this uploaded file."
    )

    submitter = models.ForeignKey(
        "auth.User",
        blank=True,
        null=True,
        related_name="attachments",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return self.file_name

    class Meta:
        db_table = "test_attachments"

    @property
    def stored_filename(self) -> str:
        return attachment_stored_filename(self.stored_name)


class TestAttachmentData(models.Model):
    contents = models.BinaryField(blank=True)
    attachment = models.OneToOneField(TestAttachment, on_delete=models.CASCADE)

    class Meta:
        db_table = "test_attachment_data"


# ============================
# New TCMS Environments models
# ============================


class TCMSEnvGroup(TCMSActionModel):
    name = models.CharField(unique=True, max_length=255)
    is_active = models.BooleanField(default=True)

    manager = models.ForeignKey(
        "auth.User", related_name="env_group_manager", on_delete=models.CASCADE
    )

    modified_by = models.ForeignKey(
        "auth.User",
        blank=True,
        null=True,
        related_name="env_group_modifier",
        on_delete=models.CASCADE,
    )

    property = models.ManyToManyField(
        "management.TCMSEnvProperty",
        through="management.TCMSEnvGroupPropertyMap",
        related_name="group",
    )

    class Meta:
        db_table = "tcms_env_groups"

    def __str__(self):
        return self.name

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True)


class TCMSEnvProperty(TCMSActionModel):
    name = models.CharField(unique=True, max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tcms_env_properties"

    def __str__(self):
        return self.name

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).order_by("name")


class TCMSEnvGroupPropertyMap(models.Model):
    group = models.ForeignKey(TCMSEnvGroup, on_delete=models.CASCADE)
    property = models.ForeignKey(TCMSEnvProperty, on_delete=models.CASCADE)

    class Meta:
        db_table = "tcms_env_group_property_map"


class TCMSEnvValue(TCMSActionModel):
    value = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    # TODO: rename value to values
    property = models.ForeignKey(TCMSEnvProperty, related_name="value", on_delete=models.CASCADE)

    class Meta:
        db_table = "tcms_env_values"
        unique_together = ("property", "value")

    def __str__(self):
        return self.value

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True)


# FIXME: plugins_support is no longer available, this is dead code.
if register_model:
    register_model(Classification)
    register_model(Product)
    register_model(Priority)
    register_model(Version)
    register_model(TestBuild)
    register_model(TestTag)
    register_model(Component)
    register_model(TCMSEnvGroup)
    register_model(TCMSEnvValue)
    register_model(TestAttachment)

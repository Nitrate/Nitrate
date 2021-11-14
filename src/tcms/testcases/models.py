# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Max, ObjectDoesNotExist, QuerySet
from django.db.models.aggregates import Count
from django.db.models.signals import post_delete, post_save, pre_save
from django.urls import reverse
from django.utils.encoding import smart_str
from html2text import html2text

from tcms.core.models import TCMSActionModel, TCMSContentTypeBaseModel
from tcms.core.models.fields import DurationField
from tcms.core.utils import EnumLike, checksum, format_timedelta
from tcms.issuetracker.models import Issue
from tcms.issuetracker.services import find_service
from tcms.management.models import Component
from tcms.testcases import signals as case_watchers

try:
    from tcms.plugins_support.signals import register_model
except ImportError:
    register_model = None

AUTOMATED_CHOICES = (
    (0, "Manual"),
    (1, "Auto"),
    (2, "Both"),
)

log = logging.getLogger(__name__)


class NoneText:
    author = None
    case_text_version = 0
    action = ""
    effect = ""
    setup = ""
    breakdown = ""
    create_date = datetime.now()

    @classmethod
    def serialize(cls):
        return {}


class PlainText:
    """Contains plain text converted from four text"""

    def __init__(self, action, setup, effect, breakdown):
        self.action = action
        self.setup = setup
        self.effect = effect
        self.breakdown = breakdown


class TestCaseStatus(EnumLike, TCMSActionModel):
    id = models.AutoField(db_column="case_status_id", primary_key=True)
    # FIXME: if name has unique value for each status, give unique constraint
    # to this field. Otherwise, all SQL queries filtering upon this
    #        field will cost much time in the database side.
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "test_case_status"
        verbose_name = "Test case status"
        verbose_name_plural = "Test case status"

    def __str__(self):
        return self.name

    def is_confirmed(self):
        return self.name == "CONFIRMED"


class TestCaseCategory(TCMSActionModel):
    id = models.AutoField(db_column="category_id", primary_key=True)
    name = models.CharField(max_length=255)
    product = models.ForeignKey(
        "management.Product", related_name="category", on_delete=models.CASCADE
    )
    description = models.TextField(blank=True)

    class Meta:
        db_table = "test_case_categories"
        verbose_name_plural = "test case categories"
        unique_together = ("product", "name")

    def __str__(self):
        return self.name


class TestCase(TCMSActionModel):
    case_id = models.AutoField(primary_key=True)
    create_date = models.DateTimeField(db_column="creation_date", auto_now_add=True)
    is_automated = models.IntegerField(db_column="isautomated", default=0)
    is_automated_proposed = models.BooleanField(default=False)
    script = models.TextField(blank=True)
    arguments = models.TextField(blank=True)
    extra_link = models.CharField(max_length=1024, default=None, blank=True, null=True)
    summary = models.CharField(max_length=255, blank=True)
    requirement = models.CharField(max_length=255, blank=True)
    alias = models.CharField(max_length=255, blank=True)
    estimated_time = DurationField(db_column="estimated_time", default=0)
    notes = models.TextField(blank=True)

    case_status = models.ForeignKey(TestCaseStatus, on_delete=models.CASCADE)
    category = models.ForeignKey(
        TestCaseCategory, related_name="category_case", on_delete=models.CASCADE
    )
    priority = models.ForeignKey(
        "management.Priority", related_name="priority_case", on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        "auth.User", related_name="cases_as_author", on_delete=models.CASCADE
    )
    default_tester = models.ForeignKey(
        "auth.User",
        blank=True,
        null=True,
        related_name="cases_as_default_tester",
        on_delete=models.SET_NULL,
    )
    reviewer = models.ForeignKey(
        "auth.User",
        blank=True,
        null=True,
        related_name="cases_as_reviewer",
        on_delete=models.SET_NULL,
    )

    attachments = models.ManyToManyField(
        "management.TestAttachment",
        related_name="cases",
        through="testcases.TestCaseAttachment",
    )

    # FIXME: related_name should be cases instead of case. But now keep it
    # named case due to historical reason.
    plan = models.ManyToManyField(
        "testplans.TestPlan", related_name="case", through="testcases.TestCasePlan"
    )

    component = models.ManyToManyField(
        "management.Component",
        related_name="cases",
        through="testcases.TestCaseComponent",
    )

    tag = models.ManyToManyField(
        "management.TestTag", related_name="cases", through="testcases.TestCaseTag"
    )

    # Auto-generated attributes from back-references:
    # 'texts' : list of TestCaseTexts (from TestCaseTexts.case)
    class Meta:
        db_table = "test_cases"

    def __str__(self):
        return self.summary

    @classmethod
    def to_xmlrpc(cls, query=None):
        from tcms.xmlrpc.serializer import TestCaseXMLRPCSerializer
        from tcms.xmlrpc.utils import distinct_filter

        _query = query or {}
        qs = distinct_filter(TestCase, _query).order_by("pk")
        s = TestCaseXMLRPCSerializer(model_class=cls, queryset=qs)
        return s.serialize_queryset()

    @classmethod
    def create(cls, author, values, plans=None):
        """
        Create the case element based on models/forms.
        """
        case = cls.objects.create(
            author=author,
            is_automated=values["is_automated"],
            is_automated_proposed=values["is_automated_proposed"],
            script=values["script"],
            arguments=values["arguments"],
            extra_link=values["extra_link"],
            summary=values["summary"],
            requirement=values["requirement"],
            alias=values["alias"],
            estimated_time=values["estimated_time"],
            case_status=values["case_status"],
            category=values["category"],
            priority=values["priority"],
            default_tester=values["default_tester"],
            notes=values["notes"],
        )

        tags = values.get("tag")
        if tags:
            for tag in tags:
                case.add_tag(tag)

        components = values.get("component")
        if components is not None:
            for component in components:
                case.add_component(component=component)

        if plans:
            for plan in plans:
                case.add_to_plan(plan)

        return case

    @classmethod
    def update(cls, case_ids, values):
        if isinstance(case_ids, int):
            case_ids = [
                case_ids,
            ]

        fields = [field.name for field in cls._meta.fields]

        tcs = cls.objects.filter(pk__in=case_ids)
        _values = {k: v for k, v in values.items() if k in fields and v is not None and v != ""}
        if values["notes"] == "":
            _values["notes"] = ""
        if values["script"] == "":
            _values["script"] = ""
        tcs.update(**_values)
        return tcs

    @classmethod
    def list(cls, query, plan=None):
        """List the cases with request"""
        from django.db.models import Q

        if not plan:
            q = cls.objects
        else:
            q = cls.objects.filter(plan=plan)

        if query.get("case_id_set"):
            q = q.filter(pk__in=query["case_id_set"])

        if query.get("search"):
            q = q.filter(
                Q(pk__icontains=query["search"])
                | Q(summary__icontains=query["search"])
                | Q(author__email__startswith=query["search"])
            )

        if query.get("summary"):
            q = q.filter(Q(summary__icontains=query["summary"]))

        if query.get("author"):
            q = q.filter(
                Q(author__first_name__startswith=query["author"])
                | Q(author__last_name__startswith=query["author"])
                | Q(author__username__icontains=query["author"])
                | Q(author__email__startswith=query["author"])
            )

        if query.get("default_tester"):
            q = q.filter(
                Q(default_tester__first_name__startswith=query["default_tester"])
                | Q(default_tester__last_name__startswith=query["default_tester"])
                | Q(default_tester__username__icontains=query["default_tester"])
                | Q(default_tester__email__startswith=query["default_tester"])
            )

        if query.get("tag__name__in"):
            q = q.filter(tag__name__in=query["tag__name__in"])

        if query.get("category"):
            q = q.filter(category__name=query["category"].name)

        if query.get("priority"):
            q = q.filter(priority__in=query["priority"])

        if query.get("case_status"):
            q = q.filter(case_status__in=query["case_status"])

        # If plan exists, remove leading and trailing whitespace from it.
        plan_str = query.get("plan", "").strip()
        if plan_str:
            try:
                # Is it an integer?  If so treat as a plan_id:
                plan_id = int(plan_str)
                q = q.filter(plan__plan_id=plan_id)
            except ValueError:
                # Not an integer - treat plan_str as a plan name:
                q = q.filter(plan__name__icontains=plan_str)
        del plan_str

        if query.get("product"):
            q = q.filter(category__product=query["product"])

        if query.get("component"):
            q = q.filter(component=query["component"])

        if query.get("issue_key"):
            q = q.filter(issues__issue_key__in=query["issue_key"])

        if query.get("is_automated"):
            q = q.filter(is_automated=query["is_automated"])

        if query.get("is_automated_proposed"):
            q = q.filter(is_automated_proposed=query["is_automated_proposed"])

        return q.distinct()

    @classmethod
    def list_confirmed(cls):
        return cls.list({"case_status__name": "CONFIRMED"})

    @staticmethod
    def mail_scene(
        objects: QuerySet,
        field: Optional[str] = None,
        value=None,
        ctype=None,
        object_pk=None,
    ):
        tcs = objects.select_related("reviewer").only("summary", "reviewer__email").order_by("pk")
        tc: TestCase
        scence_templates = {
            "reviewer": {
                "template_name": "mail/change_case_reviewer.txt",
                "subject": "You have been the reviewer of cases",
                "recipients": list(set(tcs.values_list("reviewer__email", flat=True))),
                "context": {
                    "test_cases": [
                        {
                            "pk": tc.pk,
                            "summary": tc.summary,
                            "full_url": tc.get_full_url(),
                        }
                        for tc in tcs
                    ],
                },
            }
        }

        return scence_templates.get(field)

    def add_issue(
        self,
        issue_key,
        issue_tracker,
        summary=None,
        description=None,
        case_run=None,
        link_external_tracker=False,
    ):
        """Add issue to case or case run

        :param str issue_key: issue key to add.
        :param issue_tracker: to which the issue is added.
        :type issue_tracker: :class:`IssueTracker`
        :param str summary: issue's summary. It's optional.
        :param str description: a longer description for the issue. It's
            optional.
        :param case_run: If specified, that means issue is added to a test case
            run and also associated with this case. If omitted, it just means
            issue is added to this case only.
        :type case_run: :class:`TestCaseRun`
        :param bool link_external_tracker: whether to add the issue to issue
            tracker's external tracker just after issue is added. Default to
            not to do that.
        :return: newly created issue. If issue already exists (checking the
            existence of issue key), nothing changes and just return
            immediately with None.
        :rtype: :class:`Issue`
        :raises ValueError: if passed case run is not associated with this case.

        .. versionchanged:: 4.2
           ``bug_id`` is replaced with ``issue_key``. ``bug_system_id`` is
           replaced with ``issue_tracker``.
        """
        if case_run and case_run.case != self:
            raise ValueError("Case run {} is not associated with case {}".format(case_run, self))

        existing_issue = (
            Issue.objects.filter(issue_key=issue_key, tracker=issue_tracker)
            .only("issue_key")
            .first()
        )
        if existing_issue is not None:
            log.info("Issue %s already exist. Skip add.", issue_key)
            return existing_issue

        issue = Issue(
            issue_key=issue_key,
            tracker=issue_tracker,
            case=self,
            case_run=case_run,
            summary=summary,
            description=description,
        )
        issue.full_clean()
        issue.save()

        if link_external_tracker:
            service = find_service(issue_tracker)
            service.add_external_tracker(issue_key)

        return issue

    def add_component(self, component: Component):
        """Add a component

        Relationship between case and component is unique. A same component
        with same pk is not added.

        :param component: component to be added.
        :type component: :class:`Component`
        :return: the object representing relationship between this case and the
            component. If component is already added to this case, nothing will
            happen and ``None`` will be returned.
        :rtype: :class:`TestCaseComponent`.
        """
        manager = TestCaseComponent.objects
        if manager.filter(case=self, component=component).exists():
            return
        else:
            return manager.create(case=self, component=component)

    def add_tag(self, tag):
        return TestCaseTag.objects.get_or_create(case=self, tag=tag)

    def update_tags(self, new_tags):
        """Update case.tag so that case.tag == new_tags

        :param list new_tags: list of tags to be updated to this case. Each of
            them is an instance of :class:`TestTag`.
        """
        if new_tags is None or not isinstance(new_tags, list):
            return
        owning_tags = set(self.tag.iterator())
        new_tags = set(new_tags)
        tags_to_remove = owning_tags.difference(new_tags)
        tags_to_add = new_tags.difference(owning_tags)
        for tag in tags_to_add:
            self.add_tag(tag)
        for tag in tags_to_remove:
            self.remove_tag(tag)

    def add_text(
        self,
        action: str,
        effect: str,
        setup: str,
        breakdown: str,
        author=None,
        create_date=None,
        case_text_version: int = 1,
        action_checksum: Optional[str] = None,
        effect_checksum: Optional[str] = None,
        setup_checksum: Optional[str] = None,
        breakdown_checksum: Optional[str] = None,
    ):
        if not author:
            author = self.author

        new_action_checksum = checksum(action)
        new_effect_checksum = checksum(effect)
        new_setup_checksum = checksum(setup)
        new_breakdown_checksum = checksum(breakdown)

        old_action, old_effect, old_setup, old_breakdown = self.text_checksum()
        if (
            old_action != new_action_checksum
            or old_effect != new_effect_checksum
            or old_setup != new_setup_checksum
            or old_breakdown != new_breakdown_checksum
        ):
            case_text_version = self.latest_text_version() + 1

            latest_text = TestCaseText.objects.create(
                case=self,
                case_text_version=case_text_version,
                create_date=create_date or datetime.now(),
                author=author,
                action=action,
                effect=effect,
                setup=setup,
                breakdown=breakdown,
                action_checksum=action_checksum or new_action_checksum,
                effect_checksum=effect_checksum or new_effect_checksum,
                setup_checksum=setup_checksum or new_setup_checksum,
                breakdown_checksum=breakdown_checksum or new_breakdown_checksum,
            )
        else:
            latest_text = self.latest_text()

        return latest_text

    def add_to_plan(self, plan):
        TestCasePlan.objects.get_or_create(case=self, plan=plan)

    def clear_estimated_time(self):
        """Converts a integer to time"""
        return format_timedelta(self.estimated_time)

    def get_issues(self):
        return Issue.objects.filter(case__pk=self.pk).select_related("tracker", "case_run")

    def get_choiced(self, obj_value, choices):
        for x in choices:
            if x[0] == obj_value:
                return x[1]

    def get_is_automated(self):
        return self.get_choiced(self.is_automated, AUTOMATED_CHOICES)

    def get_is_automated_form_value(self):
        if self.is_automated == 2:
            return [0, 1]

        return (self.is_automated,)

    def get_is_automated_status(self):
        return self.get_is_automated() + (self.is_automated_proposed and " (Autoproposed)" or "")

    def get_previous_and_next(self, pk_list):
        pk_list = list(pk_list)
        if self.pk not in pk_list:
            return None, None
        current_idx = pk_list.index(self.pk)
        prev = TestCase.objects.get(pk=pk_list[current_idx - 1])
        next_pk = (current_idx + 1) % len(pk_list)
        next_ = TestCase.objects.get(pk=pk_list[next_pk])
        return prev, next_

    def get_text_with_version(self, case_text_version: Optional[int] = None):
        if case_text_version:
            try:
                return TestCaseText.objects.get(
                    case__case_id=self.case_id, case_text_version=case_text_version
                )
            except TestCaseText.DoesNotExist:
                return NoneText

        return self.latest_text()

    def latest_text(self, text_required=True):
        text = self.text
        if not text_required:
            text = text.defer("action", "effect", "setup", "breakdown")
        qs = text.order_by("-case_text_version")[0:1]
        return NoneText if len(qs) == 0 else qs[0]

    def latest_text_version(self):
        result = self.text.order_by("case", "case_text_version").aggregate(
            latest_version=Max("case_text_version")
        )
        latest_version = result["latest_version"]
        return 0 if latest_version is None else latest_version

    def text_exist(self):
        return self.text.exists()

    def text_checksum(self):
        qs = self.text.order_by("-case_text_version").only(
            "action_checksum", "effect_checksum", "setup_checksum", "breakdown_checksum"
        )[0:1]
        if len(qs) == 0:
            return None, None, None, None
        else:
            text = qs[0]
            return (
                text.action_checksum,
                text.effect_checksum,
                text.setup_checksum,
                text.breakdown_checksum,
            )

    def mail(self, template, subject, context={}, to=[], request=None):
        from tcms.core.mailto import mailto

        if not to:
            to = self.author.email

        to = list(set(to))
        mailto(template, subject, to, context, request=request)

    def remove_issue(self, issue_key, case_run=None):
        """Remove issue from this case or case run together

        :param str issue_key: Issue key to be removed.
        :param case_run: object of TestCaseRun or an integer representing a
            test case run pk. If omitted, only remove issue key from this case.
        :type case_run: :class:`TestCaseRun` or int
        :return: True if issue is removed, otherwise False is returned.
        :rtype: bool
        :raises TypeError: if type of argument ``case_run`` is not recognized.
        :raises ValueError: if test case run represented by argument ``case_run`` is
            not associated with this case.
        """
        from tcms.testruns.models import TestCaseRun

        if case_run is not None:
            if isinstance(case_run, TestCaseRun):
                case_run_id = case_run.pk
                rel_exists = case_run.case == self
            elif isinstance(case_run, int):
                case_run_id = case_run
                rel_exists = TestCaseRun.objects.filter(pk=case_run, case=self).exists()
            else:
                raise TypeError("Argument case_run should be an object of TestCaseRun or an int.")
            if not rel_exists:
                raise ValueError(
                    "Case run {} is not associated with case {}.".format(case_run_id, self.pk)
                )

        criteria = {"issue_key": issue_key, "case": self}
        if case_run is None:
            criteria["case_run__isnull"] = True
        else:
            criteria["case_run"] = case_run
        num_deletes, _ = Issue.objects.filter(**criteria).delete()
        return num_deletes > 0

    def remove_component(self, component):
        TestCaseComponent.objects.filter(case=self, component=component).delete()

    def remove_plan(self, plan):
        self.plan.through.objects.filter(case=self.pk, plan=plan.pk).delete()

    def remove_tag(self, tag):
        self.tag.through.objects.filter(case=self.pk, tag=tag.pk).delete()

    def get_absolute_url(self, request=None):
        return reverse(
            "case-get",
            args=[
                self.pk,
            ],
        )

    def _get_email_conf(self):
        try:
            return self.email_settings
        except ObjectDoesNotExist:
            return TestCaseEmailSettings.objects.create(case=self)

    emailing = property(_get_email_conf)

    def clone(
        self,
        to_plans,
        author=None,
        default_tester=None,
        source_plan=None,
        copy_attachment=True,
        copy_component=True,
        component_initial_owner=None,
    ):
        """Clone this case to plans

        :param to_plans: list of test plans this case will be cloned to.
        :type to_plans: list[TestPlan]
        :param author: set the author for the cloned test case. If omitted,
            original author will be used.
        :type author: django.contrib.auth.models.User or None
        :param default_tester: set the default tester for the cloned test case.
            If omitted, original author will be used.
        :type default_tester: django.contrib.auth.models.User or None
        :param source_plan: a test plan this case belongs to. If set, sort key
            of the relationship between this case and this plan will be set to
            the new relationship of cloned case and destination plan.
            Otherwise, new sort key will be calculated from the destination
            plan.
        :type source_plan: TestPlan or None
        :param bool copy_attachment: whether to copy attachments.
        :param bool copy_component: whether to copy components.
        :param component_initial_owner: the initial owner of copied component.
            This argument is only used when ``copy_component`` is set to True.
        :type component_initial_owner: django.contrib.auth.models.User or None
        :return: the cloned test case
        :rtype: TestCase
        """
        cloned_case = TestCase.objects.create(
            is_automated=self.is_automated,
            is_automated_proposed=self.is_automated_proposed,
            script=self.script,
            arguments=self.arguments,
            extra_link=self.extra_link,
            summary=self.summary,
            requirement=self.requirement,
            alias=self.alias,
            estimated_time=self.estimated_time,
            case_status=TestCaseStatus.get("PROPOSED"),
            category=self.category,
            priority=self.priority,
            notes=self.notes,
            author=author or self.author,
            default_tester=default_tester or self.author,
        )

        src_latest_text = self.latest_text()
        cloned_case.add_text(
            author=author,
            create_date=src_latest_text.create_date,
            action=src_latest_text.action,
            effect=src_latest_text.effect,
            setup=src_latest_text.setup,
            breakdown=src_latest_text.breakdown,
        )

        # The original tags are not copied actually. They are just
        # linked to the new cloned test case.
        for tag in self.tag.all():
            cloned_case.add_tag(tag=tag)

        # The original attachments are not copied actually. They
        # are just linked to the new cloned test case.
        if copy_attachment:
            TestCaseAttachment.objects.bulk_create(
                [
                    TestCaseAttachment(case=cloned_case, attachment=item)
                    for item in self.attachments.all()
                ]
            )

        rel = TestCasePlan.objects.filter(plan=source_plan, case=self).first()

        for plan in to_plans:
            if source_plan is None:
                sort_key = plan.get_case_sortkey()
            else:
                sort_key = rel.sortkey if rel else plan.get_case_sortkey()
            plan.add_case(cloned_case, sort_key)

            # Clone the categories to new product
            categories = plan.product.category
            try:
                tc_category = categories.get(name=self.category.name)
            except ObjectDoesNotExist:
                tc_category = categories.create(
                    name=self.category.name,
                    description=self.category.description,
                )
            cloned_case.category = tc_category
            cloned_case.save()

            # Clone the components to new product
            if copy_component:
                components = plan.product.component
                for component in self.component.all():
                    try:
                        new_c = components.get(name=component.name)
                    except ObjectDoesNotExist:
                        new_c = components.create(
                            name=component.name,
                            initial_owner=component_initial_owner,
                            description=component.description,
                        )

                    cloned_case.add_component(new_c)

        return cloned_case

    def transition_to_plans(self, to_plans, author=None, default_tester=None, source_plan=None):
        """Transition this case to other plans

        This method will link this case to specified test plans and no change
        to the original relationship between this case and other test plans it
        was associated with.

        :param to_plans: the test plans this case is transitioned to.
        :type to_plans: list[TestPlan]
        :param author: same as the argument ``author`` of :meth:`TestCase.clone`.
        :type author: django.contrib.auth.models.User or None
        :param default_tester: same as the argument ``default_tester`` of
            :meth:`TestCase.clone`.
        :type default_tester: django.contrib.auth.models.User or None
        :param source_plan: same as the argument ``source_plan`` of
            :meth:`TestCase.clone`.
        :type source_plan: TestPlan or None
        :return: the updated version of this case.
        :rtype: TestCase
        """
        dest_case = self
        dest_case.author = author or self.author
        dest_case.default_tester = default_tester or self.author
        dest_case.save()

        rel = TestCasePlan.objects.filter(plan=source_plan, case=self).first()

        for plan in to_plans:
            if source_plan is None:
                sort_key = plan.get_case_sortkey()
            else:
                sort_key = rel.sortkey if rel else plan.get_case_sortkey()
            plan.add_case(dest_case, sortkey=sort_key)

        return dest_case

    def get_notification_recipients(self) -> List[str]:
        recipients = set()
        emailing = self.emailing
        if emailing.auto_to_case_author:
            recipients.add(self.author.email)
        if emailing.auto_to_case_tester and self.default_tester:
            recipients.add(self.default_tester.email)
        if emailing.auto_to_run_manager:
            managers = self.case_run.values_list("run__manager__email", flat=True)
            recipients.update(managers)
        if emailing.auto_to_run_tester:
            run_testers = self.case_run.values_list("run__default_tester__email", flat=True)
            recipients.update(run_testers)
        if emailing.auto_to_case_run_assignee:
            assignees = self.case_run.values_list("assignee__email", flat=True)
            recipients.update(assignees)
        return [item for item in recipients if item]

    @classmethod
    def subtotal_by_status(
        cls, plans: Optional[Union[List[int], QuerySet]] = None
    ) -> Dict[str, Any]:
        cases = TestCase.objects
        if plans is not None:
            cases = cases.filter(plan__in=plans)
        stats = cases.values("case_status").annotate(count=Count("pk"))

        statuss = {item.pk: item.name for item in TestCaseStatus.objects.order_by("pk")}
        raw: Dict[str, int] = {name: 0 for name in statuss.values()}

        item: Dict[str, int]
        for item in stats:
            raw[statuss[item["case_status"]]] = item["count"]

        total = sum(raw.values())
        return {
            "raw": raw,
            "confirmed_cases": raw["CONFIRMED"],
            "reviewing_cases": total - raw["CONFIRMED"],
            "total": total,
        }


class TestCaseText(TCMSActionModel):
    case = models.ForeignKey(TestCase, related_name="text", on_delete=models.CASCADE)
    case_text_version = models.IntegerField()
    author = models.ForeignKey("auth.User", db_column="who", on_delete=models.CASCADE)
    create_date = models.DateTimeField(db_column="creation_ts", auto_now_add=True)
    action = models.TextField(blank=True)
    effect = models.TextField(blank=True)
    setup = models.TextField(blank=True)
    breakdown = models.TextField(blank=True)
    action_checksum = models.CharField(max_length=32)
    effect_checksum = models.CharField(max_length=32)
    setup_checksum = models.CharField(max_length=32)
    breakdown_checksum = models.CharField(max_length=32)

    class Meta:
        db_table = "test_case_texts"
        ordering = ["case", "-case_text_version"]
        unique_together = ("case", "case_text_version")

    def get_plain_text(self):
        action = html2text(smart_str(self.action)).rstrip()
        effect = html2text(smart_str(self.effect)).rstrip()
        setup = html2text(smart_str(self.setup)).rstrip()
        breakdown = html2text(smart_str(self.breakdown)).rstrip()
        return PlainText(action=action, setup=setup, effect=effect, breakdown=breakdown)


class TestCasePlan(models.Model):
    plan = models.ForeignKey("testplans.TestPlan", on_delete=models.CASCADE)
    case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    sortkey = models.IntegerField(null=True, blank=True)

    # TODO: create FOREIGN KEY constraint on plan_id and case_id individually
    # in database.

    class Meta:
        db_table = "test_case_plans"
        unique_together = ("plan", "case")


class TestCaseAttachment(models.Model):
    attachment = models.ForeignKey("management.TestAttachment", on_delete=models.CASCADE)

    case = models.ForeignKey(
        TestCase, default=None, related_name="case_attachment", on_delete=models.CASCADE
    )

    case_run = models.ForeignKey(
        "testruns.TestCaseRun",
        default=None,
        null=True,
        blank=True,
        related_name="case_run_attachment",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "test_case_attachments"
        # FIXME: what unique constraints are needed against this model?


class TestCaseComponent(models.Model):
    case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    component = models.ForeignKey("management.Component", on_delete=models.CASCADE)

    class Meta:
        db_table = "test_case_components"
        unique_together = ("case", "component")


class TestCaseTag(models.Model):
    tag = models.ForeignKey("management.TestTag", on_delete=models.CASCADE)
    case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    user = models.IntegerField(db_column="userid", default="0")

    class Meta:
        db_table = "test_case_tags"


class Contact(TCMSContentTypeBaseModel):
    """A Contact that can be added into Email settings' CC list"""

    name = models.CharField(max_length=50)
    email = models.EmailField(db_index=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "tcms_contacts"
        index_together = (("content_type", "object_pk", "site"),)

    @classmethod
    def create(cls, email, content_object, name=None):
        """Factory method to create a new Contact"""

        if not name:
            store_name = email.split("@")[0]
        else:
            store_name = name

        c = cls(
            name=store_name,
            email=email,
            content_object=content_object,
            site_id=settings.SITE_ID,
        )
        c.save()
        return c


class TestCaseEmailSettings(models.Model):
    case = models.OneToOneField(TestCase, related_name="email_settings", on_delete=models.CASCADE)

    notify_on_case_update = models.BooleanField(default=False)
    notify_on_case_delete = models.BooleanField(default=False)
    auto_to_case_author = models.BooleanField(default=False)
    auto_to_case_tester = models.BooleanField(default=False)
    auto_to_run_manager = models.BooleanField(default=False)
    auto_to_run_tester = models.BooleanField(default=False)
    auto_to_case_run_assignee = models.BooleanField(default=False)

    cc_list = GenericRelation(Contact, object_id_field="object_pk")

    class Meta:
        pass

    def add_cc(self, email_addrs):
        """Add email addresses to CC list

        Arguments:
        - email_addrs: str or list, holding one or more email addresses
        """

        emailaddr_list = []
        if not isinstance(email_addrs, list):
            emailaddr_list.append(email_addrs)
        else:
            emailaddr_list = list(email_addrs)

        for email_addr in emailaddr_list:
            Contact.create(email=email_addr, content_object=self)

    def get_cc_list(self) -> List[str]:
        """Return the whole CC list"""

        return sorted(c.email for c in self.cc_list.all())

    def remove_cc(self, email_addrs):
        """Remove one or more email addresses from EmailSettings' CC list

        If any email_addr is unknown, remove_cc will keep quiet.

        Arguments:
        - email_addrs: str or list, holding one or more email addresses
        """

        emailaddr_list = []
        if not isinstance(email_addrs, list):
            emailaddr_list.append(email_addrs)
        else:
            emailaddr_list = list(email_addrs)

        self.cc_list.filter(email__in=emailaddr_list).using(None).delete()

    def filter_new_emails(self, origin_emails, new_emails):
        """Find out the new email addresses to be added"""

        return list(set(new_emails) - set(origin_emails))

    def filter_unnecessary_emails(self, origin_emails, new_emails):
        """Find out the unnecessary addresses to be delete"""

        return list(set(origin_emails) - set(new_emails))

    def update_cc_list(self, email_addrs):
        """Add the new emails and delete unnecessary ones

        Arguments:
        - email_addrs: list, a instance of list holding emails user
        input via UI
        """

        origin_emails = self.get_cc_list()

        emails_to_delete = self.filter_unnecessary_emails(origin_emails, email_addrs)
        self.remove_cc(emails_to_delete)
        self.add_cc(self.filter_new_emails(origin_emails, email_addrs))


def _listen():
    """signals listen"""

    # case save/delete listen for email notify
    post_save.connect(case_watchers.on_case_save, TestCase)
    post_delete.connect(case_watchers.on_case_delete, TestCase)
    post_delete.connect(case_watchers.remove_case_email_settings, TestCase)
    pre_save.connect(case_watchers.pre_save_clean, TestCase)


if settings.LISTENING_MODEL_SIGNAL:
    _listen()

if register_model:
    register_model(TestCase)
    register_model(TestCaseText)
    register_model(TestCasePlan)
    register_model(TestCaseComponent)

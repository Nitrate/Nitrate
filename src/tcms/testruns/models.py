# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Count, Q, QuerySet
from django.db.models.signals import post_delete, post_save, pre_save
from django.urls import reverse
from django_comments.models import Comment

from tcms.core.models import TCMSActionModel
from tcms.core.models.fields import DurationField
from tcms.core.tcms_router import connection
from tcms.core.utils import EnumLike, format_timedelta
from tcms.issuetracker.models import Issue
from tcms.linkreference.models import LinkReference
from tcms.management.models import TCMSEnvValue, TestBuild, TestTag
from tcms.testcases.models import NoneText, TestCase, TestCaseText
from tcms.testruns import signals as run_watchers

try:
    from tcms.plugins_support.signals import register_model
except ImportError:
    register_model = None


class TestRun(TCMSActionModel):
    # Attribute names to get testrun statistics
    PERCENTAGES = (
        "failed_case_run_percent",
        "passed_case_run_percent",
        "completed_case_run_percent",
    )

    run_id = models.AutoField(primary_key=True)
    plan_text_version = models.IntegerField()
    start_date = models.DateTimeField(auto_now_add=True, db_index=True)
    stop_date = models.DateTimeField(null=True, blank=True, db_index=True)
    summary = models.TextField()
    notes = models.TextField(blank=True)
    estimated_time = DurationField(default=timedelta(seconds=0))

    product_version = models.ForeignKey(
        "management.Version", related_name="version_run", on_delete=models.CASCADE
    )
    plan = models.ForeignKey("testplans.TestPlan", related_name="run", on_delete=models.CASCADE)
    environment_id = models.IntegerField(default=0)
    build = models.ForeignKey(
        "management.TestBuild", related_name="build_runs", on_delete=models.CASCADE
    )
    manager = models.ForeignKey("auth.User", related_name="manager", on_delete=models.CASCADE)
    default_tester = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        related_name="default_tester",
        on_delete=models.SET_NULL,
    )

    env_value = models.ManyToManyField(
        "management.TCMSEnvValue", through="testruns.TCMSEnvRunValueMap"
    )

    tag = models.ManyToManyField("management.TestTag", through="testruns.TestRunTag")

    cc = models.ManyToManyField("auth.User", through="testruns.TestRunCC")
    auto_update_run_status = models.BooleanField(default=False)

    class Meta:
        db_table = "test_runs"
        unique_together = ("run_id", "product_version", "plan_text_version")

    def __str__(self):
        return self.summary

    @classmethod
    def to_xmlrpc(cls, query=None):
        from tcms.xmlrpc.serializer import TestRunXMLRPCSerializer
        from tcms.xmlrpc.utils import distinct_filter

        _query = query or {}
        qs = distinct_filter(TestRun, _query).order_by("pk")
        s = TestRunXMLRPCSerializer(model_class=cls, queryset=qs)
        return s.serialize_queryset()

    @classmethod
    def list(cls, query: Dict) -> QuerySet:
        conditions = []

        mapping = {
            "search": lambda value: Q(run_id__icontains=value) | Q(summary__icontains=value),
            "summary": lambda value: Q(summary__icontains=value),
            "product": lambda value: Q(build__product=value),
            "product_version": lambda value: Q(product_version=value),
            "plan": lambda value: Q(plan__plan_id=int(value))
            if value.isdigit()
            else Q(plan__name__icontains=value),
            "build": lambda value: Q(build=value),
            "env_group": lambda value: Q(plan__env_group=value),
            "people_id": lambda value: Q(manager__id=value) | Q(default_tester__id=value),
            "manager": lambda value: Q(manager=value),
            "default_tester": lambda value: Q(default_tester=value),
            "tag__name__in": lambda value: Q(tag__name__in=value),
            "case_run__assignee": lambda value: Q(case_run__assignee=value),
            "status": lambda value: {
                "running": Q(stop_date__isnull=True),
                "finished": Q(stop_date__isnull=False),
            }[value.lower()],
            "people": lambda value: {
                "default_tester": Q(default_tester=value),
                "manager": Q(manager=value),
                "people": Q(manager=value) | Q(default_tester=value),
                # TODO: Remove first one after upgrade to newer version.
                # query.set can return either '' or None sometimes, so
                # currently keeping these two lines here is a workaround.
                "": Q(manager=value) | Q(default_tester=value),
                None: Q(manager=value) | Q(default_tester=value),
            }[query.get("people_type")],
        }

        conditions = [
            mapping[key](value) for key, value in query.items() if value and key in mapping
        ]

        runs = cls.objects.filter(*conditions)

        value = query.get("sortby")
        if value:
            runs = runs.order_by(value)

        return runs.distinct()

    def belong_to(self, user):
        if self.manager == user or self.plan.author == user:
            return True

        return False

    def clear_estimated_time(self):
        """Converts a integer to time"""
        return format_timedelta(self.estimated_time)

    def check_all_case_runs(self, case_run_id=None):
        tcrs = self.case_run.all()
        tcrs = tcrs.select_related("case_run_status")

        for tcr in tcrs:
            if not tcr.finished():
                return False

        return True

    def get_absolute_url(self):
        return reverse("run-get", args=[self.pk])

    def get_notification_recipients(self) -> List[str]:
        """
        Get the all related mails from the run
        """
        to = [self.manager.email]
        to.extend(self.cc.values_list("email", flat=True))
        if self.default_tester_id:
            to.append(self.default_tester.email)

        for tcr in self.case_run.select_related("assignee").all():
            if tcr.assignee_id:
                to.append(tcr.assignee.email)
        return list(set(to))

    # FIXME: rewrite to use multiple values INSERT statement
    def add_case_run(
        self,
        case: TestCase,
        case_run_status: int = 1,
        assignee: Optional[User] = None,
        case_text_version: Optional[int] = None,
        build: Optional[TestBuild] = None,
        notes: Optional[str] = None,
        sortkey: int = 0,
    ):
        _case_text_version = case_text_version
        if not _case_text_version:
            _case_text_version = case.latest_text(text_required=False).case_text_version

        _assignee = (
            assignee
            or (case.default_tester_id and case.default_tester)
            or (self.default_tester_id and self.default_tester)
        )

        if isinstance(case_run_status, int):
            _case_run_status = TestCaseRunStatus.objects.get(id=case_run_status)
        else:
            _case_run_status = case_run_status

        return self.case_run.create(
            case=case,
            assignee=_assignee,
            tested_by=None,
            case_run_status=_case_run_status,
            case_text_version=_case_text_version,
            build=build or self.build,
            notes=notes,
            sortkey=sortkey,
            environment_id=self.environment_id,
            running_date=None,
            close_date=None,
        )

    def add_tag(self, tag: TestTag):
        return TestRunTag.objects.get_or_create(run=self, tag=tag)

    def add_cc(self, user):
        return TestRunCC.objects.get_or_create(
            run=self,
            user=user,
        )

    def add_env_value(self, env_value: TCMSEnvValue):
        return TCMSEnvRunValueMap.objects.get_or_create(run=self, value=env_value)

    def remove_tag(self, tag):
        cursor = connection.writer_cursor
        cursor.execute(
            "DELETE from test_run_tags WHERE run_id = %s AND tag_id = %s",
            (self.pk, tag.pk),
        )

    def remove_cc(self, user):
        cursor = connection.writer_cursor
        cursor.execute(
            "DELETE from test_run_cc WHERE run_id = %s AND who = %s",
            (self.run_id, user.id),
        )

    def remove_env_value(self, env_value: TCMSEnvValue):
        run_env_value = TCMSEnvRunValueMap.objects.get(run=self, value=env_value)
        run_env_value.delete()

    def get_issues_count(self):
        """
        Return the count of distinct bug numbers recorded for
        this particular TestRun.
        """
        # note fom Django docs: A count() call performs a SELECT COUNT(*)
        # behind the scenes !!!
        return Issue.objects.filter(case_run__run=self).values("issue_key").distinct().count()

    def get_percentage(self, count):
        case_run_count = self.total_num_caseruns
        if case_run_count == 0:
            return 0
        percent = float(count) / case_run_count * 100
        percent = round(percent, 2)
        return percent

    def _get_passed_case_run_num(self):
        passed_status_id = TestCaseRunStatus.name_to_id("PASSED")
        passed_caserun = self.case_run.filter(case_run_status=passed_status_id)
        return passed_caserun.count()

    passed_case_run_num = property(_get_passed_case_run_num)

    def _get_passed_case_run_percentage(self):
        percentage = self.get_percentage(self.passed_case_run_num)
        return percentage

    passed_case_run_percent = property(_get_passed_case_run_percentage)

    # FIXME: unused
    def get_status_case_run_num(self, status_name):
        status_id = TestCaseRunStatus.name_to_id(status_name)
        caserun = self.case_run.filter(case_run_status=status_id)
        return caserun.count()

    def _get_total_case_run_num(self):
        return self.case_run.count()

    total_num_caseruns = property(_get_total_case_run_num)

    def update_completion_status(self, is_auto_updated, is_finish=None):
        if is_auto_updated and self.auto_update_run_status:
            if self.completed_case_run_percent == 100.0:
                self.stop_date = datetime.now()
            else:
                self.stop_date = None
            self.save()
        if not is_auto_updated and not self.auto_update_run_status:
            if is_finish:
                self.stop_date = datetime.now()
            else:
                self.stop_date = None
            self.save()

    def subtotal_issues_by_case_run(self):
        """Return issues subtotal of this run

        :return: a mapping from case run pk to issues count that the case run
            has.
        :rtype: dict
        """
        q = (
            Issue.objects.filter(case_run__run=self)
            .values("case_run")
            .annotate(issues_count=Count("pk"))
        )
        return {item["case_run"]: item["issues_count"] for item in q}

    def get_issue_trackers(self) -> QuerySet:
        """Get enabled issue trackers in order to add issues to case runs of this run"""
        return self.plan.product.issue_trackers.filter(enabled=True).only(
            "pk", "name", "validate_regex"
        )


# FIXME: replace TestCaseRunStatus' internal cache with Django's cache
# machanism


class TestCaseRunStatus(EnumLike, TCMSActionModel):
    complete_status_names = ("PASSED", "ERROR", "FAILED", "WAIVED")
    failure_status_names = ("ERROR", "FAILED")
    idle_status_names = ("IDLE",)

    _complete_statuses = None
    _failed_status = None

    id = models.AutoField(db_column="case_run_status_id", primary_key=True)
    name = models.CharField(max_length=60, blank=True, unique=True)
    sortkey = models.IntegerField(null=True, blank=True, default=0)
    description = models.TextField(null=True, blank=True)
    auto_blinddown = models.BooleanField(default=True)

    class Meta:
        db_table = "test_case_run_status"

    def __str__(self):
        return self.name

    def finished(self):
        return self.name in self.complete_status_names

    @classmethod
    def completed_status_ids(cls):
        """
        There are some status indicate that
        the testcaserun is completed.
        Return IDs of these statuses.
        """
        return cls.objects.filter(name__in=cls.complete_status_names).values_list("pk", flat=True)


class TestCaseRunManager(models.Manager):
    def get_automated_case_count(self):
        return self.filter(case__is_automated=1).count()

    def get_manual_case_count(self):
        return self.filter(case__is_automated=0).count()

    def get_both(self):
        count1 = self.get_automated_case_count()
        count2 = self.get_manual_case_count()
        return self.count() - count1 - count2


class TestCaseRun(TCMSActionModel):
    objects = TestCaseRunManager()
    case_run_id = models.AutoField(primary_key=True)
    case_text_version = models.IntegerField()
    running_date = models.DateTimeField(null=True, blank=True)
    close_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    sortkey = models.IntegerField(null=True, blank=True)
    environment_id = models.IntegerField(default=0)

    assignee = models.ForeignKey(
        "auth.User",
        blank=True,
        null=True,
        related_name="case_run_assignee",
        on_delete=models.SET_NULL,
    )
    tested_by = models.ForeignKey(
        "auth.User",
        blank=True,
        null=True,
        related_name="case_run_tester",
        on_delete=models.SET_NULL,
    )
    run = models.ForeignKey(TestRun, related_name="case_run", on_delete=models.CASCADE)
    case = models.ForeignKey(
        "testcases.TestCase", related_name="case_run", on_delete=models.CASCADE
    )
    case_run_status = models.ForeignKey(
        TestCaseRunStatus, related_name="case_runs", on_delete=models.CASCADE
    )
    build = models.ForeignKey("management.TestBuild", on_delete=models.CASCADE)

    links = GenericRelation(LinkReference, object_id_field="object_pk")
    comments = GenericRelation(Comment, object_id_field="object_pk")

    class Meta:
        db_table = "test_case_runs"
        unique_together = ("case", "run", "case_text_version")

    def __str__(self):
        return f"{self.pk}: {self.case_id}"

    @classmethod
    def to_xmlrpc(cls, query={}):
        from tcms.xmlrpc.serializer import TestCaseRunXMLRPCSerializer
        from tcms.xmlrpc.utils import distinct_filter

        qs = distinct_filter(TestCaseRun, query).order_by("pk")
        s = TestCaseRunXMLRPCSerializer(model_class=cls, queryset=qs)
        return s.serialize_queryset()

    @staticmethod
    def mail_scene(
        objects: QuerySet,
        field: Optional[str] = None,
        value=None,
        ctype=None,
        object_pk=None,
    ):
        tr: TestRun = objects[0].run
        # scence_templates format:
        # template, subject, context
        tcrs = (
            objects.select_related("case", "assignee")
            .only("case__summary", "assignee__username")
            .order_by("pk")
        )
        tcr: TestCaseRun
        # FIXME: calculate the templates data lazily
        scence_templates = {
            "assignee": {
                "template_name": "mail/change_case_run_assignee.txt",
                "subject": f"Assignee of run {tr.pk} has been changed",
                "recipients": tr.get_notification_recipients(),
                "context": {
                    "run_id": tr.pk,
                    "summary": tr.summary,
                    "full_url": tr.get_full_url(),
                    "test_case_runs": [
                        {
                            "pk": tcr.pk,
                            "case_summary": tcr.case.summary,
                            "assignee": tcr.assignee.username,
                        }
                        for tcr in tcrs
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
        link_external_tracker=False,
    ):
        """Add an issue to this case run

        Every argument has same meaning of argument of :meth:`TestCase.add_issue`.

        :param str issue_key: issue key to add.
        :param issue_tracker: issue tracker the issue key should belong to.
        :type issue_tracker: :class:`IssueTracker`
        :param str summary: issue's summary.
        :param str description: issue's description.
        :param bool link_external_tracker: whether to add case to issue's
            external tracker in remote issue tracker.
        :return: the newly added issue.
        :rtype: :class:`Issue`
        """
        return self.case.add_issue(
            issue_key=issue_key,
            issue_tracker=issue_tracker,
            summary=summary,
            description=description,
            case_run=self,
            link_external_tracker=link_external_tracker,
        )

    def remove_issue(self, issue_key):
        """Remove issue from this case run

        :param str issue_key: issue key to remove.
        """
        self.case.remove_issue(issue_key, case_run=self)

    def is_finished(self):
        return self.case_run_status.is_finished()

    def get_issues(self) -> QuerySet:
        """Get issues added to this case run

        :return: a queryset of the issues.
        """
        return Issue.objects.filter(case_run=self)

    def get_issues_count(self):
        """Return the number of issues added to this case run

        :return: the number of issues.
        :rtype: int
        """
        return self.get_issues().values("pk").count()

    def get_text_versions(self):
        return TestCaseText.objects.filter(case__pk=self.case.pk).values_list(
            "case_text_version", flat=True
        )

    def get_text_with_version(self, case_text_version=None):
        if case_text_version:
            try:
                return TestCaseText.objects.get(
                    case__case_id=self.case_id, case_text_version=case_text_version
                )
            except TestCaseText.DoesNotExist:
                return NoneText
        try:
            return TestCaseText.objects.get(
                case__case_id=self.case_id, case_text_version=self.case_text_version
            )
        except TestCaseText.DoesNotExist:
            return NoneText

    def get_previous_or_next(self):
        ids = list(self.run.case_run.values_list("case_run_id", flat=True))
        current_idx = ids.index(self.case_run_id)
        prev = TestCaseRun.objects.get(case_run_id=ids[current_idx - 1])
        try:
            next = TestCaseRun.objects.get(case_run_id=ids[current_idx + 1])
        except IndexError:
            next = TestCaseRun.objects.get(case_run_id=ids[0])

        return (prev, next)

    def latest_text(self):
        try:
            return TestCaseText.objects.filter(case__case_id=self.case_id).order_by(
                "-case_text_version"
            )[0]
        except IndexError:
            return NoneText


class TestRunTag(models.Model):
    tag = models.ForeignKey("management.TestTag", on_delete=models.CASCADE)
    run = models.ForeignKey(TestRun, related_name="tags", on_delete=models.CASCADE)
    user = models.IntegerField(db_column="userid", default="0")

    class Meta:
        db_table = "test_run_tags"


class TestRunCC(models.Model):
    run = models.ForeignKey(TestRun, related_name="cc_list", on_delete=models.CASCADE)
    user = models.ForeignKey("auth.User", db_column="who", on_delete=models.CASCADE)

    class Meta:
        db_table = "test_run_cc"
        unique_together = ("run", "user")


class TCMSEnvRunValueMap(models.Model):
    run = models.ForeignKey(TestRun, on_delete=models.CASCADE)
    value = models.ForeignKey("management.TCMSEnvValue", on_delete=models.CASCADE)

    class Meta:
        db_table = "tcms_env_run_value_map"


# Signals handler
def _run_listen():
    post_save.connect(run_watchers.mail_notify_on_test_run_creation_or_update, sender=TestRun)
    post_save.connect(
        run_watchers.post_case_run_saved,
        sender=TestCaseRun,
        dispatch_uid="tcms.testruns.models.TestCaseRun",
    )
    post_delete.connect(
        run_watchers.post_case_run_deleted,
        sender=TestCaseRun,
        dispatch_uid="tcms.testruns.models.TestCaseRun",
    )
    pre_save.connect(run_watchers.pre_save_clean, sender=TestRun)


if settings.LISTENING_MODEL_SIGNAL:
    _run_listen()

if register_model:
    register_model(TestRun)
    register_model(TestCaseRun)
    register_model(TestRunTag)

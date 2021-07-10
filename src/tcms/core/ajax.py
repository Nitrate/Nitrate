# -*- coding: utf-8 -*-
"""
Shared functions for plan/case/run.

Most of these functions are use for Ajax.
"""
import datetime
import json
import logging
import operator
import sys

from functools import reduce
from typing import Any, Dict, NewType, List, Tuple, Union
from collections.abc import Iterable

from django import forms
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import models
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
from django.dispatch import Signal
from django.http import HttpResponse, JsonResponse, QueryDict
from django.http.request import HttpRequest
from django.shortcuts import render
from django.views import View
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

import tcms.comments.models

from tcms.core.mailto import mailto
from tcms.core.models import TCMSActionModel
from tcms.core.responses import (
    JsonResponseForbidden,
    JsonResponseBadRequest,
    JsonResponseNotFound,
)
from tcms.management.models import Priority
from tcms.management.models import TestTag
from tcms.testcases.models import TestCase
from tcms.testcases.models import TestCaseStatus
from tcms.testcases.views import get_selected_testcases
from tcms.testplans.models import TestPlan, TestCasePlan
from tcms.testruns import signals as run_watchers
from tcms.testruns.models import TestRun, TestCaseRun, TestCaseRunStatus
from tcms.core.utils import get_string_combinations, form_error_messages_to_list

post_update = Signal(providing_args=["instances", "kwargs"])
post_update.connect(run_watchers.post_update_handler)

logger = logging.getLogger(__name__)

SORT_KEY_MIN = 0
SORT_KEY_MAX = 32300
SORT_KEY_RANGE = [SORT_KEY_MIN, SORT_KEY_MAX]


def strip_parameters(
    request_data: Union[QueryDict, Dict[str, Any]],
    skip_parameters: Iterable,
) -> Dict[str, Any]:
    """
    Helper method which will remove the dict items listed in skip_parameters
    @return - dict
    """
    parameters = {}
    for k, v in request_data.items():
        if k not in skip_parameters and v:
            parameters[str(k)] = v

    return parameters


@require_GET
def info(request):
    """Return misc information"""

    class Objects:
        __all__ = [
            "builds",
            "categories",
            "components",
            "envs",
            "env_groups",
            "env_properties",
            "env_values",
            "tags",
            "users",
            "versions",
        ]

        def __init__(self, request, product_ids=None):
            self.request = request
            self.product_ids = product_ids
            self.internal_parameters = ("info_type", "field", "format")

        def builds(self):
            from tcms.management.models import TestBuild

            query = {
                "product_ids": self.product_ids,
                "is_active": self.request.GET.get("is_active"),
            }
            return TestBuild.list(query)

        def categories(self):
            from tcms.testcases.models import TestCaseCategory

            return TestCaseCategory.objects.filter(product__in=self.product_ids)

        def components(self):
            from tcms.management.models import Component

            return Component.objects.filter(product__in=self.product_ids)

        def envs(self):
            from tcms.management.models import TestEnvironment

            return TestEnvironment.objects.filter(product__in=self.product_ids)

        def env_groups(self):
            from tcms.management.models import TCMSEnvGroup

            return TCMSEnvGroup.objects.all()

        def env_properties(self):
            from tcms.management.models import TCMSEnvGroup, TCMSEnvProperty

            if self.request.GET.get("env_group_id"):
                env_group = TCMSEnvGroup.objects.get(id=self.request.GET["env_group_id"])
                return env_group.property.all()
            else:
                return TCMSEnvProperty.objects.all()

        def env_values(self):
            from tcms.management.models import TCMSEnvValue

            return TCMSEnvValue.objects.filter(property__id=self.request.GET.get("env_property_id"))

        def tags(self):
            query = strip_parameters(request.GET, self.internal_parameters)
            tags = TestTag.objects
            # Generate the string combination, because we are using
            # case sensitive table
            if query.get("name__startswith"):
                seq = get_string_combinations(query["name__startswith"])
                criteria = reduce(operator.or_, (models.Q(name__startswith=item) for item in seq))
                tags = tags.filter(criteria)
                del query["name__startswith"]

            tags = tags.filter(**query).distinct()
            return tags

        def users(self):
            from django.contrib.auth.models import User

            query = strip_parameters(self.request.GET, self.internal_parameters)
            return User.objects.filter(**query)

        def versions(self):
            from tcms.management.models import Version

            return Version.objects.filter(product__in=self.product_ids)

    product_ids = []
    for s in request.GET.getlist("product_id"):
        if s.isdigit():
            product_ids.append(int(s))
        else:
            return JsonResponseBadRequest(
                {"message": f"Invalid product id {s}. It must be a positive integer."}
            )

    info_type = request.GET.get("info_type")
    if info_type is None:
        return JsonResponseBadRequest({"message": "Missing parameter info_type."})

    objects = Objects(request=request, product_ids=product_ids)
    obj = getattr(objects, info_type, None)

    if obj:
        if request.GET.get("format") == "ulli":
            field = request.GET.get("field", "name")
            response_str = "<ul>"
            for o in obj():
                response_str += "<li>" + getattr(o, field, None) + "</li>"
            response_str += "</ul>"
            return HttpResponse(response_str)

        return JsonResponse(
            json.loads(
                serializers.serialize(
                    request.GET.get("format", "json"), obj(), fields=("name", "value")
                )
            ),
            safe=False,
        )

    return JsonResponseBadRequest({"message": "Unrecognizable infotype"})


@require_GET
def form(request):
    """Response get form ajax call, most using in dialog"""

    # The parameters in internal_parameters will delete from parameters
    internal_parameters = ["app_form", "format"]
    parameters = strip_parameters(request.GET, internal_parameters)
    q_app_form = request.GET.get("app_form")
    q_format = request.GET.get("format")
    if not q_format:
        q_format = "p"

    if not q_app_form:
        return HttpResponse("Unrecognizable app_form")

    # Get the form
    q_app, q_form = q_app_form.split(".")[0], q_app_form.split(".")[1]
    exec(f"from tcms.{q_app}.forms import {q_form} as form")
    try:
        __import__("tcms.%s.forms" % q_app)
    except ImportError:
        raise
    q_app_module = sys.modules["tcms.%s.forms" % q_app]
    form_class = getattr(q_app_module, q_form)
    form = form_class(initial=parameters)

    # Generate the HTML and reponse
    html = getattr(form, "as_" + q_format)
    return HttpResponse(html())


def tag(request, template_name="management/get_tag.html"):
    """Get tags for test plan or test case"""

    class Objects:
        __all__ = ["plan", "case", "run"]

        def __init__(self, request, template_name):
            self.request = request
            self.template_name = template_name
            for o in self.__all__:
                if request.GET.get(o):
                    self.object = o
                    self.object_pks = request.GET.getlist(o)
                    break

        def get(self):
            func = getattr(self, self.object)
            return func()

        def plan(self):
            return self.template_name, TestPlan.objects.filter(pk__in=self.object_pks)

        def case(self):
            return self.template_name, get_selected_testcases(self.request)

        def run(self):
            self.template_name = "run/tag_list.html"
            return self.template_name, TestRun.objects.filter(pk__in=self.object_pks)

    class TagActions:
        __all__ = ["add", "remove"]

        def __init__(self, obj, tag):
            self.obj = obj
            self.tag = TestTag.string_to_list(tag)
            self.request = request

        def add(self):
            for tag_str in self.tag:
                try:
                    tag, c = TestTag.objects.get_or_create(name=tag_str)
                    for o in self.obj:
                        o.add_tag(tag)
                except Exception:
                    return "Error when adding %s" % self.tag

            return True, self.obj

        def remove(self):
            self.obj = self.obj.filter(tag__name__in=self.tag).distinct()

            if not self.obj:
                return "Tags does not exist in current selected plan."

            else:
                for tag_str in self.tag:
                    try:
                        tag = TestTag.objects.filter(name=tag_str)[0]
                    except IndexError:
                        return f"Tag {tag_str} does not exist in current selected plan."

                    for o in self.obj:
                        try:
                            o.remove_tag(tag)
                        except Exception:
                            return "Remove tag %s error." % tag
                return True, self.obj

    objects = Objects(request, template_name)
    template_name, obj = objects.get()

    q_tag = request.GET.get("tags")
    q_action = request.GET.get("a")
    if q_action:
        tag_actions = TagActions(obj=obj, tag=q_tag)
        func = getattr(tag_actions, q_action)
        response = func()
        if not response[0]:
            return JsonResponse({})

    del q_tag, q_action

    # Response to batch operations
    if request.GET.get("t") == "json":
        if request.GET.get("f") == "serialized":
            return JsonResponse(
                # FIXME: this line of code depends on the existence of `a`
                # argument in query string. So, if a does not appear in the
                # query string, error will happen here
                json.loads(serializers.serialize(request.GET["t"], response[1])),
                safe=False,
            )

        return JsonResponse({})

    # Response the single operation
    if len(obj) == 1:
        tags = obj[0].tag.all()
        tags = tags.extra(
            select={
                "num_plans": "SELECT COUNT(*) FROM test_plan_tags "
                "WHERE test_tags.tag_id = test_plan_tags.tag_id",
                "num_cases": "SELECT COUNT(*) FROM test_case_tags "
                "WHERE test_tags.tag_id = test_case_tags.tag_id",
                "num_runs": "SELECT COUNT(*) FROM test_run_tags "
                "WHERE test_tags.tag_id = test_run_tags.tag_id",
            }
        )

        context_data = {
            "tags": tags,
            "object": obj[0],
        }
        return render(request, template_name, context=context_data)

    # Why return an empty response originally?
    return JsonResponse({})


LogActionParams = NewType("LogActionParams", Dict[str, Any])

# Construct data used to prepare log_action calls for a test case run.
LogActionInfo = NewType("LogActionInfo", Tuple[TCMSActionModel, List[LogActionParams]])


class ModelPatchBaseView(PermissionRequiredMixin, View):
    """Abstract class defining interfaces to update a model properties"""

    simple_patches: Dict[str, Tuple[forms.Form, bool]] = {
        # Validation form, whether to send mail
        # "field_name": (FormClass, True or False)
    }
    targets_field_name: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Will be set in the view method
        self.target_field = None
        self.new_value = None
        self._update_targets = None
        self._request_data = None

    def handle_no_permission(self) -> JsonResponseForbidden:
        return JsonResponseForbidden({"message": "You do not have permission to update."})

    def _sendmail(self, objects):
        """
        Send notification mail. For those not requiring sending a mail, the
        default implementation of this method just keeps quiet and do nothing.
        """

    @staticmethod
    def _record_log_actions(log_actions_info: List[LogActionInfo]) -> None:
        model: TCMSActionModel
        for model, log_actions_params in log_actions_info:
            for params in log_actions_params:
                try:
                    model.log_action(**params)
                except Exception:
                    logger.warning(
                        "Failed to log update action for case run %s. Field: %s, original: %s, "
                        "new: %s, by: %s",
                        model.pk,
                        params["field"],
                        params["original_value"],
                        params["new_value"],
                        params["who"],
                    )

    def _simple_update(
        self, models: Union[QuerySet, List[TCMSActionModel]], new_value: Any
    ) -> None:
        """A simple update method for most cases to update property of a set of cases

        In the most of the cases, the property update requires two steps, one is to update the
        property, and another one is the log an action for that property update. This pattern
        can be abstracted by the pass-in target_field and new_value. If there is some special
        cases that update a property in a more complicated way, you have to implement the
        _update_[property name] method separately.
        """
        log_actions_info = []
        changed = []

        for model in models:
            original_value = str(getattr(model, self.target_field))

            # "str(obj) == str(obj)" should cover most of the case of updating
            # a model's property. For a particular case of the property is a
            # foreign key pointing to management model like Priority, all
            # that kind of models have __str__ define which is able to return
            # a value properly for a call str().
            # For any uncovered case, a new way to detect this equality should
            # be considered instead.
            if original_value == str(new_value):
                continue

            log_actions_info.append(
                (
                    model,
                    [
                        {
                            "who": self.request.user,
                            "field": self.target_field,
                            "original_value": original_value,
                            "new_value": str(new_value),
                        }
                    ],
                )
            )

            setattr(model, self.target_field, new_value)
            changed.append(model)

        if changed:
            models[0].__class__.objects.bulk_update(changed, [self.target_field])
            self._record_log_actions(log_actions_info)

    def _simple_patch(self):
        form_class, send_mail = self.simple_patches[self.target_field]
        f = form_class(self._request_data)
        if not f.is_valid():
            return JsonResponseBadRequest({"message": form_error_messages_to_list(f)})
        patch_targets = f.cleaned_data[self.targets_field_name]
        self._simple_update(patch_targets, f.cleaned_data["new_value"])
        if send_mail:
            self._sendmail(patch_targets)

    def patch(self, request: HttpRequest):
        self._request_data = json.loads(request.body)
        self.target_field = self._request_data.get("target_field")
        if not self.target_field:
            return JsonResponseBadRequest({"message": "Missing argument target_field."})

        if self.target_field in self.simple_patches:
            action = self._simple_patch
        else:
            action = getattr(self, "_update_%s" % self.target_field, None)

        if not action:
            return JsonResponseBadRequest({"message": "Not know what to update."})

        try:
            resp = action()
        except ObjectDoesNotExist as err:
            return JsonResponseNotFound({"message": str(err)})
        except Exception:
            logger.exception(
                "Fail to update field %s with new value %s", self.target_field, self.new_value
            )
            # TODO: besides this message to users, what happening should be
            # recorded in the system log.
            return JsonResponseBadRequest(
                {
                    "message": "Update failed. Please try again or request "
                    "support from your organization."
                }
            )
        else:
            if resp is None:
                resp = JsonResponse({})
            return resp


class PatchTestCaseRunBaseForm(forms.Form):
    case_run = forms.ModelMultipleChoiceField(
        queryset=None,
        error_messages={
            "invalid_list": "Argument case_run only accepts a list of test case run pks.",
            "required": "Missing argument case_run to patch test case runs.",
            "invalid_pk_value": "%(pk)s is not a valid test case run pk.",
            "invalid_choice": "Test case run %(value)s does not exist.",
        },
    )


class PatchTestCaseRunAssigneeForm(PatchTestCaseRunBaseForm):
    new_value = forms.ModelChoiceField(
        queryset=User.objects.only("username"),
        error_messages={
            "required": "Missing argument new_value.",
            "invalid_choice": None,  # Set later inside __init__
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields["case_run"]
        f.queryset = TestCaseRun.objects.select_related("case", "assignee").only(
            "case", "assignee__username"
        )
        f: forms.ModelChoiceField = self.fields["new_value"]
        new_assignee_pk = self.data.get("new_value")
        f.error_messages["invalid_choice"] = f"No user with id {new_assignee_pk} exists."


class PatchTestCaseRunSortKeyForm(PatchTestCaseRunBaseForm):
    new_value = forms.IntegerField(
        min_value=SORT_KEY_MIN,
        max_value=SORT_KEY_MAX,
        error_messages={
            "required": "Missing argument new_value to patch test cases.",
            "invalid": "Sort key must be a positive integer.",
            "min_value": f"New sortkey is out of range {SORT_KEY_RANGE}.",
            "max_value": f"New sortkey is out of range {SORT_KEY_RANGE}.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["case_run"].queryset = TestCaseRun.objects.only("sortkey")


class PatchTestCaseRunStatusForm(PatchTestCaseRunBaseForm):
    new_value = forms.ModelChoiceField(
        queryset=TestCaseRunStatus.objects.only("name"),
        error_messages={
            "required": "Missing argument new_value.",
            "invalid_choice": None,  # Set later inside __init__
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields["case_run"]
        f.queryset = TestCaseRun.objects.select_related("case_run_status", "tested_by").only(
            "close_date", "tested_by__username", "case_run_status__name"
        )
        f: forms.ModelChoiceField = self.fields["new_value"]
        new_status = self.data.get("new_value")
        f.error_messages[
            "invalid_choice"
        ] = f'The test case run status "{new_status}" does not exist.'


class PatchTestCaseRunsView(ModelPatchBaseView):
    """Actions to update test case runs properties"""

    permission_required = "testruns.change_testcaserun"

    simple_patches = {
        "assignee": (PatchTestCaseRunAssigneeForm, True),
        "sortkey": (PatchTestCaseRunSortKeyForm, False),
    }
    targets_field_name: str = "case_run"

    def _sendmail(self, objects) -> None:
        mail_context = TestCaseRun.mail_scene(objects=objects, field=self.target_field)
        if mail_context:
            mail_context["context"]["user"] = self.request.user.username
            mailto(**mail_context)

    def _update_case_run_status(self):
        f = PatchTestCaseRunStatusForm(self._request_data)
        if not f.is_valid():
            return JsonResponseBadRequest({"message": form_error_messages_to_list(f)})

        request_user: User = self.request.user
        new_status = f.cleaned_data["new_value"]
        update_time = datetime.datetime.now()

        log_actions_info = []
        changed: List[TestCaseRun] = []
        tested_by_changed = False

        case_run: TestCaseRun
        for case_run in f.cleaned_data["case_run"]:
            if case_run.case_run_status == new_status:
                continue

            info = (
                case_run,
                [
                    {
                        "who": request_user,
                        "field": self.target_field,
                        "original_value": case_run.case_run_status.name,
                        "new_value": str(new_status),
                    },
                    # Refactor the original code to here, but have no idea why
                    # need to set this close_date by changing a test case run's status.
                    {
                        "who": request_user,
                        "field": "close_date",
                        "original_value": case_run.close_date,
                        "new_value": update_time,
                    },
                ],
            )
            if case_run.tested_by != request_user:
                tested_by_changed = True
                info[1].append(
                    {
                        "who": request_user,
                        "field": "tested_by",
                        "original_value": str(case_run.tested_by),
                        "new_value": request_user.username,
                    }
                )
                case_run.tested_by = request_user
            log_actions_info.append(info)

            case_run.case_run_status = new_status
            # FIXME: should close_date be set only when the complete status is set?
            case_run.close_date = update_time
            changed.append(case_run)

        if changed:
            changed_fields = [self.target_field, "close_date"]
            if tested_by_changed:
                changed_fields.append("tested_by")
            TestCaseRun.objects.bulk_update(changed, changed_fields)
            self._record_log_actions(log_actions_info)


class PatchTestCaseBaseForm(forms.Form):
    case = forms.ModelMultipleChoiceField(
        queryset=None,
        error_messages={
            "invalid_list": "Argument case only accepts a list of test case pks.",
            "required": "Missing argument case to patch test cases.",
            "invalid_pk_value": "%(pk)s is not a valid case pk.",
            "invalid_choice": "Test case %(value)s does not exist.",
        },
    )


class PatchTestCasePriorityForm(PatchTestCaseBaseForm):
    new_value = forms.ModelChoiceField(
        queryset=Priority.objects.all(),
        error_messages={
            "required": "Missing argument new_value.",
            "invalid_choice": "The priority you specified to change does not exist.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields["case"]
        f.queryset = TestCase.objects.select_related("priority").only("priority__value")


class PatchTestCaseDefaultTesterForm(PatchTestCaseBaseForm):
    new_value = forms.ModelChoiceField(
        queryset=User.objects.only("username"),
        to_field_name="username",
        error_messages={
            "required": "Missing argument new_value.",
            "invalid_choice": None,  # Set later inside __init__
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields["case"]
        f.queryset = TestCase.objects.select_related("default_tester").only(
            "default_tester__username"
        )
        f: forms.ModelChoiceField = self.fields["new_value"]
        f.error_messages["invalid_choice"] = (
            f"{self.data['new_value']} cannot be set as a default tester, "
            f"since this user does not exist."
        )


class PatchTestCaseStatusForm(PatchTestCaseBaseForm):
    new_value = forms.ModelChoiceField(
        queryset=TestCaseStatus.objects.only("name"),
        error_messages={
            "required": "Missing argument new_value.",
            "invalid_choice": "The status you choose does not exist.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields["case"]
        f.queryset = TestCase.objects.select_related("case_status").only("case_status__name")


class PatchTestCaseReviewerForm(PatchTestCaseBaseForm):
    new_value = forms.ModelChoiceField(
        queryset=User.objects.only("username"),
        to_field_name="username",
        error_messages={
            "required": "Missing argument new_value.",
            "invalid_choice": None,  # Set later inside __init__
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields["case"]
        f.queryset = TestCase.objects.select_related("reviewer").only("reviewer__username")
        f: forms.ModelChoiceField = self.fields["new_value"]
        f.error_messages["invalid_choice"] = f"Reviewer {self.data['new_value']} is not found"


class PatchTestCaseSortKeyForm(PatchTestCaseBaseForm):
    plan = forms.ModelChoiceField(
        queryset=TestPlan.objects.only("pk"),
        error_messages={
            "required": "Missing plan id.",
            "invalid_choice": None,  # Set later inside __init__
        },
    )
    new_value = forms.IntegerField(
        min_value=SORT_KEY_MIN,
        max_value=SORT_KEY_MAX,
        error_messages={
            "required": "Missing argument new_value to patch test cases.",
            "invalid": "Sort key must be a positive integer.",
            "min_value": f"New sortkey is out of range {SORT_KEY_RANGE}.",
            "max_value": f"New sortkey is out of range {SORT_KEY_RANGE}.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["case"].queryset = TestCase.objects.only("pk")
        f: forms.ModelChoiceField = self.fields["plan"]
        f.error_messages["invalid_choice"] = f"No plan with id {self.data['plan']} exists."


class PatchTestCasesView(ModelPatchBaseView):
    """Actions to update each possible property of TestCases"""

    permission_required = "testcases.change_testcase"
    simple_patches = {
        "priority": (PatchTestCasePriorityForm, False),
        "default_tester": (PatchTestCaseDefaultTesterForm, False),
        "case_status": (PatchTestCaseStatusForm, False),
        "reviewer": (PatchTestCaseReviewerForm, True),
    }
    targets_field_name: str = "case"

    def _sendmail(self, objects):
        mail_context = TestCase.mail_scene(
            objects=objects, field=self.target_field, value=self.new_value
        )
        if mail_context:
            from tcms.core.mailto import mailto

            mail_context["context"]["user"] = self.request.user
            mailto(**mail_context)

    def _update_sortkey(self):
        f = PatchTestCaseSortKeyForm(self._request_data)
        if not f.is_valid():
            return JsonResponseBadRequest({"message": form_error_messages_to_list(f)})

        cases = f.cleaned_data["case"]
        plan = f.cleaned_data["plan"]
        changed = []
        append_changed = changed.append
        new_sort_key = f.cleaned_data["new_value"]

        for tcp in TestCasePlan.objects.filter(plan=plan, case__in=cases):
            if tcp.sortkey == new_sort_key:
                continue
            tcp.sortkey = new_sort_key
            append_changed(tcp)

        TestCasePlan.objects.bulk_update(changed, [self.target_field])


@require_POST
def comment_case_runs(request):
    """
    Add comment to one or more caseruns at a time.
    """
    data = request.POST.copy()
    comment = data.get("comment", None)
    if not comment:
        return JsonResponseBadRequest({"message": "Comments needed"})
    run_ids = [int(item) for item in data.getlist("run")]
    if not run_ids:
        return JsonResponseBadRequest({"message": "No runs selected."})
    case_run_ids = TestCaseRun.objects.filter(pk__in=run_ids).values_list("pk", flat=True)
    if not case_run_ids:
        return JsonResponseBadRequest({"message": "No caserun found."})
    tcms.comments.models.add_comment(
        request.user,
        "testruns.testcaserun",
        case_run_ids,
        comment,
        request.META.get("REMOTE_ADDR"),
    )
    return JsonResponse({})

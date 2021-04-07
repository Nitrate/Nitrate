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
from typing import Any, Dict, NewType, List, Optional, Tuple, Union

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import models
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
from django.dispatch import Signal
from django.http import Http404, HttpResponse, JsonResponse
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
from tcms.testcases.views import plan_from_request_or_none
from tcms.testplans.models import TestPlan, TestCasePlan
from tcms.testruns import signals as run_watchers
from tcms.testruns.models import TestRun, TestCaseRun, TestCaseRunStatus
from tcms.core.utils import get_string_combinations

post_update = Signal(providing_args=["instances", "kwargs"])
post_update.connect(run_watchers.post_update_handler)

logger = logging.getLogger(__name__)

SORT_KEY_MIN = 0
SORT_KEY_MAX = 32300
SORT_KEY_RANGE = [SORT_KEY_MIN, SORT_KEY_MAX]


def is_sort_key_in_range(sort_key: int) -> bool:
    return SORT_KEY_MIN <= sort_key <= SORT_KEY_MAX


def strip_parameters(request_data, skip_parameters):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Will be set in the view method
        self.target_field = None
        self.new_value = None
        self._update_targets = None
        self._request_data = None

    def handle_no_permission(self) -> JsonResponseForbidden:
        return JsonResponseForbidden({"message": "You do not have permission to update."})

    def _sendmail(self):
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
        log_actions_info = [
            (
                model,
                [
                    {
                        "who": self.request.user,
                        "field": self.target_field,
                        "original_value": str(getattr(model, self.target_field)),
                        "new_value": str(new_value),
                    }
                ],
            )
            for model in models
        ]
        models.update(**{self.target_field: new_value})
        self._record_log_actions(log_actions_info)

    def get_update_targets(self) -> QuerySet:
        raise NotImplementedError("Must be implemented in subclass.")

    def get_update_action(self):
        return getattr(self, "_update_%s" % self.target_field, None)

    def patch(self, request: HttpRequest):
        self._request_data = json.loads(request.body)
        self.target_field = self._request_data.get("target_field")
        if not self.target_field:
            return JsonResponseBadRequest({"message": "Missing argument target_field."})
        self.new_value = self._request_data.get("new_value")
        if not self.new_value:
            return JsonResponseBadRequest({"message": "Missing argument new_value."})

        action = self.get_update_action()
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


class TestCaseRunsPatchView(ModelPatchBaseView):
    """Actions to update test case runs properties"""

    permission_required = "testruns.change_testcaserun"

    def get_update_targets(self) -> QuerySet:
        if self._update_targets is None:
            case_run_ids = [int(item) for item in self._request_data.get("case_run", [])]
            if case_run_ids:
                self._update_targets = TestCaseRun.objects.filter(pk__in=case_run_ids)
        return self._update_targets

    def _sendmail(self) -> None:
        mail_context = TestCaseRun.mail_scene(
            objects=self.get_update_targets(), field=self.target_field
        )
        if mail_context:
            mail_context["context"]["user"] = self.request.user
            mailto(**mail_context)

    def _update_assignee(self):
        new_assignee = User.objects.filter(pk=int(self.new_value)).only("username").first()
        if new_assignee is None:
            return JsonResponseBadRequest({"message": f"No user with id {self.new_value} exists."})
        case_runs = self.get_update_targets().select_related("assignee").only("assignee__username")
        if not case_runs:
            return JsonResponseBadRequest(
                {"message": "No specified test case run exists for update."}
            )
        self._simple_update(case_runs, new_assignee)
        self._sendmail()

    def _update_case_run_status(self):
        case_runs = (
            self.get_update_targets()
            .select_related("case_run_status", "tested_by")
            .only("close_date", "tested_by__username", "case_run_status__name")
        )
        if not self._update_targets:
            return JsonResponseBadRequest({"message": "No case run is specified to update."})
        request_user: User = self.request.user
        status = TestCaseRunStatus.objects.get(pk=int(self.new_value))
        update_time = datetime.datetime.now()

        case_run: TestCaseRun

        log_actions_info = []
        for case_run in case_runs:
            info = (
                case_run,
                [
                    {
                        "who": request_user,
                        "field": self.target_field,
                        "original_value": case_run.case_run_status.name,
                        "new_value": TestCaseRunStatus.id_to_name(self.new_value),
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
                info[1].append(
                    {
                        "who": request_user,
                        "field": "tested_by",
                        "original_value": case_run.tested_by,
                        "new_value": request_user.username,
                    }
                )
            log_actions_info.append(info)

        # FIXME: should close_date be set only when the complete status is set?

        update_params = {
            self.target_field: status,
            "close_date": update_time,
            "tested_by": request_user,
        }
        case_runs.update(**update_params)
        self._record_log_actions(log_actions_info)

    def _update_sortkey(self):
        if not isinstance(self.new_value, int):
            return JsonResponseBadRequest({"message": "The sortkey must be an integer."})
        new_sort_key = self.new_value
        if not is_sort_key_in_range(new_sort_key):
            return JsonResponseBadRequest(
                {"message": f"New sortkey is out of range {SORT_KEY_RANGE}."}
            )
        case_runs = self.get_update_targets().only("sortkey")
        if not case_runs:
            return JsonResponseBadRequest({"message": "No case run is specified to update."})
        self._simple_update(case_runs, new_sort_key)


class TestCasesPatchView(ModelPatchBaseView):
    """Actions to update each possible property of TestCases

    Define your own method named _update_[property name] to hold specific
    update logic.
    """

    permission_required = "testcases.change_testcase"

    def get_update_targets(self) -> QuerySet:
        """Get selected cases to update their properties"""
        if self._update_targets is None:
            item: str
            case_ids = [int(item) for item in self._request_data.get("case", [])]
            self._update_targets = TestCase.objects.filter(pk__in=case_ids)
        return self._update_targets

    def _sendmail(self):
        mail_context = TestCase.mail_scene(
            objects=self._update_targets, field=self.target_field, value=self.new_value
        )
        if mail_context:
            from tcms.core.mailto import mailto

            mail_context["context"]["user"] = self.request.user
            mailto(**mail_context)

    def _update_priority(self):
        new_priority = Priority.objects.filter(pk=self.new_value).first()
        if new_priority is None:
            raise ObjectDoesNotExist("The priority you specified to change does not exist.")
        cases = self.get_update_targets().select_related("priority").only("priority__value")
        self._simple_update(cases, new_priority)

    def _update_default_tester(self):
        new_default_tester = User.objects.filter(username=self.new_value).first()
        if new_default_tester is None:
            raise ObjectDoesNotExist(
                f"{self.new_value} cannot be set as a default tester, "
                f"since this user does not exist."
            )
        cases = (
            self.get_update_targets()
            .select_related("default_tester")
            .only("default_tester__username")
        )
        self._simple_update(cases, new_default_tester)

    def _update_case_status(self):
        new_status = TestCaseStatus.objects.filter(pk=self.new_value).first()
        if new_status is None:
            raise ObjectDoesNotExist("The status you choose does not exist.")

        cases = self.get_update_targets().select_related("case_status").only("case_status__name")
        self._simple_update(cases, new_status)
        return JsonResponse({})

    def _update_sortkey(self):
        if not is_sort_key_in_range(self.new_value):
            return JsonResponseBadRequest(
                {"message": f"New sortkey is out of range {SORT_KEY_RANGE}."}
            )
        plan_id: Optional[int] = self._request_data.get("plan")
        if plan_id is None:
            return JsonResponseBadRequest({"message": "Missing plan id."})
        plan = TestPlan.objects.filter(pk=plan_id).first()
        if plan is None:
            return JsonResponseBadRequest({"message": f"No plan with id {plan_id} exists."})
        # FIXME: read the plan id from the json data
        update_targets = self.get_update_targets()

        # ##
        # MySQL does not allow to execute UPDATE statement that contains
        # subquery querying from same table. In this case, OperationError will
        # be raised.
        offset = 0
        step_length = 500
        queryset_filter = TestCasePlan.objects.filter
        data = {self.target_field: self.new_value}
        while 1:
            sub_cases = update_targets[offset : offset + step_length]
            case_pks = [case.pk for case in sub_cases]
            if len(case_pks) == 0:
                break
            queryset_filter(plan=plan, case__in=case_pks).update(**data)
            # Move to next batch of cases to change.
            offset += step_length

    def _update_reviewer(self):
        user = User.objects.filter(username=self.new_value).first()
        if user is None:
            raise ObjectDoesNotExist(f"Reviewer {self.new_value} is not found")
        cases = self.get_update_targets().select_related("reviewer").only("reviewer__username")
        self._simple_update(cases, user)
        self._sendmail()


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

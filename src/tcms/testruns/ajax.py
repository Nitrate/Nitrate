# -*- coding: utf-8 -*-

import logging
from operator import attrgetter

from django import forms
from django.contrib.auth.decorators import permission_required
from django.core.validators import ValidationError
from django.http import JsonResponse
from django.shortcuts import Http404, get_object_or_404
from django.views.decorators.http import require_GET

from tcms.core.responses import JsonResponseBadRequest, JsonResponseForbidden, JsonResponseNotFound
from tcms.core.utils import form_error_messages_to_list
from tcms.issuetracker.models import Issue
from tcms.issuetracker.services import find_service
from tcms.testcases.forms import CaseRunIssueForm
from tcms.testruns.models import TestCaseRun, TestRun

logger = logging.getLogger(__name__)


# TODO: Split this actions class into individual view.


@require_GET
@permission_required("testruns.change_testrun")
def manage_case_run_issues(request, run_id):
    """Process the issues for case runs."""

    class CaseRunIssueActions:
        __all__ = ["add", "remove"]

        def __init__(self, request, run):
            self.request = request
            self.run = run

        def add(self):
            # TODO: make a migration for the permission
            if not self.request.user.has_perm("issuetracker.add_issue"):
                return JsonResponseForbidden({"message": "Permission denied."})

            form = CaseRunIssueForm(request.GET)

            if not form.is_valid():
                return JsonResponseBadRequest({"message": form_error_messages_to_list(form)})

            service = find_service(form.cleaned_data["tracker"])
            issue_key = form.cleaned_data["issue_key"]
            link_et = form.cleaned_data["link_external_tracker"]
            case_runs = form.cleaned_data["case_run"]

            # FIXME: maybe, make sense to validate in the form.
            if not all(case_run.run_id == self.run.pk for case_run in case_runs):
                return JsonResponseBadRequest(
                    {"message": f"Not all case runs belong to run {self.run.pk}."}
                )

            try:
                for case_run in case_runs:
                    service.add_issue(
                        issue_key,
                        case_run.case,
                        case_run=case_run,
                        add_case_to_issue=link_et,
                    )
            except ValidationError as e:
                logger.exception(
                    "Failed to add issue to case run %s. Error reported: %s",
                    form.case_run.pk,
                    str(e),
                )
                return JsonResponseBadRequest({"message": str(e)})

            return self.run_issues_info(case_runs)

        def remove(self):
            if not self.request.user.has_perm("issuetracker.delete_issue"):
                return JsonResponseForbidden({"message": "Permission denied."})

            class RemoveIssueForm(forms.Form):
                issue_key = forms.CharField()
                case_run = forms.ModelMultipleChoiceField(
                    queryset=TestCaseRun.objects.all().only("pk"),
                    error_messages={
                        "required": "Case run id is missed.",
                        "invalid_pk_value": "Case run %(pk)s does not exist.",
                    },
                )

            form = RemoveIssueForm(request.GET)
            if not form.is_valid():
                return JsonResponseBadRequest({"message": form_error_messages_to_list(form)})

            issue_key = form.cleaned_data["issue_key"]
            case_runs = form.cleaned_data["case_run"]
            for case_run in case_runs:
                try:
                    case_run.remove_issue(issue_key)
                except Exception:
                    msg = "Failed to remove issue {} from case run {}".format(
                        issue_key, case_run.pk
                    )
                    logger.exception(msg)
                    return JsonResponseBadRequest({"message": msg})

            return self.run_issues_info(case_runs)

        def run_issues_info(self, case_runs):
            """Return a JSON response including run's issues info"""
            return JsonResponse(
                {
                    # The total number of issues this run has
                    "run_issues_count": self.run.get_issues_count(),
                    # The number of issues each of case run has
                    "caserun_issues_count": Issue.count_by_case_run(
                        list(map(attrgetter("pk"), case_runs))
                    ),
                }
            )

    try:
        run = get_object_or_404(TestRun, pk=run_id)
    except Http404:
        return JsonResponseNotFound({"message": f"Test run {run_id} does not exist."})

    crba = CaseRunIssueActions(request=request, run=run)

    if not request.GET.get("a") in crba.__all__:
        return JsonResponseBadRequest({"message": "Unrecognizable actions"})

    func = getattr(crba, request.GET["a"])
    return func()

# -*- coding: utf-8 -*-

import logging

from django import forms
from django.contrib.auth.decorators import permission_required
from django.core.validators import ValidationError
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from tcms.integration.issuetracker.models import IssueTracker
from tcms.integration.issuetracker.services import find_service
from tcms.testcases.forms import CaseIssueForm
from tcms.testruns.models import TestCaseRun
from tcms.utils import HTTP_BAD_REQUEST
from tcms.utils import HTTP_FORBIDDEN
from tcms.utils import HTTP_NOT_FOUND
from tcms.utils import form_errors_to_list

logger = logging.getLogger(__name__)


# TODO: Split this actions class into individual view.

@require_GET
@permission_required('testruns.change_testrun')
def manage_case_run_issues(request, case_run_id):
    """Process the issues for case runs."""

    class CaseRunIssueActions(object):
        __all__ = ['add', 'file', 'remove', 'render_form']

        def __init__(self, request, case_run):
            self.request = request
            self.case_run = case_run

        def add(self):
            # TODO: make a migration for the permission
            if not self.request.user.has_perm('testcases.add_testcasebug'):
                return JsonResponse({'messages': ['Permission denied.']},
                                    status=HTTP_FORBIDDEN)

            form = CaseIssueForm(request.GET)

            if not form.is_valid():
                msgs = form_errors_to_list(form)
                return JsonResponse({'messages': msgs}, status=HTTP_BAD_REQUEST)

            try:
                service = find_service(form.cleaned_data['tracker'])
                service.add_issue(
                    form.cleaned_data['issue_key'],
                    form.cleaned_data['case'],
                    case_run=form.cleaned_data['case_run'],
                    add_case_to_issue=form.cleaned_data['link_external_tracker'])
            except ValidationError as e:
                logger.exception(
                    'Failed to add issue to case run %s. Error reported: %s',
                    form.case_run.pk, str(e))
                return JsonResponse({'messages': [str(e)]}, status=HTTP_BAD_REQUEST)

            return JsonResponse({
                'run_issues_count': self.get_run_issues_count(),
                'caserun_issues_count': self.case_run.issues.count(),
            })

        def file(self):
            # This name should be get from rendered webpage dynamically.
            # It is hardcoded as a temporary solution right now.
            # FIXME: name here should be RHBugzilla in final solution.
            bz_model = IssueTracker.objects.get(name='Bugzilla')
            # An eventual solution would be to just call this method
            # and pass loaded issue tracker name.
            url = find_service(bz_model).make_issue_report_url(self.case_run)

            return HttpResponseRedirect(url)

        def remove(self):
            if not self.request.user.has_perm('testcases.delete_testcasebug'):
                return JsonResponse({'messages': ['Permission denied.']},
                                    status=HTTP_FORBIDDEN)

            class RemoveIssueForm(forms.Form):
                issue_key = forms.CharField()
                case_run = forms.ModelChoiceField(
                    queryset=TestCaseRun.objects.all().only('pk'),
                    error_messages={
                        'invalid_choice': 'Case run does not exist.',
                    },
                )

            form = RemoveIssueForm(request.GET)
            if not form.is_valid():
                return JsonResponse({'messages': form_errors_to_list(form)},
                                    status=HTTP_BAD_REQUEST)

            try:
                self.case_run.remove_issue(form.cleaned_data['issue_key'],
                                           form.cleaned_data['case_run'])
            except Exception:
                msg = 'Failed to remove issue {} from case run {}'.format(
                    form.cleaned_data['issue_key'],
                    form.cleaned_data['case_run'].pk
                )
                logger.exception(msg)
                return JsonResponse({'messages': [msg]}, status=HTTP_BAD_REQUEST)

            return JsonResponse({
                'run_issues_count': self.get_run_issues_count(),
                'caserun_issues_count': self.case_run.issues.count(),
            })

        def render_form(self):
            form = CaseIssueForm(initial={
                'case_run': self.case_run.case_run_id,
                'case': self.case_run.case_id,
            })
            if self.request.GET.get('type') == 'table':
                return HttpResponse(form.as_table())

            return HttpResponse(form.as_p())

        def get_run_issues_count(self):
            return self.case_run.run.get_issues_count()

    try:
        tcr = get_object_or_404(TestCaseRun, pk=case_run_id)
    except Http404:
        return JsonResponse(
            {'messages': ['Case run {} does not exist.'.format(case_run_id)]},
            status=HTTP_NOT_FOUND)

    crba = CaseRunIssueActions(request=request, case_run=tcr)

    if not request.GET.get('a') in crba.__all__:
        return JsonResponse({'messages': ['Unrecognizable actions']},
                            status=HTTP_BAD_REQUEST)

    func = getattr(crba, request.GET['a'])
    return func()

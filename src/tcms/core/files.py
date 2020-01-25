# -*- coding: utf-8 -*-

import os
import logging

from datetime import datetime

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import smart_str
from django.views import generic
from django.views.decorators.http import require_GET
from six.moves.urllib_parse import unquote

from tcms.core.views import Prompt
from tcms.testcases.models import TestCase, TestCaseAttachment
from tcms.testplans.models import TestPlan, TestPlanAttachment
from tcms.management.models import TestAttachment, TestAttachmentData

log = logging.getLogger(__name__)


class UploadFileView(PermissionRequiredMixin, generic.View):
    """Upload a file"""

    permission_required = 'management.add_testattachment'

    def post(self, request):
        to_plan_id = request.POST.get('to_plan_id')
        to_case_id = request.POST.get('to_case_id')

        if to_plan_id is None and to_case_id is None:
            return Prompt.render(
                request=request,
                info_type=Prompt.Alert,
                info='Uploading file works with plan or case. Nitrate cannot '
                     'proceed with no plan or case ID.',
                next='javascript:window.history.go(-1);',
            )

        if request.FILES.get('upload_file'):
            upload_file = request.FILES['upload_file']

            try:
                upload_file.name.encode('utf8')
            except UnicodeEncodeError:
                return Prompt.render(
                    request=request,
                    info_type=Prompt.Alert,
                    info='Upload File name is not legal.',
                    next='javascript:window.history.go(-1);',
                )

            now = datetime.now()

            stored_name = f'{request.user.username}-{now}-{upload_file.name}'

            stored_file_name = os.path.join(
                settings.FILE_UPLOAD_DIR, stored_name).replace('\\', '/')
            stored_file_name = smart_str(stored_file_name)

            if upload_file.size > settings.MAX_UPLOAD_SIZE:
                return Prompt.render(
                    request=request,
                    info_type=Prompt.Alert,
                    info=f'You upload entity is too large. Please ensure the file is'
                         f' less than {settings.MAX_UPLOAD_SIZE} bytes.',
                    next='javascript:window.history.go(-1);',
                )

            # Create the upload directory when it's not exist
            if not os.path.exists(settings.FILE_UPLOAD_DIR):
                os.mkdir(settings.FILE_UPLOAD_DIR)

            if os.path.exists(stored_file_name):
                return Prompt.render(
                    request=request,
                    info_type=Prompt.Alert,
                    info=f"File named '{upload_file.name}' already exists in "
                         f"upload folder, please rename to another name for "
                         f"solve conflict.",
                    next='javascript:window.history.go(-1);',
                )

            with open(stored_file_name, 'wb+') as f:
                for chunk in upload_file.chunks():
                    f.write(chunk)

            # Write the file to database
            # store_file = open(upload_file_name, 'ro')
            ta = TestAttachment.objects.create(
                submitter_id=request.user.id,
                description=request.POST.get('description', None),
                file_name=upload_file.name,
                stored_name=stored_name,
                create_date=now,
                mime_type=upload_file.content_type
            )

            if request.POST.get('to_plan_id'):
                TestPlanAttachment.objects.create(
                    plan_id=int(to_plan_id),
                    attachment_id=ta.attachment_id,
                )
                return HttpResponseRedirect(
                    reverse('plan-attachment', args=[to_plan_id]))

            if request.POST.get('to_case_id'):
                TestCaseAttachment.objects.create(
                    attachment_id=ta.attachment_id,
                    case_id=int(to_case_id))
                return HttpResponseRedirect(
                    reverse('case-attachment', args=[to_case_id]))
        else:
            if 'to_plan_id' in request.POST:
                return HttpResponseRedirect(
                    reverse('plan-attachment', args=[to_plan_id]))
            if 'to_case_id' in request.POST:
                return HttpResponseRedirect(
                    reverse('case-attachment', args=[to_case_id]))


@require_GET
def check_file(request, file_id):
    """Download attachment file"""
    attachment = get_object_or_404(TestAttachment, pk=file_id)

    attachment_data = TestAttachmentData.objects.filter(
        attachment__attachment_id=file_id
    ).first()

    # First try to read file content from database.
    if attachment_data:
        # File content is not written into TestAttachmentData in upload_file,
        # this code path is dead now. Think about if file content should be
        # written into database in the future.
        contents = attachment_data.contents
    else:
        # File was not written into database, read it from configured file
        # system.
        stored_file_name = os.path.join(
            settings.FILE_UPLOAD_DIR,
            unquote(attachment.stored_name or attachment.file_name)
        ).replace('\\', '/')

        if not os.path.exists(stored_file_name):
            raise Http404(f'Attachment file {stored_file_name} does not exist.')

        try:
            with open(stored_file_name, 'rb') as f:
                contents = f.read()
        except IOError:
            msg = 'Cannot read attachment file from server.'
            log.exception(msg)
            return Prompt.render(
                request=request,
                info_type=Prompt.Alert,
                info=msg,
                next='javascript:window.history.go(-1);',
            )

    response = HttpResponse(contents, content_type=str(attachment.mime_type))
    file_name = smart_str(attachment.file_name)
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return response


def able_to_delete_attachment(request, file_id):
    """
    These are allowed to delete attachment -
        1. super user
        2. attachments's submitter
        3. testplan's author or owner
        4. testcase's owner
    """

    user = request.user
    if user.is_superuser:
        return True

    attach = TestAttachment.objects.get(attachment_id=file_id)
    if user.pk == attach.submitter_id:
        return True

    if 'from_plan' in request.GET:
        plan_id = int(request.GET['from_plan'])
        plan = TestPlan.objects.get(plan_id=plan_id)
        return user.pk == plan.owner_id or user.pk == plan.author_id

    if 'from_case' in request.GET:
        case_id = int(request.GET['from_case'])
        case = TestCase.objects.get(case_id=case_id)
        return user.pk == case.author_id

    return False


# Delete Attachment
def delete_file(request, file_id):
    ajax_response = {'rc': 0, 'response': 'ok'}
    DELEFAILURE = 1
    AUTHUNSUCCESS = 2

    state = able_to_delete_attachment(request, file_id)
    if not state:
        ajax_response['rc'] = AUTHUNSUCCESS
        ajax_response['response'] = 'auth_failure'
        return JsonResponse(ajax_response)

    # Delete plan's attachment
    if 'from_plan' in request.GET:
        try:
            plan_id = int(request.GET['from_plan'])
            attachment = TestPlanAttachment.objects.filter(attachment=file_id,
                                                           plan_id=plan_id)
            attachment.delete()
        except TestPlanAttachment.DoesNotExist:
            ajax_response['rc'] = DELEFAILURE
            ajax_response['response'] = 'failure'
        return JsonResponse(ajax_response)

    # Delete cases' attachment
    elif 'from_case' in request.GET:
        try:
            case_id = int(request.GET['from_case'])
            attachment = TestCaseAttachment.objects.filter(attachment=file_id,
                                                           case_id=case_id)
            attachment.delete()
        except TestCaseAttachment.DoesNotExist:
            ajax_response['rc'] = DELEFAILURE
            ajax_response['response'] = 'failure'

        return JsonResponse(ajax_response)

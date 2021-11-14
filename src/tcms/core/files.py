# -*- coding: utf-8 -*-
import hashlib
import logging
import os
import time
import urllib.parse
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.files.uploadedfile import UploadedFile
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import smart_str
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from tcms.core.views import prompt
from tcms.management.models import TestAttachment, TestAttachmentData
from tcms.testcases.models import TestCase, TestCaseAttachment
from tcms.testplans.models import TestPlan, TestPlanAttachment

log = logging.getLogger(__name__)


def calculate_checksum(uploaded_file: UploadedFile) -> str:
    md5 = hashlib.md5()
    for chunk in uploaded_file.chunks():
        md5.update(chunk)
    return md5.hexdigest()


class UploadFileView(PermissionRequiredMixin, generic.View):
    """Upload a file"""

    permission_required = "management.add_testattachment"

    @method_decorator(csrf_protect)
    def post(self, request):
        to_plan_id = request.POST.get("to_plan_id")
        to_case_id = request.POST.get("to_case_id")

        if to_plan_id is None and to_case_id is None:
            return prompt.alert(
                request,
                "Uploading file works with plan or case. Nitrate cannot "
                "proceed without plan or case ID.",
            )

        if to_plan_id is not None:
            redirect_url = reverse("plan-attachment", args=[to_plan_id])
            create_rel = TestPlanAttachment.objects.create
            rel_kwargs = {"plan_id": int(to_plan_id)}
        else:
            redirect_url = reverse("case-attachment", args=[to_case_id])
            create_rel = TestCaseAttachment.objects.create
            rel_kwargs = {"case_id": int(to_case_id)}

        upload_file = request.FILES.get("upload_file")

        if not upload_file:
            return HttpResponseRedirect(redirect_url)

        upload_file: UploadedFile = request.FILES["upload_file"]

        if upload_file.size > settings.MAX_UPLOAD_SIZE:
            return prompt.alert(
                request,
                f"You upload entity is too large. Please ensure the file "
                f"is less than {settings.MAX_UPLOAD_SIZE} bytes.",
            )

        uploaded_filename = upload_file.name
        try:
            uploaded_filename.encode()
        except UnicodeEncodeError:
            return prompt.alert(request, "Upload File name is not legal.")

        # Create the upload directory when it's not exist
        if not os.path.exists(settings.FILE_UPLOAD_DIR):
            os.mkdir(settings.FILE_UPLOAD_DIR)

        checksum = calculate_checksum(upload_file)
        attachment = TestAttachment.objects.filter(checksum=checksum).first()

        if attachment is not None:
            if attachment.file_name == uploaded_filename:
                return prompt.alert(request, f"File {uploaded_filename} has been uploaded already.")
            else:
                return prompt.alert(
                    request,
                    f"A file {attachment.file_name} having same content has "
                    f"been uploaded previously.",
                )

        stored_name = "{}-{}-{}".format(request.user.username, time.time(), uploaded_filename)
        attachment = TestAttachment(
            submitter_id=request.user.id,
            description=request.POST.get("description", None),
            file_name=uploaded_filename,
            stored_name=stored_name,
            mime_type=upload_file.content_type,
            checksum=checksum,
        )

        with open(attachment.stored_filename, "wb+") as f:
            for chunk in upload_file.chunks():
                f.write(chunk)

        attachment.save()

        rel_kwargs["attachment"] = attachment
        create_rel(**rel_kwargs)
        return HttpResponseRedirect(redirect_url)


@require_GET
def check_file(request, file_id):
    """Download attachment file"""
    attachment = get_object_or_404(TestAttachment, pk=file_id)

    attachment_data = TestAttachmentData.objects.filter(attachment__attachment_id=file_id).first()

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
            urllib.parse.unquote(attachment.stored_name or attachment.file_name),
        ).replace("\\", "/")

        if not os.path.exists(stored_file_name):
            raise Http404(f"Attachment file {stored_file_name} does not exist.")

        try:
            with open(stored_file_name, "rb") as f:
                contents = f.read()
        except IOError:
            msg = "Cannot read attachment file from server."
            log.exception(msg)
            return prompt.alert(request, msg)

    response = HttpResponse(contents, content_type=str(attachment.mime_type))
    file_name = smart_str(attachment.file_name)
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


def able_to_delete_attachment(request, file_id: int) -> bool:
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

    if "from_plan" in request.POST:
        plan_id = int(request.POST["from_plan"])
        plan = TestPlan.objects.get(plan_id=plan_id)
        return user.pk == plan.owner_id or user.pk == plan.author_id

    if "from_case" in request.POST:
        case_id = int(request.POST["from_case"])
        case = TestCase.objects.get(case_id=case_id)
        return user.pk == case.author_id

    return False


# Delete Attachment
@require_POST
def delete_file(request):
    file_id = int(request.POST["file_id"])
    state = able_to_delete_attachment(request, file_id)
    if not state:
        return JsonResponse(
            {
                "message": f"User {request.user.username} is not allowed to "
                f"delete the attachment."
            },
            status=HTTPStatus.UNAUTHORIZED,
        )

    # Delete plan's attachment
    if "from_plan" in request.POST:
        plan_id = int(request.POST["from_plan"])
        try:
            rel = TestPlanAttachment.objects.get(attachment=file_id, plan_id=plan_id)
        except TestPlanAttachment.DoesNotExist:
            return JsonResponse(
                {"message": f"Attachment {file_id} does not belong to plan {plan_id}."},
                status=HTTPStatus.BAD_REQUEST,
            )
        else:
            rel.delete()

        attachment = rel.attachment
        msg = f"Attachment {attachment.file_name} is removed from plan {plan_id} successfully."
        attachment.delete()
        os.unlink(attachment.stored_filename)

        return JsonResponse({"message": msg})

    # Delete cases' attachment
    elif "from_case" in request.POST:
        case_id = int(request.POST["from_case"])
        try:
            rel = TestCaseAttachment.objects.get(attachment=file_id, case_id=case_id)
        except TestCaseAttachment.DoesNotExist:
            return JsonResponse(
                {"message": f"Attachment {file_id} does not belong to case {case_id}."},
                status=HTTPStatus.BAD_REQUEST,
            )
        else:
            rel.delete()

        attachment = rel.attachment
        msg = f"Attachment {attachment.file_name} is removed from case {case_id} successfully."
        attachment.delete()
        os.unlink(attachment.stored_filename)

        return JsonResponse({"message": msg})

    else:
        return JsonResponse(
            {"message": "Unknown from where to remove the attachment."},
            status=HTTPStatus.BAD_REQUEST,
        )

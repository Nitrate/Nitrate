# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
from datetime import datetime
from http import HTTPStatus
from typing import Optional
from unittest.mock import patch

from django.conf import settings
from django.db.models import Max
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse

from tcms.core.files import able_to_delete_attachment
from tcms.core.utils import checksum
from tcms.management.models import TestAttachment
from tcms.testcases.models import TestCase, TestCaseAttachment
from tcms.testplans.models import TestPlan, TestPlanAttachment
from tests import BasePlanCase
from tests import factories as f
from tests import user_should_have_perm


class TestUploadFile(BasePlanCase):
    """Test view upload_file"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.upload_file_url = reverse("upload-file")

        user_should_have_perm(cls.tester, "management.add_testattachment")
        user_should_have_perm(cls.tester, "testcases.add_testcaseattachment")

    def setUp(self):
        super().setUp()

        klass_name = self.__class__.__name__
        self.working_dir = tempfile.mkdtemp(prefix=klass_name)

        file_content: bytes = b"abc" * 100

        fd, self.upload_filename = tempfile.mkstemp(
            suffix=f"{klass_name}-upload-file.txt", dir=self.working_dir
        )
        os.write(fd, file_content)
        os.close(fd)

        fd, self.another_filename = tempfile.mkstemp(
            suffix=f"{klass_name}-another-file.txt", dir=self.working_dir
        )
        os.write(fd, file_content)
        os.close(fd)

    def tearDown(self):
        shutil.rmtree(self.working_dir)
        super().tearDown()

    def test_no_file_is_posted(self):
        response = self.client.post(reverse("upload-file"), {"to_plan_id": self.plan.pk})
        self.assertRedirects(response, reverse("plan-attachment", args=[self.plan.pk]))

        response = self.client.post(reverse("upload-file"), {"to_case_id": self.case_1.pk})
        self.assertRedirects(response, reverse("case-attachment", args=[self.case_1.pk]))

    @patch("tcms.core.files.settings.MAX_UPLOAD_SIZE", new=10)
    def test_refuse_if_file_is_too_big(self):
        response = self._upload_attachment(
            self.upload_filename, self.upload_file_url, to_plan=self.plan
        )
        self.assertContains(response, "You upload entity is too large")

    def _upload_attachment(
        self,
        filename: str,
        endpoint: str,
        to_case: Optional[TestCase] = None,
        to_plan: Optional[TestPlan] = None,
    ):
        with patch("tcms.core.files.settings.FILE_UPLOAD_DIR", new=self.working_dir):
            with open(filename, "r") as upload_file:
                post_data = {"upload_file": upload_file}
                if to_plan:
                    post_data["to_plan_id"] = to_plan.pk
                elif to_case:
                    post_data["to_case_id"] = to_case.pk
                else:
                    raise ValueError("Missing value from both argument to_plan and to_case.")
                return self.client.post(endpoint, post_data)

    def test_upload_file_to_plan(self):
        response = self._upload_attachment(
            self.upload_filename, self.upload_file_url, to_plan=self.plan
        )

        self.assertRedirects(response, reverse("plan-attachment", args=[self.plan.pk]))

        attachments = list(
            TestAttachment.objects.filter(file_name=os.path.basename(self.upload_filename))
        )
        self.assertTrue(attachments)

        attachment = attachments[0]
        self.assertEqual(self.tester.pk, attachment.submitter.pk)

        plan_attachment_rel_exists = TestPlanAttachment.objects.filter(
            plan=self.plan, attachment=attachment
        ).exists()
        self.assertTrue(plan_attachment_rel_exists)

    def test_upload_file_to_case(self):
        response = self._upload_attachment(
            self.upload_filename, self.upload_file_url, to_case=self.case_1
        )

        self.assertRedirects(response, reverse("case-attachment", args=[self.case_1.pk]))

        attachments = list(
            TestAttachment.objects.filter(file_name=os.path.basename(self.upload_filename))
        )
        self.assertTrue(attachments)

        attachment = attachments[0]
        self.assertEqual(self.tester.pk, attachment.submitter.pk)

        case_attachment_rel_exists = TestCaseAttachment.objects.filter(
            case=self.case_1, attachment=attachment
        ).exists()
        self.assertTrue(case_attachment_rel_exists)

    def test_missing_both_plan_id_and_case_id(self):
        with open(self.upload_filename, "r") as upload_file:
            response = self.client.post(self.upload_file_url, {"upload_file": upload_file})

        self.assertContains(response, "Nitrate cannot proceed without plan or case ID")

    def test_file_is_uploaded_already(self):
        self._upload_attachment(self.upload_filename, self.upload_file_url, to_case=self.case_1)
        response = self._upload_attachment(
            self.upload_filename, self.upload_file_url, to_case=self.case_1
        )

        filename = os.path.basename(self.upload_filename)
        self.assertContains(response, f"File {filename} has been uploaded already")

    def test_another_file_with_same_content_is_uploaded_already(self):
        self._upload_attachment(self.upload_filename, self.upload_file_url, to_case=self.case_1)

        response = self._upload_attachment(
            self.another_filename, self.upload_file_url, to_case=self.case_1
        )

        filename = os.path.basename(self.upload_filename)
        self.assertContains(
            response,
            f"A file {filename} having same content has been uploaded previously",
        )


class TestAbleToDeleteFile(BasePlanCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.superuser = f.UserFactory(username="admin")
        cls.superuser.is_superuser = True
        cls.superuser.set_password("admin")
        cls.superuser.save()

        cls.anyone_else = f.UserFactory()

        cls.attachment = f.TestAttachmentFactory()

    def setUp(self):
        super().setUp()

        self.request = RequestFactory()

    def test_superuser_can(self):
        request = self.request.post(reverse("delete-file"))
        request.user = self.superuser
        self.assertTrue(able_to_delete_attachment(request, self.attachment.pk))

    def test_attachment_submitter_can(self):
        request = self.request.post(reverse("delete-file"))
        request.user = self.attachment.submitter
        self.assertTrue(able_to_delete_attachment(request, self.attachment.pk))

    def test_plan_author_can(self):
        request = self.request.post(
            reverse("delete-file"),
            {"file_id": self.attachment.pk, "from_plan": self.plan.pk},
        )
        request.user = self.plan.author
        self.assertTrue(able_to_delete_attachment(request, self.attachment.pk))

    def test_plan_owner_can(self):
        request = self.request.post(
            reverse("delete-file"),
            {"file_id": self.attachment.pk, "from_plan": self.plan.pk},
        )
        request.user = self.plan.owner
        self.assertTrue(able_to_delete_attachment(request, self.attachment.pk))

    def test_case_owner_can(self):
        request = self.request.post(
            reverse("delete-file"),
            {"file_id": self.attachment.pk, "from_case": self.case_1.pk},
        )
        request.user = self.case_1.author
        self.assertTrue(able_to_delete_attachment(request, self.attachment.pk))

    def test_cannot_delete_by_others(self):
        request = self.request.post(
            reverse("delete-file"),
            {"file_id": self.attachment.pk, "from_case": self.case_1.pk},
        )
        request.user = self.anyone_else
        self.assertFalse(able_to_delete_attachment(request, self.attachment.pk))

    def test_missing_both_plan_and_case_id(self):
        request = self.request.post(
            reverse("delete-file"),
            {
                "file_id": self.attachment.pk,
            },
        )
        request.user = self.case_1.author
        self.assertFalse(able_to_delete_attachment(request, self.attachment.pk))


class TestDeleteFileAuthorization(BasePlanCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.superuser = f.UserFactory(username="admin")
        cls.superuser.set_password("admin")
        cls.superuser.save()

        cls.anyone_else = f.UserFactory()
        cls.anyone_else_pwd = "anyone"
        cls.anyone_else.set_password(cls.anyone_else_pwd)
        cls.anyone_else.save()

        cls.plan_attachment = f.TestAttachmentFactory()
        cls.plan_attachment_rel = f.TestPlanAttachmentFactory(
            plan=cls.plan, attachment=cls.plan_attachment
        )
        cls.submitter_pwd = "secret"
        cls.plan_attachment.submitter.set_password(cls.submitter_pwd)
        cls.plan_attachment.submitter.save()

        cls.case_attachment = f.TestAttachmentFactory()
        cls.case_attachment_rel = f.TestCaseAttachmentFactory(
            case=cls.case_1, attachment=cls.case_attachment
        )
        cls.case_attachment.submitter.set_password(cls.submitter_pwd)
        cls.case_attachment.submitter.save()

    def test_refuse_if_user_cannot_delete_file(self):
        self.client.login(username=self.anyone_else.username, password=self.anyone_else_pwd)

        response = self.client.post(
            reverse("delete-file"),
            {"file_id": self.plan_attachment.pk, "from_plan": self.plan.pk},
        )

        self.assertEqual(HTTPStatus.UNAUTHORIZED, response.status_code)

    @patch("os.unlink")
    def test_delete_attachment_from_plan(self, unlink):
        self.client.login(
            username=self.plan_attachment.submitter.username,
            password=self.submitter_pwd,
        )

        stored_filename = self.plan_attachment.stored_filename

        response = self.client.post(
            reverse("delete-file"),
            {"file_id": self.plan_attachment.pk, "from_plan": self.plan.pk},
        )

        unlink.assert_called_once_with(stored_filename)

        self.assertEqual(HTTPStatus.OK, response.status_code)
        still_has = self.plan.attachments.filter(pk=self.plan_attachment.pk).exists()
        self.assertFalse(still_has)
        self.assertFalse(TestAttachment.objects.filter(pk=self.plan_attachment.pk).exists())

    @patch("os.unlink")
    def test_delete_attachment_from_case(self, unlink):
        self.client.login(
            username=self.case_attachment.submitter.username,
            password=self.submitter_pwd,
        )

        stored_filename = self.case_attachment.stored_filename

        response = self.client.post(
            reverse("delete-file"),
            {"file_id": self.case_attachment.pk, "from_case": self.case_1.pk},
        )

        unlink.assert_called_once_with(stored_filename)

        self.assertEqual(HTTPStatus.OK, response.status_code)
        still_has = self.case_1.attachments.filter(pk=self.case_attachment.pk).exists()
        self.assertFalse(still_has)
        self.assertFalse(TestAttachment.objects.filter(pk=self.case_attachment.pk).exists())

    def test_missing_both_plan_and_case_id(self):
        self.client.login(
            username=self.plan_attachment.submitter.username,
            password=self.submitter_pwd,
        )

        response = self.client.post(
            reverse("delete-file"),
            {
                "file_id": self.plan_attachment.pk,
            },
        )

        self.assertJsonResponse(
            response,
            {"message": "Unknown from where to remove the attachment."},
            status_code=HTTPStatus.BAD_REQUEST,
        )


class TestCheckFile(BasePlanCase):
    """Test view method check_file to download an attachment file"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.upload_dir = tempfile.mkdtemp()

        cls.text_file_content = "hello Nitrate"
        with open(os.path.join(cls.upload_dir, "a-1.txt"), "w", encoding="utf-8") as f:
            f.write(cls.text_file_content)

        cls.binary_file_content = b"\x00\x01\x11\x10"
        with open(os.path.join(cls.upload_dir, "b.bin"), "wb") as f:
            f.write(cls.binary_file_content)

        cls.logo_png_content = b"\x00\x01\x10"
        with open(os.path.join(cls.upload_dir, "logo.png"), "wb") as f:
            f.write(cls.logo_png_content)

        cls.text_file = TestAttachment.objects.create(
            submitter_id=cls.tester.id,
            description="description",
            file_name="a.txt",
            stored_name="a-1.txt",
            create_date=datetime.now(),
            mime_type="text/plain",
            checksum=checksum(cls.text_file_content),
        )
        cls.binary_file = TestAttachment.objects.create(
            submitter_id=cls.tester.id,
            description="binary file",
            file_name="b.txt",
            stored_name="b.bin",
            create_date=datetime.now(),
            mime_type="application/x-binary",
            checksum=checksum(cls.binary_file_content),
        )
        cls.logo_png = TestAttachment.objects.create(
            submitter_id=cls.tester.id,
            description="binary file",
            file_name="logo.png",
            # stored_name is not set, use file_name to find out attachment instead.
            stored_name=None,
            create_date=datetime.now(),
            mime_type="image/png",
            checksum=checksum(cls.logo_png_content),
        )
        cls.file_deleted = TestAttachment.objects.create(
            submitter_id=cls.tester.id,
            description="case plan",
            file_name="case-plan.txt",
            stored_name=None,
            create_date=datetime.now(),
            mime_type="text/plain",
            checksum="1234567",
        )

    def test_file_id_does_not_exist(self):
        # Calculate a non-existing attachment id. If there is no attachment in
        # database, 1 is expected.
        file_id = (TestAttachment.objects.aggregate(max_id=Max("pk"))["max_id"] or 0) + 1
        resp = self.client.get(reverse("check-file", args=[file_id]))
        self.assert404(resp)

    def test_download_text_file(self):
        with patch.object(settings, "FILE_UPLOAD_DIR", self.upload_dir):
            resp = self.client.get(reverse("check-file", args=[self.text_file.pk]))
        self.assertEqual("text/plain", resp["Content-Type"])
        self.assertEqual('attachment; filename="a.txt"', resp["Content-Disposition"])
        self.assertEqual(self.text_file_content, resp.content.decode("utf-8"))

    def test_download_binary_file(self):
        with patch.object(settings, "FILE_UPLOAD_DIR", self.upload_dir):
            resp = self.client.get(reverse("check-file", args=[self.binary_file.pk]))
        self.assertEqual("application/x-binary", resp["Content-Type"])
        self.assertEqual('attachment; filename="b.txt"', resp["Content-Disposition"])
        self.assertEqual(self.binary_file_content, resp.content)

    def test_use_original_filename_to_find_out_attachment(self):
        with patch.object(settings, "FILE_UPLOAD_DIR", self.upload_dir):
            resp = self.client.get(reverse("check-file", args=[self.logo_png.pk]))
        self.assertEqual("image/png", resp["Content-Type"])
        self.assertEqual('attachment; filename="logo.png"', resp["Content-Disposition"])
        self.assertEqual(self.logo_png_content, resp.content)

    def test_attachment_file_is_deleted_yet(self):
        with patch.object(settings, "FILE_UPLOAD_DIR", self.upload_dir):
            resp = self.client.get(reverse("check-file", args=[self.file_deleted.pk]))
        self.assert404(resp)

    @patch("tcms.core.views.prompt.render")
    def test_fail_to_read_file_content(self, render):
        # Following mock on the builtin open function will affect all calls to
        # it, so this test has to patch Prompt.render to return a response
        # manually.
        render.return_value = HttpResponse("Cannot read file")

        url = reverse("check-file", args=[self.binary_file.pk])

        # Error when opening file
        with patch.object(settings, "FILE_UPLOAD_DIR", self.upload_dir):
            with patch("builtins.open") as mock_open:
                mock_open.side_effect = IOError("io error")
                resp = self.client.get(url)
            self.assertContains(resp, "Cannot read file")

        # Error when read file content
        with patch.object(settings, "FILE_UPLOAD_DIR", self.upload_dir):
            with patch("builtins.open") as mock_open:
                fh = mock_open.return_value.__enter__.return_value
                fh.read.side_effect = IOError("io error")
                resp = self.client.get(url)
                self.assertContains(resp, "Cannot read file")

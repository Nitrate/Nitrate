# -*- coding: utf-8 -*-
import time
from http import HTTPStatus

from django import test
from django.contrib.auth.models import User
from django.urls import reverse
from django_comments.models import Comment

from tcms.comments import get_form
from tcms.comments.models import add_comment
from tests import AuthMixin, HelperAssertions
from tests import factories as f
from tests import user_should_have_perm


class TestPostComment(AuthMixin, HelperAssertions, test.TestCase):
    """Test post comments"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.case = f.TestCaseFactory()

    def _post_comment(self, comment):
        form = get_form()(self.case)
        timestamp = int(time.time())
        data = {
            "name": "",
            "email": "",
            "comment": comment,
            "content_type": "testcases.testcase",
            "object_pk": self.case.pk,
            "timestamp": timestamp,
            "security_hash": form.initial_security_hash(timestamp),
        }

        return self.client.post(reverse("comments-post"), data=data)

    def test_post_a_comment(self):
        self._post_comment("first comment")

        # Assert comment is added
        comments = Comment.objects.for_model(self.case)
        self.assertEqual(1, len(comments))
        self.assertEqual("first comment", comments[0].comment)

        # TODO: assert comments inside the response?

    def test_post_a_comment_by_authenticated_user(self):
        self.login_tester()

        self._post_comment("useful comment")

        comments = Comment.objects.for_model(self.case)
        self.assertEqual(1, len(comments))
        comment = comments[0]
        self.assertEqual("useful comment", comment.comment)
        self.assertEqual(self.tester, comment.user)
        self.assertEqual(self.tester.username, comment.name)
        self.assertEqual(self.tester.email, comment.email)

    def test_still_response_comments_even_if_fail_to_add_one(self):
        self.login_tester()
        response = self._post_comment("comment" * 2000)
        self.assert400(response)


class TestDeleteComment(AuthMixin, HelperAssertions, test.TestCase):
    """Test delete a comment"""

    auto_login = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.comment_author = f.UserFactory()

        user_should_have_perm(cls.tester, "django_comments.can_moderate")

        cls.case_1 = f.TestCaseFactory()
        cls.case_2 = f.TestCaseFactory()

        add_comment(
            cls.tester,
            "testcases.testcase",
            [cls.case_1.pk, cls.case_2.pk],
            "first comment",
        )
        add_comment(
            cls.tester,
            "testcases.testcase",
            [cls.case_1.pk, cls.case_2.pk],
            "second comment",
        )
        add_comment(
            cls.tester,
            "testcases.testcase",
            [cls.case_1.pk, cls.case_2.pk],
            "third comment",
        )
        add_comment(cls.comment_author, "testcases.testcase", [cls.case_1.pk], "4th comment")

    def setUp(self):
        super().setUp()
        self.url = reverse("comments-delete")

    def test_delete_a_comment(self):
        comment = Comment.objects.get(comment="second comment", object_pk=self.case_1.pk)

        resp = self.client.post(self.url, {"comment_id": comment.pk})

        self.assertJsonResponse(resp, {})
        self.assertTrue(
            Comment.objects.get(comment="second comment", object_pk=self.case_1.pk).is_removed
        )

    def test_delete_comments(self):
        comment_ids = [
            Comment.objects.get(comment="first comment", object_pk=self.case_1.pk).pk,
            Comment.objects.get(comment="third comment", object_pk=self.case_2.pk).pk,
        ]

        resp = self.client.post(self.url, {"comment_id": comment_ids})

        self.assertJsonResponse(resp, {})

        self.assertTrue(
            Comment.objects.get(comment="first comment", object_pk=self.case_1.pk).is_removed
        )
        self.assertTrue(
            Comment.objects.get(comment="third comment", object_pk=self.case_2.pk).is_removed
        )

    def test_ensure_not_delete_others_comment(self):
        comment_ids = [
            Comment.objects.get(comment="4th comment", object_pk=self.case_1.pk).pk,
        ]

        resp = self.client.post(self.url, {"comment_id": comment_ids})

        self.assertJsonResponse(
            resp,
            {"message": "No incoming comment id exists."},
            status_code=HTTPStatus.BAD_REQUEST,
        )

        self.assertFalse(
            Comment.objects.get(comment="4th comment", object_pk=self.case_1.pk).is_removed
        )


class TestAddComment(test.TestCase):
    """Test models.add_comment"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = User.objects.create(username="tester", email="tester@localhost")
        cls.case_1 = f.TestCaseFactory(summary="case 1")
        cls.case_2 = f.TestCaseFactory(summary="case 2")
        cls.case_3 = f.TestCaseFactory(summary="case 3")

    def test_add_a_comment(self):
        comments = add_comment(self.tester, "testcases.testcase", [self.case_1.pk], "comment 1")

        self.assertEqual("comment 1", comments[0].comment)

        self.assertTrue(
            Comment.objects.filter(object_pk=self.case_1.pk, comment="comment 1").exists()
        )

    def test_add_a_comment_to_multiple_objects(self):
        object_pks = [self.case_2.pk, self.case_3.pk]

        comments = add_comment(self.tester, "testcases.testcase", object_pks, "comment abc")

        self.assertEqual("comment abc", comments[0].comment)
        self.assertEqual("comment abc", comments[1].comment)

        for pk in object_pks:
            self.assertTrue(Comment.objects.filter(object_pk=pk, comment="comment abc").exists())

    def test_ignore_nonexisting_object_pk(self):
        object_pks = [self.case_2.pk, 99999999]

        comments = add_comment(self.tester, "testcases.testcase", object_pks, "comment abc")

        self.assertEqual(1, len(comments))
        self.assertEqual("comment abc", comments[0].comment)

    def test_fail_to_post_a_comment(self):
        # The long content will fail the process.
        comments = add_comment(
            self.tester, "testcases.testcase", [self.case_1.pk], "comment" * 2000
        )

        self.assertListEqual([], comments)

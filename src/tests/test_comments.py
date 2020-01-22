# -*- coding: utf-8 -*-
import json
import time

from django import test
from django.contrib.auth.models import User
from django.urls import reverse
from django_comments.models import Comment
from tcms.comments import get_form
from tcms.comments.models import add_comment

from tests import factories as f, user_should_have_perm


class TestPostComment(test.TestCase):
    """Test post comments"""

    @classmethod
    def setUpTestData(cls):
        cls.tester = User.objects.create_user(
            username='tester', email='tester@example.com')
        cls.tester.set_password('password')
        cls.tester.save()

        cls.case = f.TestCaseFactory()

    def setUp(self):
        self.post_comment_url = reverse('comments-post')

    def _post_comment(self, comment):
        form = get_form()(self.case)
        timestamp = int(time.time())
        data = {
            'name': '',
            'email': '',
            'comment': comment,
            'content_type': 'testcases.testcase',
            'object_pk': self.case.pk,
            'timestamp': timestamp,
            'security_hash': form.initial_security_hash(timestamp),
        }

        return self.client.post(self.post_comment_url, data=data)

    def test_post_a_comment(self):
        self._post_comment('first comment')

        # Assert comment is added
        comments = Comment.objects.for_model(self.case)
        self.assertEqual(1, len(comments))
        self.assertEqual('first comment', comments[0].comment)

        # TODO: assert comments inside the response?

    def test_post_a_comment_by_authenticated_user(self):
        self.client.login(username=self.tester.username, password='password')

        self._post_comment('useful comment')

        comments = Comment.objects.for_model(self.case)
        self.assertEqual(1, len(comments))
        comment = comments[0]
        self.assertEqual('useful comment', comment.comment)
        self.assertEqual(self.tester, comment.user)
        self.assertEqual(self.tester.username, comment.name)
        self.assertEqual(self.tester.email, comment.email)


class TestDeleteComment(test.TestCase):
    """Test delete a comment"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.tester = User.objects.create_user(
            username='tester', email='tester@example.com'
        )
        cls.tester.set_password('password')
        cls.tester.save()

        cls.comment_author = f.UserFactory()

        user_should_have_perm(cls.tester, 'django_comments.can_moderate')

        cls.case_1 = f.TestCaseFactory()
        cls.case_2 = f.TestCaseFactory()

        add_comment(cls.tester,
                    'testcases.testcase', [cls.case_1.pk, cls.case_2.pk],
                    'first comment')
        add_comment(cls.tester,
                    'testcases.testcase', [cls.case_1.pk, cls.case_2.pk],
                    'second comment')
        add_comment(cls.tester,
                    'testcases.testcase', [cls.case_1.pk, cls.case_2.pk],
                    'third comment')
        add_comment(cls.comment_author,
                    'testcases.testcase', [cls.case_1.pk], '4th comment')

    def setUp(self):
        self.url = reverse('comments-delete')
        self.client.login(username=self.tester.username, password='password')

    def test_delete_a_comment(self):
        comment = Comment.objects.get(comment='second comment',
                                      object_pk=self.case_1.pk)

        resp = self.client.post(self.url, {'comment_id': comment.pk})

        self.assertDictEqual(
            {'rc': 0, 'response': 'ok'}, json.loads(resp.content))

        comment = Comment.objects.get(comment='second comment',
                                      object_pk=self.case_1.pk)
        self.assertTrue(comment.is_removed)

    def test_delete_comments(self):
        comment_ids = [
            Comment.objects.get(
                comment='first comment', object_pk=self.case_1.pk).pk,
            Comment.objects.get(
                comment='third comment', object_pk=self.case_2.pk).pk,
        ]

        resp = self.client.post(self.url, {'comment_id': comment_ids})

        self.assertDictEqual(
            {'rc': 0, 'response': 'ok'}, json.loads(resp.content))

        self.assertTrue(
            Comment.objects.get(
                comment='first comment', object_pk=self.case_1.pk
            ).is_removed)
        self.assertTrue(
            Comment.objects.get(
                comment='third comment', object_pk=self.case_2.pk
            ).is_removed)

    def test_ensure_not_delete_others_comment(self):
        comment_ids = [
            Comment.objects.get(
                comment='4th comment', object_pk=self.case_1.pk).pk,
        ]

        resp = self.client.post(self.url, {'comment_id': comment_ids})

        self.assertDictEqual(
            {'rc': 1, 'response': 'Object does not exist.'},
            json.loads(resp.content)
        )

        self.assertFalse(
            Comment.objects.get(
                comment='4th comment', object_pk=self.case_1.pk
            ).is_removed)

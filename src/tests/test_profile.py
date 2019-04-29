# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tcms.profiles.forms import BookmarkForm


class TestOpenBookmarks(TestCase):
    """Test for opening bookmarks"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tester = User.objects.create_user(username='bookmark_tester',
                                              email='bookmark_tester@example.com',
                                              password='password')

        bookmark_form = BookmarkForm({
            'name': 'plan page',
            'url': 'http://localhost/plan/1/',
            'user': cls.tester.pk,
            'a': 'add',
        })
        bookmark_form.is_valid()
        cls.bookmark_1 = bookmark_form.save()

        bookmark_form = BookmarkForm({
            'name': 'case page',
            'url': 'http://localhost/case/1/',
            'user': cls.tester.pk,
            'a': 'add',
        })
        bookmark_form.is_valid()
        cls.bookmark_2 = bookmark_form.save()

        bookmark_form = BookmarkForm({
            'name': 'run page',
            'url': 'http://localhost/run/1/',
            'user': cls.tester.pk,
            'a': 'add',
        })
        bookmark_form.is_valid()
        cls.bookmark_3 = bookmark_form.save()

    def test_open_bookmark_page(self):
        self.client.login(username=self.tester.username, password='password')

        url = reverse('user-bookmark',
                      kwargs={'username': self.tester.username})
        response = self.client.get(url)

        for bookmark in (self.bookmark_1, self.bookmark_2, self.bookmark_3):
            self.assertContains(
                response,
                f'<input type="checkbox" id="bookmark_{bookmark.pk}" '
                f'class="js-select-bookmark" name="bookmark_id" value="{bookmark.pk}">',
                html=True)

        self.assertContains(
            response,
            '<button class="btn btn-default" type="button" id="removeSelectedBookmarks" disabled>'
            'Remove selected bookmarks</button>',
            html=True)

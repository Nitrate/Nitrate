# -*- coding: utf-8 -*-

import unittest
from textwrap import dedent
from unittest.mock import Mock

from tcms.testplans.forms import UploadedHTMLFile


class TestUploadedHTMLFile(unittest.TestCase):
    """Test UploadedHTMLFile"""

    def test_necessary_tags_are_removed(self):
        uploaded_file = Mock()
        uploaded_file.read.return_value = dedent(
            """\
            <html>
                <head>
                    <script type="text/javascript">alert('hello Nitrate')</script>
                    <style type="text/css">p {font-size: 14px}</style>
                    <link rel="icon" href="https://nitrate.com/icon.png" title="Nitrate">
                </head>
                <body>
                    <p>Importing plan</p>
                    <style type="text/css" media="screen">
                    table {border: 2px}
                    </style>
                    <script type="text/javascript">
                    console.log('testing, testing, ...')
                    </script>
                </body>
            </html>
            """
        )

        cleaner = UploadedHTMLFile(uploaded_file)
        cleaned_content = cleaner.get_content()
        self.assertEqual("<p>Importing plan</p>", cleaned_content.strip())

    def test_necessary_attributes_are_removed(self):
        uploaded_file = Mock()
        uploaded_file.read.return_value = dedent(
            """\
            <html>
                <head>
                    <script type="text/javascript">alert('hello Nitrate')</script>
                    <style type="text/css">p {font-size: 14px}</style>
                    <link rel="icon" href="https://nitrate.com/icon.png" title="Nitrate">
                </head>
                <body>
                    <div id="section" class="section">
                        <p style="font-size:large">Importing plan</p>
                    </div>
                    <style type="text/css" media="screen">
                    table {border: 2px}
                    </style>
                    <script type="text/javascript">
                    console.log('testing, testing, ...')
                    </script>
                </body>
            </html>
            """
        )
        cleaner = UploadedHTMLFile(uploaded_file)
        cleaned_content = cleaner.get_content()
        self.assertEqual(
            dedent(
                """\
                <div>
                <p>Importing plan</p>
                </div>"""
            ),
            cleaned_content.strip(),
        )

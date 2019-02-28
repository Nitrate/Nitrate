# -*- coding: utf-8 -*-

import six
import xmltodict

from django import test
from django.conf import settings

from tcms.management.models import Priority
from tcms.management.models import TestTag
from tcms.testcases.models import TestCaseStatus
from tcms.testplans.importer import clean_xml_file
from tcms.testplans.importer import process_case
from tests.factories import UserFactory

xml_single_case = '''
<testcase author="%(author)s" priority="%(priority)s"
          automated="%(automated)s" status="%(status)s">
    <summary>%(summary)s</summary>
    <categoryname>%(categoryname)s</categoryname>
    <defaulttester>%(defaulttester)s</defaulttester>
    <notes>%(notes)s</notes>
    <action>%(action)s</action>
    <expectedresults>%(expectedresults)s</expectedresults>
    <setup>%(setup)s</setup>
    <breakdown>%(breakdown)s</breakdown>
    %(tags)s
</testcase>'''


sample_case_data = {
    'author': 'user@example.com',
    'priority': 'P1',
    'automated': '0',
    'status': 'CONFIRMED',
    'summary': 'test case',
    'categoryname': '--default--',
    'defaulttester': '',
    'notes': '',
    'action': '',
    'expectedresults': '',
    'setup': '',
    'effect': '',
    'breakdown': '',
    'tag': ['tag 1'],
}


xml_file_without_error = u'''
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<!DOCTYPE testopia SYSTEM "testopia.dtd" [
  <!ENTITY testopia_lt "<">
  <!ENTITY testopia_gt ">">
]>
<testopia version="1.1">
  <testcase author="user@example.com" priority="P1"
      automated="0" status="CONFIRMED">
    <summary>测试用例</summary>
    <categoryname>--default--</categoryname>
    <defaulttester></defaulttester>
    <notes>&lt;script type=&quot;text/javascript&quot;&gt;
    alert(&quot;Exploited!&quot;);
    &lt;/script&gt;</notes>
    <action></action>
    <expectedresults></expectedresults>
    <setup></setup>
    <breakdown></breakdown>
    <tag>haha &lt;script&gt;alert(&#39;HAHAHA&#39;)&lt;/script&gt;</tag>
  </testcase>
  <testcase author="user@example.com" priority="P1"
      automated="0" status="CONFIRMED">
    <summary>case 2</summary>
    <categoryname>--default--</categoryname>
    <defaulttester></defaulttester>
    <notes></notes>
    <action></action>
    <expectedresults></expectedresults>
    <setup></setup>
    <breakdown></breakdown>
    <tag>xmlrpc</tag>
    <tag>haha</tag>
    <tag>case management system</tag>
  </testcase>
</testopia>
'''


xml_file_single_case_without_error = u'''
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<!DOCTYPE testopia SYSTEM "testopia.dtd" [
  <!ENTITY testopia_lt "<">
  <!ENTITY testopia_gt ">">
]>
<testopia version="1.1">
  <testcase author="user@example.com" priority="P1"
      automated="0" status="CONFIRMED">
    <summary>case 1</summary>
    <categoryname>--default--</categoryname>
    <defaulttester></defaulttester>
    <notes>&lt;script type=&quot;text/javascript&quot;&gt;
    alert(&quot;Exploited!&quot;);
    &lt;/script&gt;</notes>
    <action></action>
    <expectedresults></expectedresults>
    <setup></setup>
    <breakdown></breakdown>
    <tag>haha &lt;script&gt;alert(&#39;HAHAHA&#39;)&lt;/script&gt;</tag>
  </testcase>
</testopia>
'''


# With error, non-existent priority and defaulttester's email
xml_file_with_error = u'''
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<!DOCTYPE testopia SYSTEM "testopia.dtd" [
  <!ENTITY testopia_lt "<">
  <!ENTITY testopia_gt ">">
]>
<testopia version="1.1">
  <testcase author="user@example.com" priority="Pn"
      automated="0" status="CONFIRMED">
    <summary>case 2</summary>
    <categoryname>--default--</categoryname>
    <defaulttester>x-man@universe.net</defaulttester>
    <notes></notes>
    <action></action>
    <expectedresults></expectedresults>
    <setup></setup>
    <breakdown></breakdown>
    <tag>xmlrpc</tag>
    <tag>haha</tag>
    <tag>case management system</tag>
  </testcase>
</testopia>
'''


xml_file_with_wrong_version = u'''
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<!DOCTYPE testopia SYSTEM "testopia.dtd" [
  <!ENTITY testopia_lt "<">
  <!ENTITY testopia_gt ">">
]>
<testopia version="who knows"></testopia>'''


xml_file_in_malformat = u'''
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<!DOCTYPE testopia SYSTEM "testopia.dtd" [
  <!ENTITY testopia_lt "<">
  <!ENTITY testopia_gt ">">
]>
<nitrate version="1.1"></nitrate>'''


class TestProcessCase(test.TestCase):
    """Test process_case"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username='xml user', email='user@example.com')
        cls.priority_p1, created = Priority.objects.get_or_create(value='P1')
        cls.status_confirmed, created = TestCaseStatus.objects.get_or_create(name='CONFIRMED')
        cls.status_proposed, created = TestCaseStatus.objects.get_or_create(name='PROPOSED')

    def _format_xml_case_string(self, case_data):
        """Helper method to format case XML conveniently"""
        data = case_data.copy()
        data['tags'] = ''.join(
            '<tag>{}</tag>'.format(tag) for tag in data['tag'])
        data.pop('tag')
        return xml_single_case % data

    def _create_xml_dict(self, case_data):
        xml_case = self._format_xml_case_string(case_data)
        return xmltodict.parse(xml_case)

    def test_process_case(self):
        xmldict = self._create_xml_dict(sample_case_data)

        cleaned_case = process_case(xmldict['testcase'])
        self.assertEqual(self.user.id, cleaned_case['author_id'])
        self.assertEqual(self.user, cleaned_case['author'])
        self.assertEqual(sample_case_data['summary'], cleaned_case['summary'])
        self.assertEqual(None, cleaned_case['default_tester_id'])
        p1 = Priority.objects.get(value=sample_case_data['priority'])
        self.assertEqual(p1.pk, cleaned_case['priority_id'])
        self.assertEqual(False, cleaned_case['is_automated'])
        self.assertEqual(sample_case_data['categoryname'],
                         cleaned_case['category_name'])
        self.assertIsInstance(cleaned_case['tags'], list)
        for tag in sample_case_data['tag']:
            expected_tag = TestTag.objects.get(name=tag)
            self.assertEqual(expected_tag, cleaned_case['tags'][0])
        self.assertEqual(sample_case_data['action'], cleaned_case['action'])
        self.assertEqual(sample_case_data['effect'], cleaned_case['effect'])
        self.assertEqual(sample_case_data['setup'], cleaned_case['setup'])
        self.assertEqual(sample_case_data['breakdown'],
                         cleaned_case['breakdown'])
        self.assertEqual(sample_case_data['notes'], cleaned_case['notes'])

    def test_nonexistent_object(self):
        case_data = sample_case_data.copy()
        case_data['author'] = 'another_user@example.com'
        xmldict = self._create_xml_dict(case_data)
        six.assertRaisesRegex(
            self, ValueError,
            'Author email {} does not exist'.format(case_data['author']),
            process_case, xmldict['testcase'])

        case_data = sample_case_data.copy()
        case_data['defaulttester'] = 'another_user@example.com'
        xmldict = self._create_xml_dict(case_data)
        six.assertRaisesRegex(
            self, ValueError,
            'Default tester\'s email another_user@example.com does not exist',
            process_case, xmldict['testcase'])

        case_data = sample_case_data.copy()
        case_data['priority'] = 'PP'
        xmldict = self._create_xml_dict(case_data)
        six.assertRaisesRegex(self, ValueError, 'Priority PP does not exist',
                              process_case, xmldict['testcase'])

        case_data = sample_case_data.copy()
        case_data['priority'] = ''
        xmldict = self._create_xml_dict(case_data)
        self.assertRaises(ValueError, process_case, xmldict['testcase'])

        case_data = sample_case_data.copy()
        case_data['status'] = 'UNKNOWN_STATUS'
        xmldict = self._create_xml_dict(case_data)
        six.assertRaisesRegex(
            self, ValueError, 'Test case status UNKNOWN_STATUS does not exist',
            process_case, xmldict['testcase'])

        case_data = sample_case_data.copy()
        case_data['status'] = ''
        xmldict = self._create_xml_dict(case_data)
        self.assertRaises(ValueError, process_case, xmldict['testcase'])

        case_data = sample_case_data.copy()
        case_data['automated'] = ''
        xmldict = self._create_xml_dict(case_data)
        cleaned_case = process_case(xmldict['testcase'])
        self.assertEqual(False, cleaned_case['is_automated'])

        case_data = sample_case_data.copy()
        case_data['tag'] = ''
        xmldict = self._create_xml_dict(case_data)
        cleaned_case = process_case(xmldict['testcase'])
        self.assertEqual(None, cleaned_case['tags'])

        case_data = sample_case_data.copy()
        case_data['categoryname'] = ''
        xmldict = self._create_xml_dict(case_data)
        self.assertRaises(ValueError, process_case, xmldict['testcase'])

    def test_case_has_default_tester(self):
        case_data = sample_case_data.copy()
        case_data['defaulttester'] = self.user.email
        case_dict = self._create_xml_dict(case_data)
        cleaned_case = process_case(case_dict['testcase'])
        self.assertEqual(self.user.pk, cleaned_case['default_tester_id'])

    def test_invalid_author(self):
        case_data = sample_case_data.copy()
        case_data['author'] = ''
        case_dict = self._create_xml_dict(case_data)
        six.assertRaisesRegex(self, ValueError, 'Missing required author',
                              process_case, case_dict['testcase'])

    def test_invalid_priority(self):
        case_data = sample_case_data.copy()
        case_data['priority'] = ''
        case_dict = self._create_xml_dict(case_data)
        six.assertRaisesRegex(self, ValueError, 'Missing required priority',
                              process_case, case_dict['testcase'])


class TestCleanXMLFile(test.TestCase):
    """Test for testplan.clean_xml_file"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username='xml user', email='user@example.com')
        cls.priority = Priority.objects.get(value='P1')
        cls.status_confirmed = TestCaseStatus.objects.get(name='CONFIRMED')

        cls.original_xml_version = None
        if hasattr(settings, 'TESTOPIA_XML_VERSION'):
            cls.original_xml_version = settings.TESTOPIA_XML_VERSION
        settings.TESTOPIA_XML_VERSION = '1.1'

    def test_clean_xml_file(self):
        result = clean_xml_file(xml_file_without_error)
        self.assertEqual(2, len(list(result)))

        result = clean_xml_file(xml_file_single_case_without_error)
        self.assertEqual(1, len(list(result)))

        cases = clean_xml_file(xml_file_with_error)
        six.assertRaisesRegex(
            self, ValueError, 'Default tester\'s email .+ does not exist',
            list, cases)

        six.assertRaisesRegex(self, ValueError, 'Invalid XML document',
                              clean_xml_file, xml_file_in_malformat)
        six.assertRaisesRegex(self, ValueError, 'Wrong version.+',
                              clean_xml_file, xml_file_with_wrong_version)

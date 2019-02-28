# -*- coding: utf-8 -*-

import xmltodict

from django.contrib.auth.models import User
from django.conf import settings

from tcms.management.models import Priority
from tcms.management.models import TestTag
from tcms.testcases.models import TestCaseStatus


def process_case(case):
    """Convert case from XML node to Python object

    Data inside case XML node, e.g. author, default tester, will be converted
    to Python object as well.

    :param dict case: a dict representing a case XML node, which is processed
        by xmltodict library.
    :return: a mapping containing processed case and its associated object.
    :rtype: dict
    """
    # Check author
    author = case.get('@author')
    if author:
        try:
            author = User.objects.get(email=author)
            author_id = author.id
        except User.DoesNotExist:
            raise ValueError(f'Author email {author} does not exist.')
    else:
        raise ValueError('Missing required author')

    # Check default tester
    default_tester_email = case.get('defaulttester')
    if default_tester_email:
        try:
            default_tester = User.objects.get(email=default_tester_email)
            default_tester_id = default_tester.id
        except User.DoesNotExist:
            raise ValueError('Default tester\'s email {} does not exist.'.format(
                default_tester_email))
    else:
        default_tester_id = None

    # Check priority
    priority = case.get('@priority')
    if priority:
        try:
            priority = Priority.objects.get(value=priority)
            priority_id = priority.id
        except Priority.DoesNotExist:
            raise ValueError(f'Priority {priority} does not exist.')
    else:
        raise ValueError('Missing required priority')

    # Check automated status
    automated = case.get('@automated')
    if automated:
        is_automated = automated == 'Automatic' and True or False
    else:
        is_automated = False

    # Check status
    status = case.get('@status')
    if status:
        try:
            case_status = TestCaseStatus.objects.get(name=status)
            case_status_id = case_status.id
        except TestCaseStatus.DoesNotExist:
            raise ValueError(
                f'Test case status {status} does not exist.')
    else:
        raise ValueError('Missing required status')

    # Check category
    # *** Ugly code here ***
    # There is a bug in the XML file, the category is related to product.
    # But unfortunate it did not defined product in the XML file.
    # So we have to define the category_name at the moment then get the product from the plan.
    # If we did not found the category of the product we will create one.
    category_name = case.get('categoryname')
    if not category_name:
        raise ValueError('Missing required categoryname')

    # Check or create the tag
    element = 'tag'
    if case.get(element, {}):
        tags = []
        if isinstance(case[element], dict):
            tag, create = TestTag.objects.get_or_create(name=case[element]['value'])
            tags.append(tag)

        if isinstance(case[element], str):
            tag, create = TestTag.objects.get_or_create(name=case[element])
            tags.append(tag)

        if isinstance(case[element], list):
            for tag_name in case[element]:
                tag, create = TestTag.objects.get_or_create(name=tag_name)
                tags.append(tag)
    else:
        tags = None

    new_case = {
        'summary': case.get('summary') or '',
        'author_id': author_id,
        'author': author,
        'default_tester_id': default_tester_id,
        'priority_id': priority_id,
        'is_automated': is_automated,
        'case_status_id': case_status_id,
        'category_name': category_name,
        'notes': case.get('notes') or '',
        'action': case.get('action') or '',
        'effect': case.get('expectedresults') or '',
        'setup': case.get('setup') or '',
        'breakdown': case.get('breakdown') or '',
        'tags': tags,
    }

    return new_case


def clean_xml_file(xml_content):
    """Parse and extract cases from XML document"""
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode('utf-8')
    xml_content = xml_content.replace('\n', '')
    xml_content = xml_content.replace('&testopia_', '&')

    xml_data = xmltodict.parse(xml_content)
    root_element = xml_data.get('testopia', None)
    if root_element is None:
        raise ValueError('Invalid XML document.')
    if root_element.get('@version') != settings.TESTOPIA_XML_VERSION:
        raise ValueError(
            'Wrong version {}'.format(root_element.get('@version')))
    case_elements = root_element.get('testcase', None)
    if case_elements is not None:
        if isinstance(case_elements, dict):
            case_elements = [case_elements]
        return map(process_case, case_elements)
    else:
        raise ValueError('No case found in XML document.')

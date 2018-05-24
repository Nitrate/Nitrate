# -*- coding: utf-8 -*-

import six

from xml.etree import ElementTree

from tcms.core.contrib.linkreference.models import create_link
from tcms.testcases.models import TestCaseBugSystem
from tcms.testruns.helpers.serializer import escape_entities
from tcms.testruns.helpers.serializer import TCR2File
from tcms.testruns.models import TestCaseRun
from tcms.tests import BaseCaseRun


class TestTCR2FileToExportToXML(BaseCaseRun):
    """Test TCR2File to export XML"""

    @classmethod
    def setUpTestData(cls):
        super(TestTCR2FileToExportToXML, cls).setUpTestData()

        cls.log_links = {
            cls.case_run_1.pk: [
                ['todo', 'https://localhost/todo'],
                ['bugs', 'https://localhost/bugs'],
            ],
            cls.case_run_2.pk: [
                ['todo', 'https://localhost/todo'],
                ['bugs', 'https://localhost/bugs'],
                ['results', 'https://localhost/results'],
            ]
        }

        for case_run_id, links in cls.log_links.items():
            case_run = TestCaseRun.objects.get(pk=case_run_id)
            for name, url in links:
                create_link(name, url, case_run)

        # Add some bugs
        bz_sys = TestCaseBugSystem.objects.get(name='Bugzilla')
        cls.case_run_1.add_bug(bug_id='1000',
                               bug_system_id=bz_sys.pk,
                               bz_external_track=False)
        cls.case_run_1.add_bug(bug_id='2000',
                               bug_system_id=bz_sys.pk,
                               bz_external_track=False)

    def _export_to_xml(self):
        case_runs = TestCaseRun.objects.filter(
            pk__in=[self.case_run_1.pk, self.case_run_2.pk])
        exporter = TCR2File(case_runs)
        xml_buff = six.StringIO()
        exporter.write_to_xml(xml_buff)
        xml_doc = xml_buff.getvalue()
        xml_buff.close()
        return xml_doc

    def test_export_to_xml(self):
        xml_doc = self._export_to_xml()
        xml_doc = ElementTree.fromstring(xml_doc)

        self.assertEqual(2, len(list(xml_doc)))
        for elem in xml_doc:
            case_run_id = int(elem.get('case_run_id'))
            self.assertTrue(
                TestCaseRun.objects.filter(pk=case_run_id).exists())

            case_run = TestCaseRun.objects.get(pk=case_run_id)
            self.assertEqual(case_run.case.pk, int(elem.get('case_id')))
            self.assertEqual(case_run.case.category.name, elem.get('category'))
            self.assertEqual(case_run.case_run_status.name, elem.get('status'))
            self.assertEqual(escape_entities(case_run.case.summary),
                             elem.get('summary'))
            self.assertEqual(escape_entities(case_run.case.script),
                             elem.get('scripts'))
            self.assertEqual(str(case_run.case.is_automated),
                             elem.get('automated'))

    def test_export_contains_bugs(self):
        xml_doc = self._export_to_xml()
        xml_doc = ElementTree.fromstring(xml_doc)

        for case_run_elem in xml_doc:
            case_run_id = int(case_run_elem.get('case_run_id'))

            if case_run_id == self.case_run_1.pk:
                bugs_elems = case_run_elem.find('bugs').findall('bug')
                self.assertEqual(2, len(bugs_elems))
                bug_ids = [elem.get('id') for elem in bugs_elems]
                bug_ids.sort()
                self.assertEqual(['1000', '2000'], bug_ids)

            if case_run_id == self.case_run_2.pk:
                bugs_elems = case_run_elem.find('bugs').findall('bug')
                self.assertEqual(0, len(bugs_elems))

    def assert_case_run_links(
            self, case_run_id, log_links, expected_links_count):
        case_run = TestCaseRun.objects.get(pk=case_run_id)
        self.assertEqual(expected_links_count, case_run.links.count())
        for name, url in log_links:
            self.assertTrue(
                case_run.links.filter(name=name, url=url).exists())

    def test_export_contains_log_links(self):
        xml_doc = self._export_to_xml()
        xml_doc = ElementTree.fromstring(xml_doc)

        for elem in xml_doc:
            case_run_id = int(elem.get('case_run_id'))

            if case_run_id == self.case_run_1.pk:
                log_links_elems = elem.find('loglinks').findall('loglink')
                self.assertEqual(2, len(log_links_elems))
                self.assert_case_run_links(
                    case_run_id,
                    log_links=[(elem.get('name'), elem.get('url'))
                               for elem in log_links_elems],
                    expected_links_count=2)

            if case_run_id == self.case_run_2.pk:
                log_links_elems = elem.find('loglinks').findall('loglink')
                self.assertEqual(3, len(log_links_elems))
                self.assert_case_run_links(
                    case_run_id,
                    log_links=[(elem.get('name'), elem.get('url'))
                               for elem in log_links_elems],
                    expected_links_count=3)

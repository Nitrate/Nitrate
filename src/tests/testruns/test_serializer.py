# -*- coding: utf-8 -*-

import io
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from tcms.linkreference.models import create_link
from tcms.testruns.helpers.serializer import TCR2File
from tcms.testruns.models import TestCaseRun
from tests import BaseCaseRun
from tests import factories as f


def escape_entities(text):
    """Convert all XML entities

    :param text: a string containing entities possibly
    :type text: str
    :return: converted version of text
    :rtype: str
    """
    return escape(text, {'"': "&quot;"}) if text else text


class TestTCR2FileToExportToXML(BaseCaseRun):
    """Test TCR2File to export XML"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.log_links = {
            cls.case_run_1.pk: [
                ["todo", "https://localhost/todo"],
                ["issues", "https://localhost/issues"],
            ],
            cls.case_run_2.pk: [
                ["todo", "https://localhost/todo"],
                ["issues", "https://localhost/issues"],
                ["results", "https://localhost/results"],
            ],
        }

        for case_run_id, links in cls.log_links.items():
            case_run = TestCaseRun.objects.get(pk=case_run_id)
            for name, url in links:
                create_link(name, url, case_run)

        tracker = f.IssueTrackerFactory(
            service_url="http://localhost/",
            issue_report_endpoint="/enter_bug.cgi",
            validate_regex=r"^\d+$",
        )
        cls.case_run_1.add_issue("1000", tracker)
        cls.case_run_1.add_issue("2000", tracker)

    def _export_to_xml(self):
        case_runs = TestCaseRun.objects.filter(pk__in=[self.case_run_1.pk, self.case_run_2.pk])
        exporter = TCR2File(case_runs)
        xml_buff = io.StringIO()
        exporter.write_to_xml(xml_buff)
        xml_doc = xml_buff.getvalue()
        xml_buff.close()
        return xml_doc

    def test_export_to_xml(self):
        xml_doc = self._export_to_xml()
        xml_doc = ElementTree.fromstring(xml_doc)

        self.assertEqual(2, len(list(xml_doc)))
        for elem in xml_doc:
            case_run_id = int(elem.get("case_run_id"))
            self.assertTrue(TestCaseRun.objects.filter(pk=case_run_id).exists())

            case_run = TestCaseRun.objects.get(pk=case_run_id)
            self.assertEqual(case_run.case.pk, int(elem.get("case_id")))
            self.assertEqual(case_run.case.category.name, elem.get("category"))
            self.assertEqual(case_run.case_run_status.name, elem.get("status"))
            self.assertEqual(escape_entities(case_run.case.summary), elem.get("summary"))
            self.assertEqual(escape_entities(case_run.case.script), elem.get("scripts"))
            self.assertEqual(str(case_run.case.is_automated), elem.get("automated"))

    def test_export_contains_issues(self):
        xml_doc = self._export_to_xml()
        xml_doc = ElementTree.fromstring(xml_doc)

        for case_run_elem in xml_doc:
            case_run_id = int(case_run_elem.get("case_run_id"))

            if case_run_id == self.case_run_1.pk:
                issues_elems = case_run_elem.find("issues").findall("issue")
                self.assertEqual(2, len(issues_elems))
                issue_keys = sorted(elem.get("key") for elem in issues_elems)
                self.assertEqual(["1000", "2000"], issue_keys)

            if case_run_id == self.case_run_2.pk:
                issues_elems = case_run_elem.find("issues").findall("issue")
                self.assertEqual(0, len(issues_elems))

    def assert_case_run_links(self, case_run_id, log_links, expected_links_count):
        case_run = TestCaseRun.objects.get(pk=case_run_id)
        self.assertEqual(expected_links_count, case_run.links.count())
        for name, url in log_links:
            self.assertTrue(case_run.links.filter(name=name, url=url).exists())

    def test_export_contains_log_links(self):
        xml_doc = self._export_to_xml()
        xml_doc = ElementTree.fromstring(xml_doc)

        for elem in xml_doc:
            case_run_id = int(elem.get("case_run_id"))

            if case_run_id == self.case_run_1.pk:
                log_links_elems = elem.find("loglinks").findall("loglink")
                self.assertEqual(2, len(log_links_elems))
                self.assert_case_run_links(
                    case_run_id,
                    log_links=[(elem.get("name"), elem.get("url")) for elem in log_links_elems],
                    expected_links_count=2,
                )

            if case_run_id == self.case_run_2.pk:
                log_links_elems = elem.find("loglinks").findall("loglink")
                self.assertEqual(3, len(log_links_elems))
                self.assert_case_run_links(
                    case_run_id,
                    log_links=[(elem.get("name"), elem.get("url")) for elem in log_links_elems],
                    expected_links_count=3,
                )

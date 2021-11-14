# -*- coding: utf-8 -*-
"""
A serializer to import/export between model objects and file formats.
"""

import csv

from django.template import Template
from django.template.loader import get_template

# TODO: rewrite export module to export TestCaseRuns, TestPlans and other
# Nitrate objects.


class TCR2File:
    """
    Write TestCaseRun queryset into CSV or XML.
    """

    HEADERS = (
        "Case Run ID",
        "Case ID",
        "Category",
        "Status",
        "Summary",
        "script",
        "Automated",
        "Log Link",
        "Issue Keys",
    )

    def __init__(self, tcrs):
        self.headers = self.HEADERS
        self.tcrs = tcrs.select_related("case", "case__category", "case_run_status").only(
            "case__summary",
            "case__script",
            "case__is_automated",
            "case__category__name",
            "case_run_status__name",
        )
        self.rows = []

    def tcr_attrs_in_a_list(self, tcr):
        if tcr.case.script is None:
            case_script = ""
        else:
            case_script = tcr.case.script.encode()

        return (
            tcr.pk,
            tcr.case.pk,
            tcr.case.category.name.encode(),
            tcr.case_run_status.name.encode(),
            tcr.case.summary.encode(),
            case_script,
            tcr.case.is_automated,
            self.log_links(tcr),
            self.issue_keys(tcr),
        )

    def log_links(self, tcr):
        """Wrap log links into a single cell by joining log links"""
        return "\n".join(tcr.links.values_list("url", flat=True))

    def issue_keys(self, tcr):
        """Wrap issues into a single cell by joining issue keys"""
        issue_keys = tcr.issues.values_list("issue_key", flat=True)
        return " ".join(str(pk) for pk in issue_keys.iterator())

    def tcrs_in_rows(self):
        tcr_attrs_in_a_list = self.tcr_attrs_in_a_list
        for tcr in self.tcrs.iterator():
            row = tcr_attrs_in_a_list(tcr)
            yield row

    def write_to_csv(self, fileobj):
        writer = csv.writer(fileobj)
        writer.writerow(self.headers)
        writer.writerows(self.tcrs_in_rows())

    def write_to_xml(self, output):
        """Write test case runs in XML

        .. versionchanged:: 4.2
           Element ``bugs`` is renamed to ``issues``.
        """
        xml_template: Template = get_template("run/export-to.xml")
        output.write(xml_template.render({"case_runs": self.tcrs}))

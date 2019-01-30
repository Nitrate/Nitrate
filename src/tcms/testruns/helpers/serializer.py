# -*- coding: utf-8 -*-
"""
A serializer to import/export between model objects and file formats.
"""

import csv

from xml.sax.saxutils import escape


def escape_entities(text):
    """Convert all XML entities

    @param text: a string containing entities possibly
    @type text: str
    @return: converted version of text
    @rtype: str
    """
    return escape(text, {'"': '&quot;'}) if text else text


# TODO: rewrite export module to export TestCaseRuns, TestPlans and other
# Nitrate objects.


class TCR2File(object):
    """
    Write TestCaseRun queryset into CSV or XML.
    """
    ROOT = 'testcaseruns'
    HEADERS = ("Case Run ID", "Case ID",
               "Category", "Status", "Summary",
               "script", "Automated", "Log Link",
               "Issue Keys")

    def __init__(self, tcrs):
        self.root = self.ROOT
        self.headers = self.HEADERS

        qs = tcrs.select_related('case',
                                 'case__category',
                                 'case_run_status')
        self.tcrs = qs.only('case__summary',
                            'case__script',
                            'case__is_automated',
                            'case__category__name',
                            'case_run_status__name')
        self.rows = []

    def tcr_attrs_in_a_list(self, tcr):
        if tcr.case.script is None:
            case_script = ''
        else:
            case_script = tcr.case.script.encode('utf-8')

        line = (tcr.pk, tcr.case.pk,
                tcr.case.category.name.encode('utf-8'),
                tcr.case_run_status.name.encode('utf-8'),
                tcr.case.summary.encode('utf-8'),
                case_script,
                tcr.case.is_automated,
                self.log_links(tcr),
                self.issue_keys(tcr))
        return line

    def log_links(self, tcr):
        """Wrap log links into a single cell by joining log links"""
        return '\n'.join(
            (url.encode('utf-8')
             for url in tcr.links.values_list('url', flat=True))
        )

    def issue_keys(self, tcr):
        """Wrap issues into a single cell by joining issue keys"""
        issue_keys = tcr.issues.values_list('issue_key', flat=True)
        return ' '.join(str(pk) for pk in issue_keys.iterator())

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
        write_to_output = output.write
        tcr_start_elem = u'<testcaserun case_run_id="%d" case_id="%d" ' \
                         u'category="%s" status="%s" summary="%s" ' \
                         u'scripts="%s" automated="%s">'

        write_to_output(u'<%s>' % self.root)
        for tcr in self.tcrs.iterator():
            summary = escape_entities(tcr.case.summary)
            script = escape_entities(tcr.case.script)
            write_to_output(tcr_start_elem % (tcr.pk, tcr.case.pk,
                                              tcr.case.category.name or u'',
                                              tcr.case_run_status.name,
                                              summary or u'',
                                              script or u'',
                                              str(tcr.case.is_automated)))
            write_to_output(u'<loglinks>')
            for link in tcr.links.iterator():
                write_to_output(
                    u'<loglink name="%s" url="%s" />' % (link.name, link.url))
            write_to_output(u'</loglinks>')
            write_to_output(u'<issues>')
            for issue in tcr.issues.iterator():
                write_to_output(u'<issue key="%s" />' % issue.issue_key)
            write_to_output(u'</issues>')
            write_to_output(u'</testcaserun>')
        write_to_output(u'</%s>' % self.root)

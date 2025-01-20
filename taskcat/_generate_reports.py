import logging
import time
from pathlib import Path

import requests

import yattag

from ._cfn.stack import Stack
from ._cfn.threaded import Stacker

LOG = logging.getLogger(__name__)


REPO_LINK = "https://github.com/aws-ia/taskcat"
DOC_LINK = "http://taskcat.io"


class ReportBuilder:
    """This class generates the test report."""

    STYLE_SHEET_URL = "https://raw.githubusercontent.com/aws-ia/taskcat/main/assets/css/taskcat_reporting.css"

    def __init__(self, stacks: Stacker, output_file: Path, version: str):
        self._stacks = stacks
        self._output_file = output_file
        self._version = version

    def _get_output_file(self, region, stack_name, resource_type):
        """Determine the output file name to use."""

        extension = ".txt"
        if resource_type == "cfnlog":
            location = f"{stack_name}-{region}-cfnlogs{extension}"
            return str(location)
        if resource_type == "resource_log":
            location = f"{stack_name}-{region}-resources{extension}"
            return str(location)
        return None

    def _get_stack_status_badge(self, stack: Stack):
        """Generate a status and associated class from the stack status."""

        status = stack.status
        status_class = "test-red"
        status_icon = "❌"
        if status == "CREATE_COMPLETE":
            status_icon = "✅"
            status_class = "test-green"
        return f"{status_icon} {status}", status_class

    def _get_css(self):
        """Gets the latest CSS for the report from this github repo when building the report."""

        stylesheet = """th, td {
            border: 1px solid black;
        table {
            border-collapse: collapse;
        }
        td.test-green {
            background-color: #98FF98;
        }
        td.test-red {
            background-color: #FCB3BC;
        }
        """
        r = requests.get(url=self.__class__.STYLE_SHEET_URL, timeout=3)
        try:
            r.raise_for_status()
            stylesheet = r.text
        except requests.exceptions.HTTPError as e:
            LOG.error(
                f"Failed to fetch stylesheet, falling back to default stylesheet: {e}"
            )

        return stylesheet

    def _render_document(self, report_timestamp):
        """Renders the report document HTML."""

        doc, tag, text = yattag.SimpleDoc(stag_end=">").tagtext()
        stag = doc.stag
        line = doc.line

        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            with tag("head"):
                stag("meta", charset="utf-8")
                stag("meta", name="viewport", content="width=device-width")
                with tag("style"):
                    text("\n" + self._get_css())
                line("title", "TaskCat Report")
            with tag("body"):
                # Header / Banner
                with tag("table", klass="header-table-fill"):
                    with tag("tbody"):
                        with tag("tr"):
                            with tag("td"):
                                line("a", f"GitHub Repo: {REPO_LINK}", href=REPO_LINK)
                                stag("br")
                                line("a", f"Documentation: {DOC_LINK}", href=DOC_LINK)
                                stag("br")
                                text(f"Report Generated: {report_timestamp}")
                            with tag("td", klass="taskcat-logo"):
                                line("h3", "taskcat")
                with tag("table", klass="table-fill"):
                    with tag("thead"):
                        with tag("tr"):
                            line("th", "Test Name", klass="text-center", width="25%")
                            line("th", "Tested Region", klass="text-left", width="10%")
                            line("th", "Stack Name", klass="text-left", width="30%")
                            line("th", "Tested Results", klass="text-left", width="20%")
                            line("th", "Test Logs", klass="text-left", width="15%")
                    # Test Results
                    with tag("tbody"):
                        for stack in self._stacks.stacks:
                            stack: Stack  # type hint
                            LOG.info(f"Reporting on {str(stack.id)}")
                            with tag("tr"):
                                with tag("td", klass="test-info"):
                                    line("h3", stack.test_name)
                                line("td", stack.region_name, klass="text-left")
                                line("td", stack.name, klass="text-left")
                                status, status_class = self._get_stack_status_badge(
                                    stack
                                )
                                line("td", status, klass=status_class)
                                with tag("td", klass="text-left"):
                                    log_file = self._get_output_file(
                                        stack.region_name, stack.name, "cfnlog"
                                    )
                                    line("a", "View Logs", href=log_file)
                            with tag("tr", klass="test-footer"):
                                line("td", " ", colspan=5)
                    # Footer
                    with tag("tfoot"):
                        with tag("tr", klass="test-footer"):
                            line(
                                "td", f"Generated by taskcat {self._version}", colspan=5
                            )

        return doc

    def generate_report(
        self,
    ):
        """Generate the report."""

        report_timestamp = time.strftime("%A - %b,%d,%Y @ %H:%M:%S")

        # Render
        doc = self._render_document(report_timestamp)

        # Output
        html_output = yattag.indent(
            doc.getvalue(), indentation="    ", newline="\r\n", indent_text=True
        )
        with open(str(self._output_file.resolve()), "w", encoding="utf-8") as _f:
            _f.write(html_output)
        return html_output

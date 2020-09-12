import logging
import time
from pathlib import Path

import requests

import yattag

from ._cfn.stack import Stack
from ._cfn.threaded import Stacker

LOG = logging.getLogger(__name__)


class ReportBuilder:
    """
    This class generates the test report.

    """

    def __init__(self, stacks: Stacker, output_file: Path, version: str = "0.9.0"):
        self._stacks = stacks
        self._output_file = output_file
        self._version = version

    # TODO: refactor for readability
    def generate_report(  # noqa: C901
        self,
    ):  # pylint: disable=too-many-locals, too-many-statements
        doc = yattag.Doc()

        # Type of cfn log return cfn log file
        def get_output_file(region, stack_name, resource_type):
            extension = ".txt"
            if resource_type == "cfnlog":
                location = "{}-{}-{}{}".format(stack_name, region, "cfnlogs", extension)
                return str(location)
            if resource_type == "resource_log":
                location = "{}-{}-{}{}".format(
                    stack_name, region, "resources", extension
                )
                return str(location)
            return None

        def get_teststate(stack: Stack):
            rstatus = stack.status
            if rstatus == "CREATE_COMPLETE":
                status_css = "class=test-green"
            elif rstatus == "CREATE_FAILED":
                status_css = "class=test-red"
            else:
                status_css = "class=test-red"
            return rstatus, status_css

        tag = doc.tag
        text = doc.text
        logo = "taskcat"
        repo_link = "https://github.com/aws-quickstart/taskcat"
        css_url = (
            "https://raw.githubusercontent.com/aws-quickstart/taskcat/main/"
            "assets/css/taskcat_reporting.css"
        )
        output_css = requests.get(css_url).text
        doc_link = "http://taskcat.io"

        with tag("html"):
            with tag("head"):
                doc.stag("meta", charset="utf-8")
                doc.stag("meta", name="viewport", content="width=device-width")
                with tag("style", type="text/css"):
                    text(output_css)
                with tag("title"):
                    text("TaskCat Report")

            with tag("body"):
                tested_on = time.strftime("%A - %b,%d,%Y @ %H:%M:%S")

                with tag("table", "class=header-table-fill"):
                    with tag("tbody"):
                        with tag("th", "colspan=2"):
                            with tag("tr"):
                                with tag("td"):
                                    with tag("a", href=repo_link):
                                        text("GitHub Repo: ")
                                        text(repo_link)
                                        doc.stag("br")
                                    with tag("a", href=doc_link):
                                        text("Documentation: ")
                                        text(doc_link)
                                        doc.stag("br")
                                    text("Tested on: ")
                                    text(tested_on)
                                with tag("td", "class=taskcat-logo"):
                                    with tag("h3"):
                                        text(logo)
            doc.stag("p")
            with tag("table", "class=table-fill"):
                with tag("tbody"):
                    with tag("thread"):
                        with tag("tr"):
                            with tag("th", "class=text-center", "width=25%"):
                                text("Test Name")
                            with tag("th", "class=text-left", "width=10%"):
                                text("Tested Region")
                            with tag("th", "class=text-left", "width=30%"):
                                text("Stack Name")
                            with tag("th", "class=text-left", "width=20%"):
                                text("Tested Results")
                            with tag("th", "class=text-left", "width=15%"):
                                text("Test Logs")

                            for stack in self._stacks.stacks:
                                with tag("tr", "class= test-footer"):
                                    with tag("td", "colspan=5"):
                                        text("")

                                testname = stack.test_name
                                LOG.info(f"Reporting on {str(stack.id)}")
                                status, css = get_teststate(stack)

                                with tag("tr"):
                                    with tag("td", "class=test-info"):
                                        with tag("h3"):
                                            text(testname)
                                    with tag("td", "class=text-left"):
                                        text(stack.region_name)
                                    with tag("td", "class=text-left"):
                                        text(stack.name)
                                    with tag("td", css):
                                        text(str(status))
                                    with tag("td", "class=text-left"):
                                        clog = get_output_file(
                                            stack.region_name, stack.name, "cfnlog"
                                        )
                                        with tag("a", href=clog):
                                            text("View Logs ")
                            with tag("tr", "class= test-footer"):
                                with tag("td", "colspan=5"):
                                    vtag = "Generated by {} {}".format(
                                        "taskcat", self._version
                                    )
                                    text(vtag)

                        doc.stag("p")

            html_output = yattag.indent(
                doc.getvalue(), indentation="    ", newline="\r\n", indent_text=True
            )

            file = open(str(self._output_file.resolve()), "w")
            file.write(html_output)
            file.close()

            return html_output

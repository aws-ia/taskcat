import time
import yattag

from botocore.vendored import requests
from taskcat.colored_console import PrintMsg
from taskcat.common_utils import CommonTools
from taskcat.exceptions import TaskCatException


class ReportBuilder:
    """
    This class generates the test report.

    """

    def __init__(self, test_data, dashboard_filename, version, boto_client, taskcat):
        self.dashboard_filename = dashboard_filename
        self.test_data = test_data
        self.version = version
        self._boto_client = boto_client
        self.taskcat = taskcat

    def generate_report(self):
        doc = yattag.Doc()

        # Type of cfn log return cfn log file
        def get_output_file(region, stack_name, resource_type):
            extension = '.txt'
            if resource_type == 'cfnlog':
                location = "{}-{}-{}{}".format(stack_name, region, 'cfnlogs', extension)
                return str(location)
            elif resource_type == 'resource_log':
                location = "{}-{}-{}{}".format(stack_name, region, 'resources', extension)
                return str(location)

        def get_teststate(stackname, region):
            rstatus = None
            status_css = None
            try:

                cfn_client = self._boto_client.get('cloudformation', region)
                test_query = cfn_client.describe_stacks(StackName=stackname)

                for result in test_query['Stacks']:
                    rstatus = result.get('StackStatus')
                    if rstatus == 'CREATE_COMPLETE':
                        status_css = 'class=test-green'
                    elif rstatus == 'CREATE_FAILED':
                        status_css = 'class=test-red'
                        self.taskcat.one_or_more_tests_failed = True
                        if self.taskcat.retain_if_failed and (self.taskcat.run_cleanup == True):
                            self.taskcat.run_cleanup = False
                    else:
                        status_css = 'class=test-red'
            except TaskCatException:
                raise
            except Exception as e:
                print(PrintMsg.ERROR + "Error describing stack named [%s] " % stackname)
                print(PrintMsg.DEBUG + str(e))
                rstatus = 'MANUALLY_DELETED'
                status_css = 'class=test-orange'

            return rstatus, status_css

        tag = doc.tag
        text = doc.text
        logo = 'taskcat'
        repo_link = 'https://github.com/aws-quickstart/taskcat'
        css_url = 'https://raw.githubusercontent.com/aws-quickstart/taskcat/master/assets/css/taskcat_reporting.css'
        output_css = requests.get(css_url).text
        doc_link = 'http://taskcat.io'

        with tag('html'):
            with tag('head'):
                doc.stag('meta', charset='utf-8')
                doc.stag(
                    'meta', name="viewport", content="width=device-width")
                with tag('style', type='text/css'):
                    text(output_css)
                with tag('title'):
                    text('TaskCat Report')

            with tag('body'):
                tested_on = time.strftime('%A - %b,%d,%Y @ %H:%M:%S')

                with tag('table', 'class=header-table-fill'):
                    with tag('tbody'):
                        with tag('th', 'colspan=2'):
                            with tag('tr'):
                                with tag('td'):
                                    with tag('a', href=repo_link):
                                        text('GitHub Repo: ')
                                        text(repo_link)
                                        doc.stag('br')
                                    with tag('a', href=doc_link):
                                        text('Documentation: ')
                                        text(doc_link)
                                        doc.stag('br')
                                    text('Tested on: ')
                                    text(tested_on)
                                with tag('td', 'class=taskcat-logo'):
                                    with tag('h3'):
                                        text(logo)
            doc.stag('p')
            with tag('table', 'class=table-fill'):
                with tag('tbody'):
                    with tag('thread'):
                        with tag('tr'):
                            with tag('th',
                                     'class=text-center',
                                     'width=25%'):
                                text('Test Name')
                            with tag('th',
                                     'class=text-left',
                                     'width=10%'):
                                text('Tested Region')
                            with tag('th',
                                     'class=text-left',
                                     'width=30%'):
                                text('Stack Name')
                            with tag('th',
                                     'class=text-left',
                                     'width=20%'):
                                text('Tested Results')
                            with tag('th',
                                     'class=text-left',
                                     'width=15%'):
                                text('Test Logs')

                            for test in self.test_data:
                                with tag('tr', 'class= test-footer'):
                                    with tag('td', 'colspan=5'):
                                        text('')

                                testname = test.get_test_name()
                                print(PrintMsg.INFO + "(Generating Reports)")
                                print(PrintMsg.INFO + " - Processing {}".format(testname))
                                for stack in test.get_test_stacks():
                                    print("Reporting on {}".format(str(stack['StackId'])))
                                    stack_id = CommonTools(stack['StackId']).parse_stack_info()
                                    status, css = get_teststate(
                                        stack_id['stack_name'],
                                        stack_id['region'])

                                    with tag('tr'):
                                        with tag('td',
                                                 'class=test-info'):
                                            with tag('h3'):
                                                text(testname)
                                        with tag('td',
                                                 'class=text-left'):
                                            text(stack_id['region'])
                                        with tag('td',
                                                 'class=text-left'):
                                            text(stack_id['stack_name'])
                                        with tag('td', css):
                                            text(str(status))
                                        with tag('td',
                                                 'class=text-left'):
                                            clog = get_output_file(
                                                stack_id['region'],
                                                stack_id['stack_name'],
                                                'cfnlog')
                                            # rlog = get_output_file(
                                            #    state['region'],
                                            #    state['stack_name'],
                                            #    'resource_log')
                                            #
                                            with tag('a', href=clog):
                                                text('View Logs ')
                                                # with tag('a', href=rlog):
                                                #    text('Resource Logs ')
                            with tag('tr', 'class= test-footer'):
                                with tag('td', 'colspan=5'):
                                    vtag = 'Generated by {} {}'.format('taskcat', self.version)
                                    text(vtag)

                        doc.stag('p')
                        print('\n')

            html_output = yattag.indent(doc.getvalue(),
                                        indentation='    ',
                                        newline='\r\n',
                                        indent_text=True)

            file = open(self.dashboard_filename, 'w')
            file.write(html_output)
            file.close()

            return html_output

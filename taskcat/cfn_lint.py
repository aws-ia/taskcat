import textwrap
import cfnlint.core
from yaml.scanner import ScannerError
from taskcat.colored_console import PrintMsg
import yaml
import re


class Lint(object):

    _code_regex = re.compile("^([WER][0-9]*:)")

    def __init__(self, config, path=""):
        """
        Lints templates using cfn_python_lint. Uses config file to define regions and templates to test. Recurses into
        child templates, excluding submodules.

        :param config: path to tascat ci config file
        """
        self._config = yaml.safe_load(open(config))
        self._rules = cfnlint.core.get_rules([], [], [])
        self._path = path
        self.lints = self._lint()

    def _get_template_path(self, test):
        if self._path:
            return '%s/templates/%s' % (self._path, self._config['tests'][test]['template_file'])
        else:
            return 'templates/%s' % (self._config['tests'][test]['template_file'])

    def _get_test_regions(self, test):
        if 'regions' in self._config['tests'][test].keys():
            return self._filter_unsupported_regions(self._config['tests'][test]['regions'])
        else:
            return self._filter_unsupported_regions(self._config['global']['regions'])

    def _filter_unsupported_regions(self, regions):
        lint_regions = set(cfnlint.core.REGIONS)
        if set(regions).issubset(lint_regions):
            return regions
        supported = set(regions).intersection(lint_regions)
        unsupported = set(regions).difference(lint_regions)
        print(PrintMsg.ERROR + "The following regions are not supported by cfn-python-lint and will not be linted %s" % unsupported)
        return list(supported)

    @staticmethod
    def _parse_template(template_path, quiet=False):
        try:
            return cfnlint.decode.cfn_yaml.load(template_path)
        except ScannerError as e:
            if not quiet:
                print(PrintMsg.ERROR + 'Linter failed to load template %s "%s" line %s, column %s' % (
                      template_path, e.problem, e.problem_mark.line, e.problem_mark.column))
        except FileNotFoundError as e:
            if not quiet:
                print(PrintMsg.ERROR + 'Linter failed to load template %s "%s"' % (template_path, str(e)))

    def _lint(self):
        lints = {}
        templates = {}

        for test in self._config['tests'].keys():
            lints[test] = {}
            lints[test]['regions'] = self._get_test_regions(test)
            template_file = self._get_template_path(test)
            lints[test]['template_file'] = template_file
            if template_file not in templates.keys():
                templates[template_file] = self._get_child_templates(template_file, set(), parent_path=self._path)
            lints[test]['results'] = {}
            templates[template_file].add(template_file)
            lint_errors = set()
            for t in templates[template_file]:
                template = self._parse_template(t, quiet=True)
                if template:
                    try:
                        lints[test]['results'][t] = cfnlint.core.run_checks(
                            t, template, self._rules, lints[test]['regions']
                        )
                    except cfnlint.core.CfnLintExitException as e:
                        lint_errors.add(PrintMsg.ERROR + str(e))
            for e in lint_errors:
                print(e)
        return lints

    def output_results(self):
        """
        Prints lint results to terminal using taskcat console formatting

        :return:
        """
        for test in self.lints.keys():
            for t in self.lints[test]['results'].keys():
                if len(self.lints[test]['results'][t]) == 0:
                    print(PrintMsg.INFO + "Lint passed for test %s on template %s:" % (test, t))
                else:
                    print(PrintMsg.ERROR + "Lint detected issues for test %s on template %s:" % (test, t))
                for r in self.lints[test]['results'][t]:
                    print(self._format_message(r, test, t))

    def _format_message(self, message, test, t):
        message = message.__str__().lstrip('[')
        sev = message[0]
        code = Lint._code_regex.findall(message)[0][:-1]
        path = message.split(" ")[-1]
        line_no = ""
        if len(path.split(":")) == 2:
            line_no = path.split(":")[1]
        prefix = "    line " + line_no + " [" + code + "] ["
        indent = "\n" + " " * (2 + len(prefix))
        message = indent.join(textwrap.wrap(" ".join(message.split(" ")[1:-2]), 141-(len(indent) + 11)))
        message = prefix + message
        if sev == 'E':
            return PrintMsg.ERROR + message
        elif sev == 'W':
            if 'E' + message[1:] not in [r.__str__().lstrip('[') for r in self.lints[test]['results'][t]]:
                return PrintMsg.INFO + message
        else:
            return PrintMsg.DEBUG + "linter produced unkown output: " + message

    def _get_child_templates(self, filename, children, parent_path=''):
        template = self._parse_template(filename)
        if not template:
            return children
        for resource in template['Resources'].keys():
            child_name = ''
            if template['Resources'][resource]['Type'] == "AWS::CloudFormation::Stack":
                template_url = template['Resources'][resource]['Properties']['TemplateURL']
                if isinstance(template_url, dict):
                    if 'Fn::Sub' in template_url.keys():
                        if isinstance(template_url['Fn::Sub'], str):
                            child_name = template_url['Fn::Sub'].split('}')[-1]
                        else:
                            child_name = template_url['Fn::Sub'][0].split('}')[-1]
                    elif 'Fn::Join' in list(template_url.keys())[0]:
                        child_name = template_url['Fn::Join'][1][-1]
                elif isinstance(template_url, str):
                    if 'submodules/' not in template_url:
                        child_name = '/'.join(template_url.split('/')[-2:])
            if child_name and not child_name.startswith('submodules/'):
                if parent_path:
                    child_name = "%s/%s" % (parent_path, child_name)
                children.add(child_name)
                children.union(self._get_child_templates(child_name, children, parent_path=parent_path))
        return children

import logging
import re
import textwrap

import cfnlint.core
from taskcat.config import Config

LOG = logging.getLogger(__name__)


class Lint:

    _code_regex = re.compile("^([WER][0-9]*:)")

    def __init__(self, config: Config, strict: bool = False):
        """
        Lints templates using cfn_python_lint. Uses config to define regions and
        templates to test. Recurses into child templates, excluding submodules.

        :param config: path to tascat ci config file
        """
        self._config: Config = config
        self._rules = cfnlint.core.get_rules([], [], [])
        self.lints = self._lint()
        self.strict: bool = strict

    @staticmethod
    def _filter_unsupported_regions(regions):
        lint_regions = set(cfnlint.core.REGIONS)
        if set(regions).issubset(lint_regions):
            return regions
        supported = set(regions).intersection(lint_regions)
        unsupported = set(regions).difference(lint_regions)
        LOG.error(
            "The following regions are not supported by cfn-python-lint and will "
            "not be linted %s",
            unsupported,
        )
        return list(supported)

    def _lint(self):
        lints = dict()
        lint_errors = set()

        for name, test in self._config.tests.items():
            lints[name] = {"regions": self._filter_unsupported_regions(test.regions)}
            lints[name]["template_file"] = test.template.template_path
            lints[name]["results"] = dict()

            templates = [t for t in test.template.descendents]
            templates.append(test.template)
            templates = set(templates)
            for template in templates:
                tpath = str(template.template_path)
                results = []
                try:
                    results = cfnlint.core.run_checks(
                        tpath, template.template, self._rules, lints[name]["regions"]
                    )
                    lints[name]["results"][tpath] = results
                except cfnlint.core.CfnLintExitException as e:
                    lint_errors.add(str(e))
                lints[name]["results"][tpath] = results
            for e in lint_errors:
                LOG.error(e)
        return lints, lint_errors

    def output_results(self):
        """
        Prints lint results to terminal using taskcat console formatting

        :return:
        """
        lints = self.lints[0]
        for test in lints:
            for result in lints[test]["results"]:
                if not lints[test]["results"][result]:
                    LOG.info(f"Lint passed for test {test} on template {result}")
                else:
                    msg = f"Lint detected issues for test {test} on template {result}:"
                    if self._is_error(lints[test]["results"][result]):
                        LOG.error(msg)
                    else:
                        LOG.warning(msg)
                for inner_result in lints[test]["results"][result]:
                    self._format_message(inner_result, test, result)

    @property
    def passed(self):
        for test in self.lints[0]:
            for template in self.lints[0][test]["results"]:
                results = self.lints[0][test]["results"][template]
                if not results:
                    if self._is_error(results) or self.strict:
                        return False
        return True

    @staticmethod
    def _is_error(messages):
        for message in messages:
            sev = message.__str__().lstrip("[")[0]
            if sev == "E":
                return True
        return False

    def _format_message(self, message, test, result):
        sev = message.rule.id[0]
        code = message.rule.id[1:]
        prefix = f"    line {message.linenumber} [{code}] [{message.rule.shortdesc}] "
        indent = "\n" + " " * (2 + len(prefix))
        message = indent.join(textwrap.wrap(message.message, 141 - (len(indent) + 11)))
        message = prefix + message
        if sev == "E":
            LOG.error(message)
        elif sev == "W":
            if "E" + code not in [
                r.__str__().lstrip("[") for r in self.lints[0][test]["results"][result]
            ]:
                LOG.warning(message)
        else:
            LOG.error("linter produced unkown output: " + message)

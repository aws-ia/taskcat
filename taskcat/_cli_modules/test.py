# flake8: noqa B950,F841
import logging
from pathlib import Path

from taskcat._cfn.threaded import Stacker
from taskcat._cfn_lint import Lint as TaskCatLint
from taskcat._client_factory import Boto3Cache
from taskcat._config import Config
from taskcat._lambda_build import LambdaBuild
from taskcat._s3_stage import stage_in_s3
from taskcat._tui import TerminalPrinter
from taskcat._validate import validate_all_templates
from taskcat.exceptions import TaskCatException

LOG = logging.getLogger(__name__)


class Test:
    """
    Performs functional tests on CloudFormation templates.
    """

    # pylint: disable=too-many-locals
    @staticmethod
    def run(input_file="./.taskcat.yml", project_root="./"):
        """tests whether CloudFormation templates are able to successfully launch

        :param input_file: path to either a taskat project config file or a
        CloudFormation template
        :param project_root: root path of the project relative to input_file
        """
        project_root = Path(project_root).expanduser().resolve()
        input_file = project_root / input_file
        config = Config.create(
            project_root=project_root,
            # TODO: detect if input file is taskcat config or CloudFormation template
            project_config_path=input_file,
        )
        boto3_cache = Boto3Cache()
        # 1. build lambdas
        LambdaBuild(config, project_root)
        # 2. lint
        templates = config.get_templates(project_root, boto3_cache)
        lint = TaskCatLint(config, templates, project_root)
        errors = lint.lints[1]
        lint.output_results()
        if errors or not lint.passed:
            raise TaskCatException("Lint failed with errors")
        # 3. s3 sync
        buckets = config.get_buckets(boto3_cache)
        stage_in_s3(buckets, config.config.project.name, project_root)
        # 4. validate
        validate_all_templates(config, templates, buckets)
        # 5. launch stacks
        regions = config.get_regions(boto3_cache)
        parameters = config.get_rendered_parameters(buckets, regions, templates)
        tests = config.get_tests(project_root, templates, regions, buckets, parameters)
        test_definition = Stacker(config.config.project.name, tests)
        test_definition.create_stacks()
        terminal_printer = TerminalPrinter()
        # 6. wait for completion
        terminal_printer.report_test_progress(stacker=test_definition)
        # 7. delete stacks
        test_definition.delete_stacks()
        terminal_printer.report_test_progress(stacker=test_definition)
        # TODO: summarise stack statusses (did they complete/delete ok) and print any
        #  error events
        # 8. delete buckets
        for test in buckets.values():
            for bucket in test.values():
                bucket.delete(delete_objects=True)
        # 8. create report

        # 9. raise if something failed

    def resume(self, run_id):  # pylint: disable=no-self-use
        """resumes a monitoring of a previously started test run"""
        # do some stuff
        raise NotImplementedError()

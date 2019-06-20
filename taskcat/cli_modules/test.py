from taskcat.config import Config


class Test:
    """
    Performs functional tests on CloudFormation templates.
    """

    # pylint: disable=no-self-use, line-too-long, unused-variable
    def run(self, input_file, project_root="./"):
        """tests whether CloudFormation templates are able to successfully launch

        :param input_file: path to either a taskat project config file or a CloudFormation template
        :param project_root: root path of the project relative to input_file
        """
        config = Config(
            input_file, project_root=project_root
        )  # pylint: disable=unused-variable
        # 1. build lambdas
        # 2. lint
        # 3. s3 sync
        # 4. validate
        # 5. launch stacks
        # 6. wait for completion
        # 7. delete stacks
        # 8. create report

    def resume(self, run_id):  # pylint: disable=no-self-use
        """resumes a monitoring of a previously started test run"""
        # do some stuff
        raise NotImplementedError()

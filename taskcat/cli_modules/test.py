from taskcat.config import Config


class Test:
    """
    Performs functional tests on CloudFormation templates.
    """

    def run(self, entry_point, project_root='./'):  # pylint: disable=no-self-use
        config = Config(entry_point, project_root=project_root)  # pylint: disable=unused-variable
        # 1. build lambdas
        # 2. lint
        # 3. s3 sync
        # 4. validate
        # 5. launch stacks
        # 6. wait for completion
        # 7. delete stacks
        # 8. create report

    def resume(self, run_id):  # pylint: disable=no-self-use
        # do some stuff
        raise NotImplementedError()

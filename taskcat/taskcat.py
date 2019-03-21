from taskcat import LegacyTaskCat


class TaskCat(object):

    def __init__(self, args):
        self._legacy = LegacyTaskCat(args)
        self.set_config = self._legacy.set_config
        self.aws_api_init = self._legacy.aws_api_init
        self.validate_yaml = self._legacy.validate_yaml
        self.get_config = self._legacy.get_config
        self.lambda_build_only = self._legacy.lambda_build_only
        self.set_project_name = self._legacy.set_project_name
        self.set_project_path = self._legacy.set_project_path
        self.stage_in_s3 = self._legacy.stage_in_s3
        self.validate_template = self._legacy.validate_template
        self.validate_parameters = self._legacy.validate_parameters
        self.stackcreate = self._legacy.stackcreate
        self.get_stackstatus = self._legacy.get_stackstatus
        self.createreport = self._legacy.createreport
        self.cleanup = self._legacy.cleanup
        self.one_or_more_tests_failed = self._legacy.one_or_more_tests_failed

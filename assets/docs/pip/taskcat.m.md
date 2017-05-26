Module taskcat
--------------

Classes
-------
TaskCat 
    Ancestors (in MRO)
    ------------------
    taskcat.TaskCat
    builtins.object

    Static methods
    --------------
    __init__(self, nametag='[taskcat]')
        Initialize self.  See help(type(self)) for accurate signature.

    aws_api_init(self, args)
        This function reads the AWS credentials from various sources to ensure
        that the client has right credentials defined to successfully run
        TaskCat against an AWS account.

        :param args: Command line arguments for AWS credentials. It could be
            either profile name, access key and secret key or none.

    cleanup(self, testdata_list, speed)
        This function deletes the CloudFormation stacks of the given tests.

        :param testdata_list: List of TestData objects
        :param speed: Interval (in seconds) in which the status has to be checked
            while deleting the stacks.

    collect_resources(self, testdata_list, logpath)
        This function collects the AWS resources information created by the
        CloudFormation stack for generating the report.

        :param testdata_list: List of TestData object
        :param logpath: Log file path

    createcfnlogs(self, testdata_list, logpath)
        This function creates the CloudFormation log files.

        :param testdata_list: List of TestData objects
        :param logpath: Log file path
        :return:

    createreport(self, testdata_list, filename)
        This function creates the test report.

        :param testdata_list: List of TestData objects
        :param filename: Report file name
        :return:

    deep_cleanup(self, testdata_list)
        This function deletes the AWS resources which were not deleted
        by deleting CloudFormation stacks.

        :param testdata_list: List of TestData objects

    define_tests(self, yamlc, test)
        This function reads the given test config yaml object and defines
        the tests as per the given config object.

        :param yamlc: TaskCat config yaml object
        :param test: Test scenarios

    genpassword(self, pass_length, pass_type)
        Returns a password of given length and type.

        :param pass_length: Length of the desired password
        :param pass_type: Type of the desired password - String only OR Alphanumeric
            * A = AlphaNumeric, Example 'vGceIP8EHC'
        :return: Password of given length and type

    genreport(self, testdata_list, dashboard_filename)
        This function generates the test report.

        :param testdata_list: List of TestData objects
        :param dashboard_filename: Report file name

    get_all_resources(self, stackids, region)
        Given a list of stackids, function returns the list of dictionary items, where each
        item consist of stackId and the resources associated with that stack.

        :param stackids: List of Stack Ids
        :param region: AWS region
        :return: A list of dictionary object in the following format
                [
                    {
                        'stackId': 'string',
                        'resources': [
                            {
                               'logicalId': 'string',
                               'physicalId': 'string',
                               'resourceType': 'String'
                            },
                        ]
                    },
                ]

    get_available_azs(region, count)
        Returns a list of availability zones in a given region.

        :param region: Region for the availability zones
        :param count: Minimum number of availability zones needed

        :return: List of availability zones in a given region

    get_capabilities(self)

    get_cfnlogs(stackname, region)
        This function returns the event logs of the given stack in a specific format.
        :param stackname: Name of the stack
        :param region: Region stack belongs to
        :return: Event logs of the stack

    get_config(self)

    get_default_region(self)

    get_docleanup(self)

    get_global_region(self, yamlcfg)
        Returns a list of regions defined under global region in the yml config file.

        :param yamlcfg: Content of the yml config file
        :return: List of regions

    get_parameter_file(self)

    get_parameter_path(self)

    get_password(self)

    get_project(self)

    get_resources(self, stackname, region, include_stacks=False)
        Given a stackname, and region function returns the list of dictionary items, where each item
        consist of logicalId, physicalId and resourceType of the aws resource associated
        with the stack.

        :param include_stacks: 
        :param stackname: CloudFormation stack name
        :param region: AWS region
        :return: List of objects in the following format
             [
                 {
                     'logicalId': 'string',
                     'physicalId': 'string',
                     'resourceType': 'String'
                 },
             ]

    get_resources_helper(self, stackname, region, l_resources, include_stacks)
        This is a helper function of get_resources function. Check get_resources function for details.

    get_s3_url(self, key)
        Returns S3 url of a given object.

        :param key: Name of the object whose S3 url is being returned
        :return: S3 url of the given key

    get_s3bucket(self)

    get_s3contents(url)

    get_stackstatus(self, testdata_list, speed)
        Given a list of TestData objects, this function checks the stack status
        of each CloudFormation stack and updates the corresponding TestData object
        with the status.

        :param testdata_list: List of TestData object
        :param speed: Interval (in seconds) in which the status has to be checked in loop

    get_template_file(self)

    get_template_path(self)

    get_test_region(self)

    if_stackexists(self, stackname, region)
        This function checks if a stack exist with the given stack name.
        Returns "yes" if exist, otherwise "no".

        :param stackname: Stack name
        :param region: AWS region

        :return: "yes" if stack exist, otherwise "no"

    parse_stack_info(self, stack_name)
        Returns a dictionary object containing the region and stack name.

        :param stack_name: Full stack name arn
        :return: Dictionary object containing the region and stack name

    regxfind(re_object, data_line)
        Returns the matching string.

        :param re_object: Regex object
        :param data_line: String to be searched

        :return: Matching String if found, otherwise return 'Not-found'

    set_capabilities(self, ability)

    set_config(self, config_yml)

    set_default_region(self, region)

    set_docleanup(self, cleanup_value)

    set_parameter_file(self, parameter)

    set_parameter_path(self, parameter)

    set_password(self, password)

    set_project(self, project)

    set_s3bucket(self, bucket)

    set_template_file(self, template)

    set_template_path(self, template)

    set_test_region(self, region_list)

    stackcheck(self, stack_id)
        Given the stack id, this function returns the status of the stack as
        a list with stack name, region, and status as list items, in the respective
        order.

        :param stack_id: CloudFormation stack id

        :return: List containing the stack name, region and stack status in the
            respective order.

    stackcreate(self, taskcat_cfg, test_list, sprefix)
        This function creates CloudFormation stack for the given tests.

        :param taskcat_cfg: TaskCat config as yaml object
        :param test_list: List of tests
        :param sprefix: Special prefix as string. Purpose of this param is to use it for tagging
            the stack.

        :return: List of TestData objects

    stackdelete(self, testdata_list)
        This function deletes the CloudFormation stacks of the given tests.

        :param testdata_list: List of TestData objects

    stage_in_s3(self, taskcat_cfg)
        Upload templates and other artifacts to s3.

        This function creates the s3 bucket with name provided in the config yml file. If
        no bucket name provided, it creates the s3 bucket using project name provided in
        config yml file. And uploads the templates and other artifacts to the s3 bucket.

        :param taskcat_cfg: Taskcat configuration provided in yml file

    validate_json(self, jsonin)
        This function validates the given JSON.

        :param jsonin: Json object to be validated

        :return: TRUE if given Json is valid, FALSE otherwise.

    validate_parameters(self, taskcat_cfg, test_list)
        This function validates the parameters file of the CloudFormation template.

        :param taskcat_cfg: TaskCat config yaml object
        :param test_list: List of tests

        :return: TRUE if the parameters file is valid, else FALSE

    validate_template(self, taskcat_cfg, test_list)
        Returns TRUE if all the template files are valid, otherwise FALSE.

        :param taskcat_cfg: TaskCat config object
        :param test_list: List of tests

        :return: TRUE if templates are valid, else FALSE

    validate_yaml(self, yaml_file)
        This function validates the given yaml file.

        :param yaml_file: Yaml file name

    welcome(self, prog_name='taskcat.io')

    write_logs(self, stack_id, logpath)
        This function writes the event logs of the given stack and all the child stacks to a given file.
        :param stack_id: Stack Id
        :param logpath: Log file path
        :return:

    Instance variables
    ------------------
    banner

    capabilities

    config

    defult_region

    interface

    nametag

    parameter_path

    project

    run_cleanup

    s3bucket

    template_path

    test_region

    verbose

## Usage

### CLI
The cli is self documenting by using `--help`. The most common use of taskcat is for
executing function tests of CloudFormation templates. The command for this is:

```bash
taskcat test run
```

add `--help to see the supported flags and arguments`

### Python
Taskcat can be imported into Python and used in the testing framework of your choice.
``` python
from taskcat.testing import CFNTest
test = CFNTest.from_file(project_root='./template_dir')
with test as stacks:
    # Calling 'with' or 'test.run()' will deploy the stacks.
    for stack in stacks:
        print(f"Testing {stack.name}")
        bucket_name = ""
        for output in stack.outputs:
            if output.key == "LogsBucketName":
                bucket_name = output.value
                break
        assert "logs" in bucket_name
        assert stack.region.name in bucket_name
        print(f"Created bucket: {bucket_name}")
```

The example used here is very simple, you would most likely leverage other python modules like boto3 to do more advanced testing. The `CFNTest` object can be passed the same arguments as `taskcat test run`. See the [docs](https://aws-ia.github.io/taskcat/apidocs/taskcat/testing/index.html) for more details.

### Config files
taskcat has several configuration files which can be used to set behaviors in a flexible way.

#### Global config
`~/.taskcat.yml` provides global settings that become defaults for all projects. Please see our [schema reference](docs/schema/taskcat_schema.html) for specific configuration options that are available.

#### Project config
`<PROJECT_ROOT>/.taskcat.yml` provides project specific configuration. Please see our [schema reference](docs/schema/taskcat_schema.html) for specific configuration options that are available.


#### Precedence
With the exception of the `parameters` section, more specific config with the same key
takes precedence.

> The rationale behind having parameters function this way is so that values can be
overridden at a system level outside of a project, that is likely committed to source
control. parameters that define account specific things like VPC details, Key Pairs, or
secrets like API keys can be defined per host outside of source control.

For example, consider this global config:

`~/.taskcat.yml`
```yaml
general:
  s3_bucket: my-globally-defined-bucket
  parameters:
    KeyPair: my-global-ec2-keypair
```

Given a simple project config:

```yaml
project:
  name: my-project
  regions:
  - us-east-2
tests:
  default:
    template: ./template.yaml
```

The effective test configuration would become:

```yaml
tests:
  default:
    template: ./template.yaml
    s3_bucket: my-globally-defined-bucket
    parameters:
      KeyPair: my-global-ec2-keypair
```

If any item is re-defined in a project it takes precedence over the global value.
Anything defined in a test takes precedence over what is defined in the project or
global configuration. with the **exception** of the `parameters` section which works in
reverse. For example, using the same global config as above, given this project config:

```yaml
project:
  name: my-project
  regions:
  - us-east-2
  s3_bucket: my-project-s3-bucket
tests:
  default:
    template: ./template.yaml
    parameters:
      KeyPair: my-test-ec2-keypair
```

Would result in this effective test configuration:

```yaml
tests:
  default:
    template: ./template.yaml
    s3_bucket: my-project-s3-bucket
    parameters:
      KeyPair: my-global-ec2-keypair
```

Notice that `s3_bucket` took the most specific value and `KeyPair` the most general.

### CLI interface

taskcat adopts a similar cli command structure to `git` with a
`taskcat command subcommand --flag` style. The cli is also designed to be simplest if
run from the root of a project. Let's have a look at equivalent command to run a test:


cd into the project root and type __test__ __run__:

```bash
cd ./quickstart-aws-vpc
taskcat test run
```

or run it from anywhere by providing the path to the project root
```bash
taskcat test run -p ./quickstart-aws-vpc
```


### Configuration files
The configuration files required for taskcat have changed, to ease migration, if taskcat
is run and legacy config files are found, they are converted and written to new file
locations. For more information on the new format, see the [config file docs](#config-files).

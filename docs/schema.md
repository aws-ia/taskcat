# Schema Reference

The taskcat configuration schema defines the structure and validation rules for `.taskcat.yml` files. This reference provides a comprehensive overview of all available configuration options.

## Overview

The taskcat configuration file uses YAML format and supports three main sections:

- **`general`** - Global configuration settings
- **`project`** - Project-specific configuration  
- **`tests`** - Individual test definitions

## Configuration Structure

```yaml
# Basic structure
general:
  # Global settings applied to all tests
  
project:
  # Project-specific settings
  
tests:
  test-name:
    # Individual test configuration
```

## General Section

Global configuration settings that apply to all tests unless overridden.

### Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `artifact_regions` | `array[string]` | AWS regions where artifacts are copied | `["us-east-1", "us-west-2"]` |
| `auth` | `object` | AWS authentication profiles by region | `{"default": "my-profile"}` |
| `parameters` | `object` | Global CloudFormation parameters | `{"InstanceType": "t3.micro"}` |
| `regions` | `array[string]` | Default AWS regions for testing | `["us-east-1", "us-west-2"]` |
| `s3_bucket` | `string` | S3 bucket for artifacts (auto-generated if omitted) | `"my-taskcat-bucket"` |
| `s3_regional_buckets` | `boolean` | Enable regional auto-buckets | `true` |
| `tags` | `object` | CloudFormation stack tags | `{"Environment": "test"}` |
| `prehooks` | `array[object]` | Hooks executed before tests | See [Hooks](#hooks) |
| `posthooks` | `array[object]` | Hooks executed after tests | See [Hooks](#hooks) |

### Example

```yaml
general:
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
  parameters:
    Environment: test
    Owner: taskcat-team
  tags:
    Project: taskcat
    CostCenter: "1001"
  s3_regional_buckets: true
```

## Project Section

Project-specific configuration that applies to all tests within the project.

### Properties

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `name` | `string` | Project name (lowercase, hyphens only) | - |
| `owner` | `string` | Project owner email | - |
| `regions` | `array[string]` | Project default regions | - |
| `s3_bucket` | `string` | Project S3 bucket name | Auto-generated |
| `s3_object_acl` | `string` | S3 object ACL | `"private"` |
| `template` | `string` | Default template path | - |
| `parameters` | `object` | Project default parameters | `{}` |
| `auth` | `object` | Project authentication settings | - |
| `lambda_source_path` | `string` | Lambda source directory | `"lambda_functions/source"` |
| `lambda_zip_path` | `string` | Lambda zip output directory | `"lambda_functions/packages"` |
| `package_lambda` | `boolean` | Enable Lambda packaging | `true` |
| `build_submodules` | `boolean` | Build Lambda zips for submodules | `true` |
| `shorten_stack_name` | `boolean` | Use shortened stack names | `false` |
| `role_name` | `string` | IAM role for CloudFormation | - |
| `org_id` | `string` | AWS Organization ID | - |
| `az_blacklist` | `array[string]` | Excluded Availability Zone IDs | `[]` |

### Example

```yaml
project:
  name: my-cloudformation-project
  owner: developer@example.com
  regions:
    - us-east-1
    - us-west-2
  parameters:
    ProjectName: my-project
    Environment: production
  lambda_source_path: functions/source
  lambda_zip_path: functions/packages
  package_lambda: true
  shorten_stack_name: true
```

## Tests Section

Individual test configurations. Each test can override project and global settings.

### Properties

| Property | Type | Description | Required |
|----------|------|-------------|----------|
| `template` | `string` | CloudFormation template path | ✅ |
| `parameters` | `object` | Test-specific parameters | - |
| `regions` | `array[string]` | Test-specific regions | - |
| `auth` | `object` | Test-specific authentication | - |
| `artifact_regions` | `array[string]` | Test-specific artifact regions | - |
| `az_blacklist` | `array[string]` | Test-specific AZ exclusions | - |

### Example

```yaml
tests:
  basic-test:
    template: templates/basic.yaml
    parameters:
      InstanceType: t3.micro
      KeyName: my-key-pair
    regions:
      - us-east-1
      - us-west-2
      
  advanced-test:
    template: templates/advanced.yaml
    parameters:
      InstanceType: m5.large
      DatabasePassword: $[taskcat_genpass_16S]
      S3Bucket: $[taskcat_autobucket]
    regions:
      - us-east-1
      - us-west-2
      - eu-west-1
    auth:
      us-east-1: production-profile
      eu-west-1: europe-profile
```

## Parameter Types

CloudFormation parameters support multiple data types:

### String Parameters
```yaml
parameters:
  InstanceType: t3.micro
  KeyName: my-key-pair
```

### Numeric Parameters
```yaml
parameters:
  Port: 8080
  MaxSize: 10
```

### Boolean Parameters
```yaml
parameters:
  EnableLogging: true
  CreateDatabase: false
```

### Array Parameters
```yaml
parameters:
  SecurityGroups:
    - sg-12345678
    - sg-87654321
  AvailabilityZones:
    - us-east-1a
    - us-east-1b
```

## Hooks

Hooks allow you to execute custom scripts before (`prehooks`) or after (`posthooks`) test execution.

### Hook Structure

```yaml
prehooks:
  - type: script
    config:
      command: ./scripts/setup.sh
      
posthooks:
  - type: script
    config:
      command: ./scripts/cleanup.sh
```

### Hook Types

| Type | Description | Configuration |
|------|-------------|---------------|
| `script` | Execute shell script | `command`: Script path or command |

## AWS Regions

Valid AWS region formats follow the pattern: `^(ap|eu|us|sa|ca|cn|af|me|us-gov)-(central|south|north|east|west|southeast|southwest|northeast|northwest)-[0-9]$`

### Examples
- `us-east-1` - US East (N. Virginia)
- `us-west-2` - US West (Oregon)
- `eu-west-1` - Europe (Ireland)
- `ap-southeast-1` - Asia Pacific (Singapore)

## Availability Zone IDs

When using `az_blacklist`, specify Availability Zone IDs (not names):

### Examples
- `use1-az1` - US East 1 AZ 1
- `usw2-az2` - US West 2 AZ 2
- `euw1-az3` - EU West 1 AZ 3

## S3 Object ACLs

Valid S3 object ACL values:

- `private` (default)
- `public-read`
- `public-read-write`
- `authenticated-read`
- `aws-exec-read`
- `bucket-owner-read`
- `bucket-owner-full-control`

## Complete Example

```yaml
# Complete taskcat configuration example
general:
  regions:
    - us-east-1
    - us-west-2
  parameters:
    Environment: test
  tags:
    Project: taskcat-example
    Owner: development-team

project:
  name: example-project
  owner: developer@example.com
  s3_regional_buckets: true
  package_lambda: true
  lambda_source_path: functions/source
  lambda_zip_path: functions/packages

tests:
  vpc-test:
    template: templates/vpc.yaml
    parameters:
      VpcCidr: 10.0.0.0/16
      AvailabilityZones: $[taskcat_genaz_2]
    regions:
      - us-east-1
      - us-west-2
      
  application-test:
    template: templates/application.yaml
    parameters:
      InstanceType: t3.medium
      DatabasePassword: $[taskcat_genpass_20S]
      S3Bucket: $[taskcat_autobucket]
      KeyName: $[taskcat_getkeypair]
    regions:
      - us-east-1
    auth:
      us-east-1: production-profile
```

## Validation

The schema includes built-in validation for:

- **Required fields** - Ensures essential properties are present
- **Data types** - Validates correct data types for each property
- **Format validation** - Checks AWS region formats, naming patterns
- **Enum validation** - Validates against allowed values (e.g., S3 ACLs)
- **Pattern matching** - Ensures strings match required patterns

## Best Practices

1. **Use descriptive test names** - Make test purposes clear
2. **Leverage inheritance** - Define common settings in `general` or `project`
3. **Use Dynamic Values** - Employ `$[taskcat_*]` functions for flexibility
4. **Regional considerations** - Test in multiple regions for global deployments
5. **Parameter validation** - Ensure all required parameters are provided
6. **Resource cleanup** - Use appropriate hooks for setup and teardown

## See Also

- [Dynamic Values Reference](dynamic-values.md) - Complete guide to `$[taskcat_*]` functions
- [Configuration Guide](configuration.md) - Detailed configuration examples
- [Parameter Overrides](parameter-overrides.md) - Advanced parameter techniques

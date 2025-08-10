# Configuration

Learn how to configure taskcat for your specific testing needs with comprehensive configuration options.

## Configuration File Structure

taskcat uses YAML configuration files (`.taskcat.yml`) with this structure:

```yaml
general:
  # Global settings applied to all tests
  
project:
  # Project-specific settings
  
tests:
  # Individual test definitions
```

## Basic Configuration

### Minimal Configuration

```yaml
project:
  name: my-project
  regions:
    - us-east-1

tests:
  basic:
    template: template.yaml
```

### Standard Configuration

```yaml
project:
  name: my-cloudformation-project
  regions:
    - us-east-1
    - us-west-2
  parameters:
    Environment: test
    Owner: development-team

tests:
  vpc-test:
    template: templates/vpc.yaml
    parameters:
      VpcCidr: 10.0.0.0/16
      
  app-test:
    template: templates/app.yaml
    parameters:
      InstanceType: t3.micro
      DatabasePassword: $[taskcat_genpass_16S]
```

## Global Settings

Configure settings that apply to all tests:

```yaml
general:
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
  parameters:
    Environment: production
    ProjectName: my-project
  tags:
    CostCenter: "1001"
    Department: Engineering
  s3_regional_buckets: true
```

### Global Properties

| Property | Description | Example |
|----------|-------------|---------|
| `regions` | Default regions for all tests | `["us-east-1", "us-west-2"]` |
| `parameters` | Global CloudFormation parameters | `{"Environment": "prod"}` |
| `tags` | CloudFormation stack tags | `{"Project": "taskcat"}` |
| `s3_bucket` | Custom S3 bucket name | `"my-taskcat-bucket"` |
| `s3_regional_buckets` | Enable regional buckets | `true` |
| `auth` | AWS authentication profiles | `{"default": "my-profile"}` |

## Project Settings

Configure project-specific options:

```yaml
project:
  name: enterprise-application
  owner: platform-team@company.com
  regions:
    - us-east-1
    - us-west-2
  parameters:
    ProjectName: enterprise-app
    Environment: production
  lambda_source_path: functions/source
  lambda_zip_path: functions/packages
  package_lambda: true
  shorten_stack_name: true
  s3_object_acl: bucket-owner-read
```

### Project Properties

| Property | Description | Default |
|----------|-------------|---------|
| `name` | Project identifier | Required |
| `owner` | Project owner email | - |
| `template` | Default template path | - |
| `lambda_source_path` | Lambda source directory | `lambda_functions/source` |
| `lambda_zip_path` | Lambda package directory | `lambda_functions/packages` |
| `package_lambda` | Enable Lambda packaging | `true` |
| `build_submodules` | Build submodule Lambdas | `true` |
| `shorten_stack_name` | Use short stack names | `false` |
| `role_name` | CloudFormation service role | - |

## Test Configuration

Define individual tests with specific settings:

```yaml
tests:
  # Basic test
  simple-test:
    template: templates/simple.yaml
    
  # Test with parameters
  parameterized-test:
    template: templates/app.yaml
    parameters:
      InstanceType: t3.medium
      DatabasePassword: $[taskcat_genpass_20S]
      
  # Test with specific regions
  regional-test:
    template: templates/global.yaml
    regions:
      - us-east-1
      - eu-west-1
      - ap-southeast-1
      
  # Test with authentication
  authenticated-test:
    template: templates/secure.yaml
    auth:
      us-east-1: production-profile
      eu-west-1: europe-profile
```

### Test Properties

| Property | Description | Required |
|----------|-------------|----------|
| `template` | CloudFormation template path | ✅ |
| `parameters` | Test-specific parameters | - |
| `regions` | Test-specific regions | - |
| `auth` | Authentication overrides | - |
| `artifact_regions` | Artifact copy regions | - |

## Advanced Configuration

### Multi-Environment Setup

```yaml
project:
  name: multi-env-app
  
tests:
  development:
    template: templates/app.yaml
    parameters:
      Environment: dev
      InstanceType: t3.micro
      DatabaseInstanceClass: db.t3.micro
    regions:
      - us-east-1
      
  staging:
    template: templates/app.yaml
    parameters:
      Environment: staging
      InstanceType: t3.small
      DatabaseInstanceClass: db.t3.small
    regions:
      - us-east-1
      - us-west-2
      
  production:
    template: templates/app.yaml
    parameters:
      Environment: prod
      InstanceType: m5.large
      DatabaseInstanceClass: db.r5.large
    regions:
      - us-east-1
      - us-west-2
      - eu-west-1
```

### Cross-Account Testing

```yaml
project:
  name: cross-account-app
  
tests:
  development-account:
    template: templates/app.yaml
    auth:
      default: dev-account-profile
    parameters:
      Environment: dev
      
  production-account:
    template: templates/app.yaml
    auth:
      default: prod-account-profile
    parameters:
      Environment: prod
```

### Lambda Function Testing

```yaml
project:
  name: serverless-app
  lambda_source_path: src/functions
  lambda_zip_path: dist/functions
  package_lambda: true
  build_submodules: true
  
tests:
  lambda-test:
    template: templates/serverless.yaml
    parameters:
      Runtime: python3.9
      MemorySize: 256
      Timeout: 30
```

## Authentication Configuration

Configure AWS authentication for different regions or accounts:

### Profile-Based Authentication

```yaml
general:
  auth:
    default: my-default-profile
    us-gov-east-1: govcloud-profile
    cn-north-1: china-profile

project:
  auth:
    us-east-1: production-profile
    eu-west-1: europe-profile
```

### Test-Specific Authentication

```yaml
tests:
  secure-test:
    template: templates/secure.yaml
    auth:
      us-east-1: security-profile
      us-west-2: security-profile
```

## Parameter Configuration

### Static Parameters

```yaml
tests:
  static-test:
    template: templates/app.yaml
    parameters:
      InstanceType: t3.medium
      Environment: production
      EnableLogging: true
      Port: 8080
```

### Dynamic Parameters

```yaml
tests:
  dynamic-test:
    template: templates/app.yaml
    parameters:
      # Generate unique values
      S3Bucket: $[taskcat_autobucket]
      DatabasePassword: $[taskcat_genpass_16S]
      UniqueId: $[taskcat_genuuid]
      
      # Environment-aware values
      CurrentRegion: $[taskcat_current_region]
      ProjectName: $[taskcat_project_name]
      TestName: $[taskcat_test_name]
      
      # AWS resource values
      AvailabilityZones: $[taskcat_genaz_2]
      KeyPair: $[taskcat_getkeypair]
      
      # External values
      DatabaseHost: $[taskcat_ssm_/app/database/host]
      ApiKey: $[taskcat_secretsmanager_prod/api/key]
```

## S3 Configuration

### Bucket Management

```yaml
project:
  # Use custom bucket
  s3_bucket: my-custom-taskcat-bucket
  
  # Enable regional buckets
  s3_regional_buckets: true
  
  # Set object ACL
  s3_object_acl: bucket-owner-read
  
  # Enable legacy signature version
  s3_enable_sig_v2: false
```

### Artifact Regions

```yaml
general:
  artifact_regions:
    - us-east-1
    - us-west-2
    - eu-west-1

tests:
  global-test:
    template: templates/global.yaml
    artifact_regions:
      - us-east-1
      - ap-southeast-1
```

## Hooks Configuration

Execute custom scripts before or after tests:

```yaml
general:
  prehooks:
    - type: script
      config:
        command: ./scripts/setup.sh
        
  posthooks:
    - type: script
      config:
        command: ./scripts/cleanup.sh

tests:
  custom-test:
    template: templates/app.yaml
    prehooks:
      - type: script
        config:
          command: ./scripts/test-setup.sh
```

## Validation and Linting

Validate your configuration:

```bash
# Lint configuration
taskcat lint

# Lint specific file
taskcat lint --config-file custom.yml

# Validate templates
taskcat lint --templates
```

## Best Practices

### 1. Use Hierarchical Configuration

```yaml
# Global defaults
general:
  regions:
    - us-east-1
    - us-west-2
  parameters:
    Environment: test

# Project overrides
project:
  parameters:
    ProjectName: my-app

# Test-specific settings
tests:
  production:
    parameters:
      Environment: prod  # Overrides global
```

### 2. Leverage Dynamic Values

```yaml
tests:
  flexible-test:
    template: templates/app.yaml
    parameters:
      # Avoid hardcoded values
      S3Bucket: $[taskcat_autobucket]
      DatabasePassword: $[taskcat_genpass_20S]
      
      # Use context-aware values
      StackName: $[taskcat_project_name]-$[taskcat_test_name]
      Region: $[taskcat_current_region]
```

### 3. Organize Templates

```yaml
project:
  name: organized-project
  
tests:
  infrastructure:
    template: infrastructure/vpc.yaml
    
  database:
    template: database/rds.yaml
    
  application:
    template: application/app.yaml
```

### 4. Use Meaningful Names

```yaml
tests:
  # Good: Descriptive names
  vpc-with-public-subnets:
    template: templates/vpc-public.yaml
    
  rds-mysql-multi-az:
    template: templates/rds-mysql.yaml
    
  # Avoid: Generic names
  test1:
    template: template1.yaml
```

## Configuration Examples

See the [Examples](examples.md) page for complete, real-world configuration examples.

## Next Steps

- [Dynamic Values](dynamic-values.md) - Master runtime parameters
- [Parameter Overrides](parameter-overrides.md) - Advanced parameter techniques
- [Schema Reference](schema.md) - Complete configuration reference

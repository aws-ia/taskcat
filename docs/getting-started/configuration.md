# Configuration Guide

Learn how to configure taskcat for your specific testing needs with comprehensive configuration options.

## Configuration File Structure

taskcat uses YAML configuration files (`.taskcat.yml`) with this structure:

```yaml
project:
  name: string                    # Project name
  regions: [list]                 # AWS regions to test
  s3_bucket: string              # Optional: Custom S3 bucket
  s3_key_prefix: string          # Optional: S3 key prefix
  
tests:
  test-name:                     # Test identifier
    template: string             # Path to CloudFormation template
    parameters: {}               # Parameter overrides
    regions: [list]              # Optional: Test-specific regions
    
global:
  parameters: {}                 # Global parameter overrides
```

## Project Configuration

### Basic Project Settings

```yaml
project:
  name: my-cloudformation-project
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
```

### Advanced Project Settings

```yaml
project:
  name: enterprise-infrastructure
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
    - ap-southeast-1
  s3_bucket: my-custom-taskcat-bucket
  s3_key_prefix: testing/templates/
  tags:
    Environment: Testing
    Project: taskcat
    Owner: DevOps-Team
```

## Test Configuration

### Single Test

```yaml
tests:
  basic-test:
    template: templates/main.yaml
    parameters:
      InstanceType: t3.micro
      Environment: test
```

### Multiple Tests

```yaml
tests:
  small-deployment:
    template: templates/small.yaml
    parameters:
      InstanceType: t3.micro
      
  large-deployment:
    template: templates/large.yaml
    parameters:
      InstanceType: m5.xlarge
      
  multi-az-test:
    template: templates/multi-az.yaml
    regions:
      - us-east-1
      - us-west-2
    parameters:
      AvailabilityZones: $[taskcat_genaz_3]
```

## Parameter Management

### Global Parameters

Parameters that apply to all tests:

```yaml
global:
  parameters:
    KeyPairName: my-keypair
    VpcCidr: 10.0.0.0/16
    Environment: testing

tests:
  test1:
    template: templates/app.yaml
    # Inherits global parameters
  test2:
    template: templates/db.yaml
    # Also inherits global parameters
```

### Test-Specific Parameters

Override global parameters for specific tests:

```yaml
global:
  parameters:
    Environment: testing
    InstanceType: t3.micro

tests:
  production-test:
    template: templates/app.yaml
    parameters:
      Environment: production    # Overrides global
      InstanceType: m5.large    # Overrides global
```

### Pseudo-Parameters

Use dynamic parameters for flexible testing:

```yaml
tests:
  dynamic-test:
    template: templates/app.yaml
    parameters:
      # Generate random values
      DatabasePassword: $[taskcat_genpass_16S]
      S3Bucket: $[taskcat_autobucket]
      
      # Use current context
      Region: $[taskcat_current_region]
      ProjectName: $[taskcat_project_name]
      
      # Generate availability zones
      AvailabilityZones: $[taskcat_genaz_2]
      
      # Reference other parameters
      PasswordConfirm: $[taskcat_getval_DatabasePassword]
```

## Region Configuration

### Project-Level Regions

All tests use these regions by default:

```yaml
project:
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
```

### Test-Specific Regions

Override regions for specific tests:

```yaml
project:
  regions:
    - us-east-1
    - us-west-2

tests:
  global-test:
    template: templates/global.yaml
    regions:
      - us-east-1
      - us-west-2
      - eu-west-1
      - ap-southeast-1
      
  us-only-test:
    template: templates/us-specific.yaml
    regions:
      - us-east-1
      - us-west-2
```

## Advanced Configuration

### Custom S3 Configuration

```yaml
project:
  name: my-project
  s3_bucket: my-custom-bucket-${AWS::Region}
  s3_key_prefix: taskcat-tests/
  s3_object_acl: private
```

### Authentication Configuration

```yaml
project:
  auth:
    us-east-1: profile1
    us-west-2: profile2
    default: default-profile
```

### Template Processing

```yaml
project:
  template:
    transforms:
      - AWS::Serverless-2016-10-31
    capabilities:
      - CAPABILITY_IAM
      - CAPABILITY_NAMED_IAM
```

## Configuration Examples

### Microservices Architecture

```yaml
project:
  name: microservices-platform
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1

global:
  parameters:
    Environment: testing
    VpcCidr: 10.0.0.0/16

tests:
  vpc-infrastructure:
    template: templates/vpc.yaml
    
  application-tier:
    template: templates/app-tier.yaml
    parameters:
      InstanceType: t3.medium
      
  database-tier:
    template: templates/db-tier.yaml
    parameters:
      DBInstanceClass: db.t3.micro
      
  monitoring:
    template: templates/monitoring.yaml
    regions:
      - us-east-1  # Only deploy monitoring in primary region
```

### Multi-Environment Testing

```yaml
project:
  name: multi-env-app
  regions:
    - us-east-1
    - us-west-2

tests:
  development:
    template: templates/app.yaml
    parameters:
      Environment: dev
      InstanceType: t3.micro
      
  staging:
    template: templates/app.yaml
    parameters:
      Environment: staging
      InstanceType: t3.small
      
  production:
    template: templates/app.yaml
    parameters:
      Environment: prod
      InstanceType: m5.large
```

## Best Practices

### 1. Use Meaningful Names
```yaml
tests:
  vpc-with-public-subnets:     # ✅ Descriptive
    template: templates/vpc.yaml
    
  test1:                       # ❌ Not descriptive
    template: templates/vpc.yaml
```

### 2. Organize Parameters
```yaml
global:
  parameters:
    # Common across all tests
    Environment: testing
    Owner: devops-team
    
tests:
  web-tier:
    parameters:
      # Specific to this test
      InstanceType: t3.medium
      MinSize: 2
      MaxSize: 10
```

### 3. Use Pseudo-Parameters
```yaml
parameters:
  # ✅ Dynamic and flexible
  DatabasePassword: $[taskcat_genpass_16S]
  S3Bucket: $[taskcat_autobucket]
  
  # ❌ Static and potentially conflicting
  DatabasePassword: hardcoded-password
  S3Bucket: my-static-bucket-name
```

## Validation

Validate your configuration:

```bash
# Check configuration syntax
taskcat test run --dry-run

# Lint CloudFormation templates
taskcat lint

# Generate configuration schema
taskcat schema
```

## Next Steps

- [Pseudo-Parameters Guide](../usage/PSUEDO_PARAMETERS.md)
- [Parameter Overrides](../usage/PARAMETER_OVERRIDES.md)
- [Advanced Examples](../examples/advanced.md)

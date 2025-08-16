# Parameter Overrides

Learn how to override CloudFormation parameters at different levels for flexible and reusable test configurations.

## Overview

Parameter overrides allow you to:

- **Reuse templates** across different environments
- **Customize deployments** without modifying templates
- **Manage configurations** hierarchically
- **Test variations** of the same template

## Override Hierarchy

Parameters are resolved in this order (highest to lowest priority):

1. **Test-level parameters** - Specific to individual tests
2. **Project-level parameters** - Applied to all project tests
3. **Global parameters** - Applied to all tests
4. **Template defaults** - Default values in CloudFormation template

```yaml
general:
  parameters:
    Environment: test        # Lowest priority

project:
  parameters:
    Environment: staging     # Overrides global

tests:
  production:
    parameters:
      Environment: prod      # Highest priority
```

## Basic Parameter Overrides

### Template with Parameters

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Parameters:
  InstanceType:
    Type: String
    Default: t3.micro
  Environment:
    Type: String
    Default: dev
  DatabasePassword:
    Type: String
    NoEcho: true
```

### Configuration with Overrides

```yaml
# .taskcat.yml
project:
  name: parameter-override-example
  parameters:
    Environment: staging    # Override template default

tests:
  development:
    template: template.yaml
    parameters:
      InstanceType: t3.micro
      Environment: dev      # Override project setting
      
  production:
    template: template.yaml
    parameters:
      InstanceType: m5.large
      Environment: prod     # Override project setting
      DatabasePassword: $[taskcat_genpass_20S]
```

## Global Parameter Overrides

Set parameters that apply to all tests:

```yaml
general:
  parameters:
    # Common parameters for all tests
    ProjectName: my-application
    Owner: platform-team
    CostCenter: "1001"
    
  tags:
    # Common tags for all stacks
    Project: my-application
    ManagedBy: taskcat
```

## Project Parameter Overrides

Set parameters that apply to all tests in a project:

```yaml
project:
  name: web-application
  parameters:
    # Project-wide parameters
    ApplicationName: web-app
    Environment: staging
    VpcCidr: 10.0.0.0/16
    
tests:
  vpc-test:
    template: templates/vpc.yaml
    # Inherits all project parameters
    
  app-test:
    template: templates/app.yaml
    parameters:
      Environment: production  # Overrides project Environment
```

## Test-Specific Overrides

Override parameters for individual tests:

```yaml
tests:
  small-deployment:
    template: templates/app.yaml
    parameters:
      InstanceType: t3.micro
      MinSize: 1
      MaxSize: 2
      
  large-deployment:
    template: templates/app.yaml
    parameters:
      InstanceType: m5.xlarge
      MinSize: 3
      MaxSize: 10
      
  secure-deployment:
    template: templates/app.yaml
    parameters:
      InstanceType: m5.large
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
      EnableEncryption: true
```

## Environment-Based Overrides

Create environment-specific configurations:

```yaml
project:
  name: multi-environment-app
  
tests:
  development:
    template: templates/app.yaml
    parameters:
      Environment: dev
      InstanceType: t3.micro
      DatabaseInstanceClass: db.t3.micro
      BackupRetentionPeriod: 1
      MultiAZ: false
      
  staging:
    template: templates/app.yaml
    parameters:
      Environment: staging
      InstanceType: t3.medium
      DatabaseInstanceClass: db.t3.small
      BackupRetentionPeriod: 7
      MultiAZ: false
      
  production:
    template: templates/app.yaml
    parameters:
      Environment: prod
      InstanceType: m5.large
      DatabaseInstanceClass: db.r5.large
      BackupRetentionPeriod: 30
      MultiAZ: true
      EnableEncryption: true
      EnableMonitoring: true
```

## Region-Specific Overrides

Different parameters for different regions:

```yaml
tests:
  multi-region-app:
    template: templates/app.yaml
    regions:
      - us-east-1
      - us-west-2
      - eu-west-1
    parameters:
      # Base parameters for all regions
      InstanceType: m5.large
      Environment: prod
      
  us-east-1-specific:
    template: templates/app.yaml
    regions:
      - us-east-1
    parameters:
      # US East specific configuration
      InstanceType: m5.xlarge
      EnableCloudFront: true
      PrimaryRegion: true
      
  europe-specific:
    template: templates/app.yaml
    regions:
      - eu-west-1
    parameters:
      # Europe specific configuration
      InstanceType: m5.large
      DataResidency: EU
      ComplianceMode: GDPR
```

## Dynamic Parameter Overrides

Combine static and dynamic parameters:

```yaml
project:
  parameters:
    # Static project parameters
    ProjectName: my-app
    Owner: development-team
    
tests:
  dynamic-test:
    template: templates/app.yaml
    parameters:
      # Static overrides
      Environment: production
      InstanceType: m5.large
      
      # Dynamic values
      S3Bucket: $[taskcat_autobucket]
      DatabasePassword: $[taskcat_genpass_20S]
      UniqueId: $[taskcat_genuuid]
      CurrentRegion: $[taskcat_current_region]
      
      # Context-aware values
      StackName: $[taskcat_project_name]-$[taskcat_test_name]
      LogGroup: /aws/lambda/$[taskcat_project_name]
```

## Complex Parameter Scenarios

### Conditional Parameters

```yaml
tests:
  conditional-test:
    template: templates/conditional.yaml
    parameters:
      CreateDatabase: true
      DatabaseInstanceClass: db.t3.micro
      DatabasePassword: $[taskcat_genpass_16S]
      
  no-database-test:
    template: templates/conditional.yaml
    parameters:
      CreateDatabase: false
      # Database parameters not needed
```

### Nested Stack Parameters

```yaml
tests:
  nested-stack-test:
    template: templates/parent.yaml
    parameters:
      # Parent stack parameters
      Environment: production
      
      # Child stack parameters (passed through)
      VpcTemplateUrl: https://s3.amazonaws.com/templates/vpc.yaml
      VpcInstanceType: t3.medium
      
      AppTemplateUrl: https://s3.amazonaws.com/templates/app.yaml
      AppInstanceType: m5.large
      AppDatabasePassword: $[taskcat_genpass_20S]
```

### Cross-Stack References

```yaml
tests:
  vpc-stack:
    template: templates/vpc.yaml
    parameters:
      VpcCidr: 10.0.0.0/16
      Environment: production
      
  app-stack:
    template: templates/app.yaml
    parameters:
      # Reference outputs from vpc-stack
      VpcId: $[taskcat_getval_VpcId]
      PrivateSubnets: $[taskcat_getval_PrivateSubnets]
      Environment: production
      InstanceType: m5.large
```

## Parameter File Integration

Use external parameter files:

### Parameter File

```json
// parameters/production.json
[
  {
    "ParameterKey": "InstanceType",
    "ParameterValue": "m5.large"
  },
  {
    "ParameterKey": "Environment",
    "ParameterValue": "production"
  },
  {
    "ParameterKey": "DatabaseInstanceClass",
    "ParameterValue": "db.r5.large"
  }
]
```

### Configuration Reference

```yaml
tests:
  production-from-file:
    template: templates/app.yaml
    parameter_input: parameters/production.json
    parameters:
      # Additional parameters or overrides
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
```

## Validation and Testing

### Parameter Validation

```bash
# Validate parameters before testing
taskcat lint

# Test with specific parameters
taskcat test run --parameters InstanceType=t3.micro,Environment=test
```

### Parameter Debugging

```yaml
tests:
  debug-parameters:
    template: templates/debug.yaml
    parameters:
      # Use outputs to verify parameter values
      DebugInstanceType: t3.micro
      DebugEnvironment: $[taskcat_test_name]
      DebugRegion: $[taskcat_current_region]
      DebugProject: $[taskcat_project_name]
```

## Best Practices

### 1. Use Hierarchical Configuration

```yaml
# ✅ Good: Logical hierarchy
general:
  parameters:
    Owner: platform-team        # Global default

project:
  parameters:
    Environment: staging        # Project default
    
tests:
  production:
    parameters:
      Environment: prod         # Test-specific override
```

### 2. Group Related Parameters

```yaml
# ✅ Good: Grouped by function
tests:
  web-app:
    parameters:
      # Instance configuration
      InstanceType: m5.large
      MinSize: 2
      MaxSize: 10
      
      # Database configuration
      DatabaseInstanceClass: db.r5.large
      DatabasePassword: $[taskcat_genpass_20S]
      MultiAZ: true
      
      # Security configuration
      EnableEncryption: true
      SSLCertificateArn: $[taskcat_ssm_/ssl/cert/arn]
```

### 3. Use Meaningful Parameter Names

```yaml
# ✅ Good: Descriptive names
parameters:
  WebServerInstanceType: m5.large
  DatabaseMasterPassword: $[taskcat_genpass_20S]
  ApplicationLoadBalancerScheme: internet-facing
  
# ❌ Avoid: Generic names
parameters:
  Type1: m5.large
  Password: $[taskcat_genpass_20S]
  Scheme: internet-facing
```

### 4. Document Parameter Purpose

```yaml
tests:
  documented-test:
    template: templates/app.yaml
    parameters:
      # Production-grade instance for high availability
      InstanceType: m5.large
      
      # Secure password for RDS master user
      DatabasePassword: $[taskcat_genpass_20S]
      
      # Enable encryption for compliance requirements
      EnableEncryption: true
```

## Common Patterns

### Multi-Tier Application

```yaml
project:
  name: three-tier-app
  parameters:
    ProjectName: three-tier-app
    Environment: production
    
tests:
  web-tier:
    template: templates/web-tier.yaml
    parameters:
      InstanceType: m5.large
      MinSize: 2
      MaxSize: 10
      
  app-tier:
    template: templates/app-tier.yaml
    parameters:
      InstanceType: m5.xlarge
      MinSize: 3
      MaxSize: 15
      
  data-tier:
    template: templates/data-tier.yaml
    parameters:
      DatabaseInstanceClass: db.r5.2xlarge
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
      MultiAZ: true
```

### Blue-Green Deployment

```yaml
tests:
  blue-environment:
    template: templates/app.yaml
    parameters:
      Environment: blue
      InstanceType: m5.large
      LoadBalancerWeight: 100
      
  green-environment:
    template: templates/app.yaml
    parameters:
      Environment: green
      InstanceType: m5.large
      LoadBalancerWeight: 0
```

## Troubleshooting

### Common Issues

**Parameter not found:**
- Verify parameter exists in template
- Check parameter name spelling
- Ensure parameter is not marked as `NoEcho`

**Type mismatch:**
- Verify parameter type in template
- Check value format (string, number, boolean)
- Validate array/list formatting

**Override not working:**
- Check parameter hierarchy
- Verify configuration syntax
- Test with `taskcat lint`

For more help, see the [Troubleshooting Guide](troubleshooting.md).

## Next Steps

- [Dynamic Values](dynamic-values.md) - Runtime-evaluated parameters
- [Configuration Guide](configuration.md) - Complete configuration options
- [Schema Reference](schema.md) - Full parameter reference

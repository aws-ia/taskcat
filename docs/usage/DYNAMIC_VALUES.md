# Dynamic Values

Dynamic Values are runtime-evaluated parameters that provide flexible, context-aware configurations for your CloudFormation templates. These values are evaluated during taskcat execution and can pull data from your AWS environment, generate random values, or provide contextual information about your test run.

## Overview

Dynamic Values solve common testing challenges:

- **Environment-specific values**: Pull actual values from your AWS environment
- **Unique resource names**: Generate random strings to avoid naming conflicts
- **Context awareness**: Access current region, project name, and test information
- **Security**: Generate secure passwords and retrieve secrets safely
- **Flexibility**: Reference other parameters and create complex configurations

## Syntax

Dynamic Values use the syntax: `$[taskcat_function_name]` or `$[taskcat_function_name_parameter]`

```yaml
parameters:
  DatabasePassword: $[taskcat_genpass_16S]
  S3BucketName: $[taskcat_autobucket]
  CurrentRegion: $[taskcat_current_region]
  AvailabilityZones: $[taskcat_genaz_2]
```

## Complete Dynamic Values Reference

### Random Value Generation

| Dynamic Value | Description | Example Output | Use Case |
|---------------|-------------|----------------|----------|
| `$[taskcat_random-string]` | Generate 20-character random string | `kj8s9dkf7h3m2n4p5q6r` | Unique resource identifiers |
| `$[taskcat_random-numbers]` | Generate 20-digit random number | `12345678901234567890` | Unique numeric identifiers |
| `$[taskcat_genuuid]` | Generate UUID v1 | `550e8400-e29b-41d4-a716-446655440000` | Globally unique identifiers |

### Password Generation

| Dynamic Value | Description | Example | Use Case |
|---------------|-------------|---------|----------|
| `$[taskcat_genpass_8]` | 8-character alphanumeric password | `aB3dE7gH` | Simple passwords |
| `$[taskcat_genpass_16S]` | 16-character password with special chars | `aB3!dE7@gH9#kL2$` | Secure passwords |
| `$[taskcat_genpass_32A]` | 32-character alphanumeric password | `aB3dE7gH9kL2mN4pQ6rS8tU0vW2xY4zA` | Long secure passwords |

**Password Types:**
- No suffix: Alphanumeric only
- `S`: Includes special characters (!@#$%^&*)
- `A`: Alphanumeric only (explicit)

### AWS Environment Values

| Dynamic Value | Description | Example Output | Use Case |
|---------------|-------------|----------------|----------|
| `$[taskcat_current_region]` | Current AWS region | `us-east-1` | Region-specific configurations |
| `$[taskcat_genaz_2]` | 2 availability zones | `us-east-1a,us-east-1b` | Multi-AZ deployments |
| `$[taskcat_genaz_3]` | 3 availability zones | `us-east-1a,us-east-1b,us-east-1c` | High availability setups |
| `$[taskcat_gensingleaz_1]` | Single AZ (1st available) | `us-east-1a` | Single AZ deployments |
| `$[taskcat_gensingleaz_2]` | Single AZ (2nd available) | `us-east-1b` | Specific AZ selection |

### S3 and Storage

| Dynamic Value | Description | Example Output | Use Case |
|---------------|-------------|----------------|----------|
| `$[taskcat_autobucket]` | Auto-generated S3 bucket name | `tcat-myproject-us-east-1-123456789` | Template artifacts |
| `$[taskcat_autobucket_prefix]` | S3 bucket prefix | `myproject-us-east-1-123456789` | Custom bucket naming |

### Context Information

| Dynamic Value | Description | Example Output | Use Case |
|---------------|-------------|----------------|----------|
| `$[taskcat_project_name]` | Current project name | `my-cloudformation-project` | Tagging and naming |
| `$[taskcat_test_name]` | Current test name | `production-test` | Test identification |
| `$[taskcat_git_branch]` | Current Git branch | `feature/new-feature` | Branch-specific configs |

### Parameter References

| Dynamic Value | Description | Example | Use Case |
|---------------|-------------|---------|----------|
| `$[taskcat_getval_ParameterName]` | Reference another parameter | `$[taskcat_getval_DatabasePassword]` | Parameter dependencies |

### AWS Services Integration

| Dynamic Value | Description | Example | Use Case |
|---------------|-------------|---------|----------|
| `$[taskcat_ssm_/path/to/parameter]` | Retrieve SSM Parameter | `$[taskcat_ssm_/app/database/host]` | Configuration management |
| `$[taskcat_secretsmanager_secret-name]` | Retrieve Secrets Manager value | `$[taskcat_secretsmanager_prod/db/password]` | Secure credential retrieval |

### Legacy/Specialized Values

| Dynamic Value | Description | Example Output | Use Case |
|---------------|-------------|----------------|----------|
| `$[taskcat_getkeypair]` | Default key pair name | `cikey` | EC2 key pair reference |
| `$[taskcat_getlicensebucket]` | License bucket placeholder | `override_this` | License content storage |
| `$[taskcat_getmediabucket]` | Media bucket placeholder | `override_this` | Media content storage |

## Advanced Examples

### Multi-Tier Application

```yaml
project:
  name: multi-tier-app
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1

global:
  parameters:
    ProjectName: $[taskcat_project_name]
    Environment: production
    
tests:
  vpc-infrastructure:
    template: templates/vpc.yaml
    parameters:
      VpcName: $[taskcat_project_name]-vpc-$[taskcat_current_region]
      AvailabilityZones: $[taskcat_genaz_3]
      
  database-tier:
    template: templates/rds.yaml
    parameters:
      DBInstanceIdentifier: $[taskcat_project_name]-db-$[taskcat_random-string]
      MasterUsername: admin
      MasterUserPassword: $[taskcat_genpass_32S]
      DBSubnetGroupName: $[taskcat_getval_VpcName]-db-subnets
      
  application-tier:
    template: templates/app.yaml
    parameters:
      ApplicationName: $[taskcat_project_name]-app
      InstanceType: m5.large
      KeyName: $[taskcat_getkeypair]
      S3Bucket: $[taskcat_autobucket]
      DatabaseEndpoint: $[taskcat_getval_DBInstanceIdentifier]
      
  monitoring:
    template: templates/monitoring.yaml
    parameters:
      DashboardName: $[taskcat_project_name]-$[taskcat_test_name]-dashboard
      LogGroupName: /aws/lambda/$[taskcat_project_name]
      AlertEmail: $[taskcat_ssm_/notifications/email]
```

### Environment-Specific Configuration

```yaml
project:
  name: environment-configs
  regions:
    - us-east-1

tests:
  development:
    template: templates/app.yaml
    parameters:
      Environment: dev
      InstanceType: t3.micro
      DatabasePassword: $[taskcat_genpass_16]
      S3Bucket: $[taskcat_project_name]-dev-$[taskcat_current_region]
      
  staging:
    template: templates/app.yaml
    parameters:
      Environment: staging
      InstanceType: t3.small
      DatabasePassword: $[taskcat_secretsmanager_staging/db/password]
      S3Bucket: $[taskcat_project_name]-staging-$[taskcat_current_region]
      
  production:
    template: templates/app.yaml
    parameters:
      Environment: prod
      InstanceType: m5.large
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
      S3Bucket: $[taskcat_project_name]-prod-$[taskcat_current_region]
      BackupRetention: 30
      MonitoringEnabled: true
```

### Security-Focused Configuration

```yaml
project:
  name: secure-app
  regions:
    - us-east-1
    - us-west-2

tests:
  secure-deployment:
    template: templates/secure-app.yaml
    parameters:
      # Generate unique, secure passwords
      DatabaseMasterPassword: $[taskcat_genpass_32S]
      ApplicationSecret: $[taskcat_genpass_24S]
      
      # Use AWS Secrets Manager for production secrets
      ApiKey: $[taskcat_secretsmanager_prod/api/key]
      CertificateArn: $[taskcat_ssm_/ssl/certificate/arn]
      
      # Generate unique resource names
      KMSKeyAlias: $[taskcat_project_name]-key-$[taskcat_genuuid]
      S3BucketName: $[taskcat_autobucket]
      
      # Context-aware naming
      LogGroupName: /aws/lambda/$[taskcat_project_name]-$[taskcat_current_region]
      
      # Reference other parameters
      DatabasePasswordConfirm: $[taskcat_getval_DatabaseMasterPassword]
```

### Multi-Region Deployment

```yaml
project:
  name: global-app
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
    - ap-southeast-1

tests:
  global-infrastructure:
    template: templates/global-app.yaml
    parameters:
      # Region-specific configurations
      PrimaryRegion: us-east-1
      CurrentRegion: $[taskcat_current_region]
      
      # Generate region-specific AZs
      AvailabilityZones: $[taskcat_genaz_2]
      
      # Unique naming per region
      S3BucketName: $[taskcat_project_name]-$[taskcat_current_region]-$[taskcat_random-numbers]
      
      # Global unique identifiers
      DeploymentId: $[taskcat_genuuid]
      
      # Branch-specific configurations
      GitBranch: $[taskcat_git_branch]
      
      # Environment from SSM
      Environment: $[taskcat_ssm_/global/environment]
```

## Best Practices

### 1. Use Appropriate Value Types

```yaml
# ✅ Good: Use specific types for specific purposes
parameters:
  DatabasePassword: $[taskcat_genpass_16S]    # Secure password
  ResourceId: $[taskcat_genuuid]              # Globally unique
  BucketName: $[taskcat_autobucket]           # S3-compliant naming
  
# ❌ Avoid: Using generic values for specific purposes
parameters:
  DatabasePassword: $[taskcat_random-string]  # Not secure enough
  ResourceId: $[taskcat_random-numbers]       # May not be unique
```

### 2. Leverage Parameter References

```yaml
# ✅ Good: Reference parameters to maintain consistency
parameters:
  MasterPassword: $[taskcat_genpass_20S]
  PasswordConfirm: $[taskcat_getval_MasterPassword]
  
# ❌ Avoid: Generating separate values for related parameters
parameters:
  MasterPassword: $[taskcat_genpass_20S]
  PasswordConfirm: $[taskcat_genpass_20S]     # Different values!
```

### 3. Use Context-Aware Naming

```yaml
# ✅ Good: Include context in resource names
parameters:
  LogGroup: /aws/lambda/$[taskcat_project_name]-$[taskcat_current_region]
  S3Bucket: $[taskcat_project_name]-logs-$[taskcat_current_region]
  
# ❌ Avoid: Generic naming that may conflict
parameters:
  LogGroup: /aws/lambda/myapp
  S3Bucket: myapp-logs
```

### 4. Secure Credential Management

```yaml
# ✅ Good: Use AWS services for production secrets
parameters:
  DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
  ApiKey: $[taskcat_ssm_/app/api/key]
  
# ✅ Good: Generate secure passwords for testing
parameters:
  TestPassword: $[taskcat_genpass_16S]
  
# ❌ Avoid: Hardcoded secrets
parameters:
  DatabasePassword: "hardcoded-password"
```

## Troubleshooting

### Common Issues

**Dynamic Value not replaced:**
- Check syntax: `$[taskcat_function_name]`
- Verify function name spelling
- Ensure proper parameter placement

**AWS service integration fails:**
- Verify IAM permissions for SSM/Secrets Manager
- Check parameter/secret exists in target region
- Validate parameter path format

**AZ generation fails:**
- Check if region has enough AZs
- Verify region is enabled in your account
- Consider AZ exclusions in configuration

**Parameter reference fails:**
- Ensure referenced parameter exists
- Check parameter name spelling
- Verify parameter is defined before reference

For more troubleshooting help, see the [Troubleshooting Guide](../support/troubleshooting.md).

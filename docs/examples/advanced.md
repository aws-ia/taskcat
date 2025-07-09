# Advanced Examples

This page covers more complex TaskCat configurations and use cases.

## Multi-Test Configuration

```yaml
# .taskcat.yml
project:
  name: enterprise-app
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1

global:
  parameters:
    Environment: testing
    Owner: devops-team

tests:
  infrastructure:
    template: templates/infrastructure.yaml
    parameters:
      VpcCidr: 10.0.0.0/16
      AvailabilityZones: $[taskcat_genaz_3]
      
  application:
    template: templates/application.yaml
    parameters:
      InstanceType: t3.medium
      DatabasePassword: $[taskcat_genpass_16S]
      
  monitoring:
    template: templates/monitoring.yaml
    regions:
      - us-east-1  # Only deploy monitoring in primary region
```

## Using AWS Service Integration

```yaml
tests:
  app-with-secrets:
    template: templates/app.yaml
    parameters:
      # Get AMI ID from SSM Parameter Store
      LatestAMI: $[taskcat_ssm_/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2]
      
      # Get database credentials from Secrets Manager
      DatabaseCredentials: $[taskcat_secretsmanager_prod/database/master]
      
      # Use current region for region-specific resources
      DeploymentRegion: $[taskcat_current_region]
      
      # Generate unique identifiers
      UniqueId: $[taskcat_genuuid]
```

## Parameter Validation

```yaml
tests:
  parameter-validation:
    template: templates/app.yaml
    parameters:
      # Password with confirmation
      AdminPassword: $[taskcat_genpass_12S]
      ConfirmPassword: $[taskcat_getval_AdminPassword]
      
      # Consistent naming
      ProjectName: $[taskcat_project_name]
      TestName: $[taskcat_test_name]
```

## Custom Authentication

```yaml
project:
  name: multi-account-test
  auth:
    us-east-1: production-profile
    us-west-2: staging-profile
    eu-west-1: development-profile
    default: default-profile
```

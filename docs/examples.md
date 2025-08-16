# Examples

Explore real-world taskcat configurations and learn from practical implementations. These examples demonstrate best practices, advanced features, and common use cases.

## Basic Examples

### Simple S3 Bucket Test

```yaml
# .taskcat.yml
project:
  name: simple-s3-test
  regions:
    - us-east-1

tests:
  basic:
    template: s3-bucket.yaml
    parameters:
      BucketName: $[taskcat_autobucket]
```

```yaml
# s3-bucket.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Simple S3 bucket

Parameters:
  BucketName:
    Type: String

Resources:
  TestBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref BucketName
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

Outputs:
  BucketName:
    Value: !Ref TestBucket
  BucketArn:
    Value: !GetAtt TestBucket.Arn
```

### Multi-Region VPC Test

```yaml
# .taskcat.yml
project:
  name: vpc-multi-region
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1

tests:
  vpc-test:
    template: vpc.yaml
    parameters:
      VpcCidr: 10.0.0.0/16
      AvailabilityZones: $[taskcat_genaz_2]
      Environment: test
```

## Intermediate Examples

### Web Application with Database

```yaml
# .taskcat.yml
project:
  name: web-app-with-db
  regions:
    - us-east-1
    - us-west-2
  parameters:
    ProjectName: web-application
    Environment: staging

tests:
  vpc-infrastructure:
    template: templates/vpc.yaml
    parameters:
      VpcCidr: 10.0.0.0/16
      AvailabilityZones: $[taskcat_genaz_3]
      
  database:
    template: templates/rds.yaml
    parameters:
      DatabaseName: webapp
      DatabaseUsername: admin
      DatabasePassword: $[taskcat_genpass_16S]
      DatabaseInstanceClass: db.t3.micro
      
  web-application:
    template: templates/web-app.yaml
    parameters:
      InstanceType: t3.medium
      MinSize: 2
      MaxSize: 6
      KeyName: $[taskcat_getkeypair]
      S3Bucket: $[taskcat_autobucket]
```

### Serverless Application

```yaml
# .taskcat.yml
project:
  name: serverless-api
  regions:
    - us-east-1
    - us-west-2
  lambda_source_path: src/functions
  lambda_zip_path: dist/functions
  package_lambda: true

tests:
  api-gateway:
    template: templates/api-gateway.yaml
    parameters:
      ApiName: $[taskcat_project_name]-api
      StageName: $[taskcat_test_name]
      
  lambda-functions:
    template: templates/lambda.yaml
    parameters:
      FunctionName: $[taskcat_project_name]-function
      Runtime: python3.9
      MemorySize: 256
      Timeout: 30
      S3Bucket: $[taskcat_autobucket]
      
  dynamodb-table:
    template: templates/dynamodb.yaml
    parameters:
      TableName: $[taskcat_project_name]-table
      BillingMode: PAY_PER_REQUEST
```

## Advanced Examples

### Multi-Environment Enterprise Application

```yaml
# .taskcat.yml
project:
  name: enterprise-app
  owner: platform-team@company.com
  s3_regional_buckets: true
  package_lambda: true

general:
  parameters:
    ProjectName: enterprise-application
    Owner: platform-team
  tags:
    CostCenter: "1001"
    Department: Engineering

tests:
  development:
    template: templates/main.yaml
    regions:
      - us-east-1
    parameters:
      Environment: dev
      InstanceType: t3.micro
      DatabaseInstanceClass: db.t3.micro
      MinSize: 1
      MaxSize: 2
      EnableMonitoring: false
      BackupRetentionPeriod: 1
      
  staging:
    template: templates/main.yaml
    regions:
      - us-east-1
      - us-west-2
    parameters:
      Environment: staging
      InstanceType: t3.medium
      DatabaseInstanceClass: db.t3.small
      MinSize: 2
      MaxSize: 4
      EnableMonitoring: true
      BackupRetentionPeriod: 7
      DatabasePassword: $[taskcat_genpass_20S]
      
  production:
    template: templates/main.yaml
    regions:
      - us-east-1
      - us-west-2
      - eu-west-1
    parameters:
      Environment: prod
      InstanceType: m5.large
      DatabaseInstanceClass: db.r5.large
      MinSize: 3
      MaxSize: 10
      EnableMonitoring: true
      EnableEncryption: true
      MultiAZ: true
      BackupRetentionPeriod: 30
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
      SSLCertificateArn: $[taskcat_ssm_/ssl/certificate/arn]
    auth:
      us-east-1: production-profile
      us-west-2: production-profile
      eu-west-1: europe-profile
```

### Cross-Account Deployment

```yaml
# .taskcat.yml
project:
  name: cross-account-app
  
tests:
  shared-services-account:
    template: templates/shared-services.yaml
    regions:
      - us-east-1
    auth:
      default: shared-services-profile
    parameters:
      Environment: shared
      VpcCidr: 10.0.0.0/16
      
  development-account:
    template: templates/application.yaml
    regions:
      - us-east-1
    auth:
      default: dev-account-profile
    parameters:
      Environment: dev
      SharedServicesVpcId: $[taskcat_ssm_/shared/vpc/id]
      InstanceType: t3.micro
      
  production-account:
    template: templates/application.yaml
    regions:
      - us-east-1
      - us-west-2
    auth:
      default: prod-account-profile
    parameters:
      Environment: prod
      SharedServicesVpcId: $[taskcat_ssm_/shared/vpc/id]
      InstanceType: m5.large
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
```

### Microservices Architecture

```yaml
# .taskcat.yml
project:
  name: microservices-platform
  regions:
    - us-east-1
    - us-west-2
  lambda_source_path: services
  package_lambda: true

general:
  parameters:
    Platform: microservices
    Environment: production
  tags:
    Architecture: microservices
    ManagedBy: taskcat

tests:
  infrastructure:
    template: templates/infrastructure.yaml
    parameters:
      VpcCidr: 10.0.0.0/16
      AvailabilityZones: $[taskcat_genaz_3]
      ClusterName: $[taskcat_project_name]-cluster
      
  user-service:
    template: templates/microservice.yaml
    parameters:
      ServiceName: user-service
      ContainerImage: user-service:latest
      ContainerPort: 8080
      DesiredCount: 3
      DatabaseName: users
      DatabasePassword: $[taskcat_genpass_20S]
      
  order-service:
    template: templates/microservice.yaml
    parameters:
      ServiceName: order-service
      ContainerImage: order-service:latest
      ContainerPort: 8081
      DesiredCount: 2
      DatabaseName: orders
      DatabasePassword: $[taskcat_genpass_20S]
      
  notification-service:
    template: templates/lambda-service.yaml
    parameters:
      ServiceName: notification-service
      Runtime: python3.9
      MemorySize: 512
      Timeout: 60
      QueueName: $[taskcat_project_name]-notifications
      
  api-gateway:
    template: templates/api-gateway.yaml
    parameters:
      ApiName: $[taskcat_project_name]-api
      StageName: v1
      UserServiceEndpoint: $[taskcat_getval_UserServiceEndpoint]
      OrderServiceEndpoint: $[taskcat_getval_OrderServiceEndpoint]
```

### Data Pipeline

```yaml
# .taskcat.yml
project:
  name: data-pipeline
  regions:
    - us-east-1
  parameters:
    DataBucket: $[taskcat_autobucket]
    Environment: production

tests:
  data-ingestion:
    template: templates/data-ingestion.yaml
    parameters:
      KinesisStreamName: $[taskcat_project_name]-stream
      KinesisShardCount: 2
      FirehoseDeliveryStreamName: $[taskcat_project_name]-firehose
      S3Bucket: $[taskcat_getval_DataBucket]
      
  data-processing:
    template: templates/data-processing.yaml
    parameters:
      GlueJobName: $[taskcat_project_name]-etl
      GlueJobScript: s3://$[taskcat_getval_DataBucket]/scripts/etl.py
      DatabaseName: $[taskcat_project_name]_db
      TableName: processed_data
      
  data-analytics:
    template: templates/data-analytics.yaml
    parameters:
      RedshiftClusterIdentifier: $[taskcat_project_name]-cluster
      RedshiftDatabaseName: analytics
      RedshiftMasterUsername: admin
      RedshiftMasterPassword: $[taskcat_genpass_20S]
      RedshiftNodeType: dc2.large
      RedshiftNumberOfNodes: 2
```

## Specialized Examples

### Security-Focused Deployment

```yaml
# .taskcat.yml
project:
  name: secure-application
  regions:
    - us-east-1
    - us-west-2

tests:
  security-baseline:
    template: templates/security-baseline.yaml
    parameters:
      EnableCloudTrail: true
      EnableGuardDuty: true
      EnableSecurityHub: true
      EnableConfig: true
      CloudTrailS3Bucket: $[taskcat_autobucket]
      
  encrypted-application:
    template: templates/encrypted-app.yaml
    parameters:
      KMSKeyAlias: $[taskcat_project_name]-key
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
      SSLCertificateArn: $[taskcat_ssm_/ssl/certificate/arn]
      EnableEncryptionAtRest: true
      EnableEncryptionInTransit: true
      InstanceType: m5.large
      
  compliance-monitoring:
    template: templates/compliance.yaml
    parameters:
      ComplianceFramework: SOC2
      LogRetentionPeriod: 2557  # 7 years in days
      EnableLogEncryption: true
      MonitoringS3Bucket: $[taskcat_autobucket]
```

### Disaster Recovery Setup

```yaml
# .taskcat.yml
project:
  name: disaster-recovery
  
tests:
  primary-region:
    template: templates/primary-infrastructure.yaml
    regions:
      - us-east-1
    parameters:
      Environment: production
      IsPrimaryRegion: true
      DatabaseInstanceClass: db.r5.xlarge
      MultiAZ: true
      BackupRetentionPeriod: 35
      CrossRegionBackupEnabled: true
      ReplicationTargetRegion: us-west-2
      
  disaster-recovery-region:
    template: templates/dr-infrastructure.yaml
    regions:
      - us-west-2
    parameters:
      Environment: production
      IsDRRegion: true
      DatabaseInstanceClass: db.r5.large
      ReadReplicaSourceRegion: us-east-1
      AutomatedBackupRetentionPeriod: 35
      
  failover-automation:
    template: templates/failover-automation.yaml
    regions:
      - us-east-1
      - us-west-2
    parameters:
      PrimaryRegion: us-east-1
      DRRegion: us-west-2
      Route53HealthCheckUrl: https://api.example.com/health
      FailoverThreshold: 3
```

## Testing Patterns

### Blue-Green Deployment Testing

```yaml
# .taskcat.yml
project:
  name: blue-green-deployment
  
tests:
  blue-environment:
    template: templates/application.yaml
    parameters:
      Environment: blue
      Version: v1.0.0
      TrafficWeight: 100
      InstanceType: m5.large
      
  green-environment:
    template: templates/application.yaml
    parameters:
      Environment: green
      Version: v1.1.0
      TrafficWeight: 0
      InstanceType: m5.large
      
  traffic-shifting:
    template: templates/traffic-manager.yaml
    parameters:
      BlueEnvironmentArn: $[taskcat_getval_BlueEnvironmentArn]
      GreenEnvironmentArn: $[taskcat_getval_GreenEnvironmentArn]
      InitialTrafficPercentage: 10
```

### A/B Testing Infrastructure

```yaml
# .taskcat.yml
project:
  name: ab-testing-platform
  
tests:
  variant-a:
    template: templates/application-variant.yaml
    parameters:
      VariantName: A
      FeatureFlags: feature-a-enabled
      InstanceType: m5.large
      TrafficPercentage: 50
      
  variant-b:
    template: templates/application-variant.yaml
    parameters:
      VariantName: B
      FeatureFlags: feature-b-enabled
      InstanceType: m5.large
      TrafficPercentage: 50
      
  analytics-infrastructure:
    template: templates/analytics.yaml
    parameters:
      KinesisStreamName: $[taskcat_project_name]-events
      ElasticsearchDomain: $[taskcat_project_name]-analytics
      KibanaDashboardName: ab-testing-dashboard
```

## Best Practices Examples

### Parameterized and Reusable

```yaml
# .taskcat.yml - Good example of reusable configuration
project:
  name: reusable-infrastructure
  parameters:
    # Common parameters
    ProjectName: $[taskcat_project_name]
    Owner: platform-team
    
general:
  parameters:
    # Global defaults
    Environment: test
    EnableMonitoring: true
  tags:
    ManagedBy: taskcat
    Project: $[taskcat_project_name]

tests:
  # Small deployment for development
  small:
    template: templates/scalable-app.yaml
    parameters:
      Size: small
      InstanceType: t3.micro
      MinSize: 1
      MaxSize: 2
      DatabaseInstanceClass: db.t3.micro
      
  # Medium deployment for staging
  medium:
    template: templates/scalable-app.yaml
    parameters:
      Size: medium
      InstanceType: t3.medium
      MinSize: 2
      MaxSize: 4
      DatabaseInstanceClass: db.t3.small
      
  # Large deployment for production
  large:
    template: templates/scalable-app.yaml
    parameters:
      Size: large
      InstanceType: m5.large
      MinSize: 3
      MaxSize: 10
      DatabaseInstanceClass: db.r5.large
      EnableEncryption: true
      MultiAZ: true
```

### Security Best Practices

```yaml
# .taskcat.yml - Security-focused configuration
project:
  name: secure-by-design
  
tests:
  security-compliant:
    template: templates/secure-application.yaml
    parameters:
      # Use Secrets Manager for sensitive data
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
      ApiKey: $[taskcat_secretsmanager_prod/api/key]
      
      # Use SSM for configuration
      DatabaseEndpoint: $[taskcat_ssm_/app/database/endpoint]
      CacheEndpoint: $[taskcat_ssm_/app/cache/endpoint]
      
      # Generate unique, secure values
      EncryptionKey: $[taskcat_genuuid]
      S3Bucket: $[taskcat_autobucket]
      
      # Security settings
      EnableEncryption: true
      EnableLogging: true
      EnableMonitoring: true
      RestrictPublicAccess: true
```

## Integration Examples

### CI/CD Pipeline Integration

```yaml
# .taskcat.yml for CI/CD
project:
  name: cicd-integration
  
tests:
  pull-request:
    template: templates/app.yaml
    regions:
      - us-east-1
    parameters:
      Environment: pr-$[taskcat_git_branch]
      InstanceType: t3.micro
      
  staging-deployment:
    template: templates/app.yaml
    regions:
      - us-east-1
      - us-west-2
    parameters:
      Environment: staging
      InstanceType: t3.medium
      GitCommit: $[taskcat_git_branch]
      
  production-deployment:
    template: templates/app.yaml
    regions:
      - us-east-1
      - us-west-2
      - eu-west-1
    parameters:
      Environment: production
      InstanceType: m5.large
      GitCommit: $[taskcat_git_branch]
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
```

These examples demonstrate the flexibility and power of taskcat for testing CloudFormation templates across various scenarios, from simple single-resource tests to complex multi-tier applications and enterprise deployments.

## Next Steps

- [Configuration Guide](configuration.md) - Detailed configuration options
- [Dynamic Values](dynamic-values.md) - Runtime-evaluated parameters
- [Parameter Overrides](parameter-overrides.md) - Advanced parameter techniques
- [Schema Reference](schema.md) - Complete configuration reference

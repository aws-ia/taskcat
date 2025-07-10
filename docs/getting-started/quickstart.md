# Quick Start Guide

Get up and running with taskcat in just a few minutes! This guide will walk you through creating and running your first taskcat test.

## Step 1: Create a Simple Template

First, let's create a basic CloudFormation template to test:

```yaml
# templates/simple-s3.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Simple S3 bucket for taskcat testing'

Parameters:
  BucketName:
    Type: String
    Description: Name for the S3 bucket
    Default: my-test-bucket

Resources:
  TestBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "${BucketName}-${AWS::Region}-${AWS::AccountId}"
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

Outputs:
  BucketName:
    Description: Name of the created bucket
    Value: !Ref TestBucket
    Export:
      Name: !Sub "${AWS::StackName}-BucketName"
```

## Step 2: Create taskcat Configuration

Create a taskcat configuration file:

```yaml
# .taskcat.yml
project:
  name: my-first-taskcat-test
  regions:
    - us-east-1
    - us-west-2

tests:
  simple-test:
    template: templates/simple-s3.yaml
    parameters:
      BucketName: $[taskcat_random-string]
```

## Step 3: Run Your First Test

Execute the test:

```bash
taskcat test run
```

taskcat will:
1. 🚀 Deploy your template in specified regions
2. ✅ Validate the deployment
3. 📊 Generate a detailed report
4. 🧹 Clean up resources

## Step 4: View Results

Check the results in the `taskcat_outputs` directory:

```bash
ls taskcat_outputs/
# index.html - Main report
# logs/ - Detailed logs
# templates/ - Processed templates
```

Open `taskcat_outputs/index.html` in your browser to see the visual report.

## What Just Happened?

taskcat performed these actions:

1. **Template Processing**: Replaced pseudo-parameters with actual values
2. **Multi-Region Deployment**: Created CloudFormation stacks in us-east-1 and us-west-2
3. **Validation**: Verified successful deployment and resource creation
4. **Reporting**: Generated comprehensive HTML and JSON reports
5. **Cleanup**: Automatically deleted test resources

## Next Steps

Now that you've run your first test, explore:

- [Configuration Guide](configuration.md) - Advanced configuration options
- [Dynamic Values](../usage/DYNAMIC_VALUES.md) - Runtime-evaluated parameters and AWS environment integration
- [Examples](../examples/) - Real-world usage scenarios

## Common Next Actions

### Test Multiple Templates
```yaml
tests:
  test1:
    template: templates/vpc.yaml
  test2:
    template: templates/ec2.yaml
    parameters:
      InstanceType: t3.micro
```

### Add Parameter Overrides
```yaml
tests:
  production-test:
    template: templates/app.yaml
    parameters:
      Environment: prod
      InstanceType: m5.large
```

### Customize Regions
```yaml
project:
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
    - ap-southeast-1
```

Congratulations! You've successfully run your first taskcat test. 🎉

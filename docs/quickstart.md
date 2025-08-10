# Quick Start

Get up and running with taskcat in under 5 minutes. This guide walks you through creating and running your first test.

## Step 1: Create a CloudFormation Template

Create a simple template to test:

```yaml
# template.yaml
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
      BucketName: !Sub "${BucketName}-${AWS::AccountId}-${AWS::Region}"
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

Outputs:
  BucketName:
    Description: Name of the created S3 bucket
    Value: !Ref TestBucket
  BucketArn:
    Description: ARN of the created S3 bucket
    Value: !GetAtt TestBucket.Arn
```

## Step 2: Create taskcat Configuration

Create a `.taskcat.yml` configuration file:

```yaml
# .taskcat.yml
project:
  name: my-first-test
  regions:
    - us-east-1
    - us-west-2

tests:
  basic-test:
    template: template.yaml
    parameters:
      BucketName: $[taskcat_random-string]
```

## Step 3: Run Your First Test

Execute the test:

```bash
taskcat test run
```

taskcat will:

1. 🚀 **Deploy** your template in specified regions
2. ✅ **Validate** the deployment succeeds  
3. 📊 **Generate** a detailed report
4. 🧹 **Clean up** all test resources

## Step 4: View Results

Check the results:

```bash
# List output files
ls taskcat_outputs/

# Open the HTML report
open taskcat_outputs/index.html
```

The report includes:
- Deployment status for each region
- CloudFormation events and logs
- Resource details and outputs
- Performance metrics

## What Just Happened?

taskcat performed these actions:

1. **Template Processing** - Replaced `$[taskcat_random-string]` with a unique value
2. **Multi-Region Deployment** - Created CloudFormation stacks in us-east-1 and us-west-2
3. **Validation** - Verified successful deployment and resource creation
4. **Reporting** - Generated comprehensive HTML and JSON reports
5. **Cleanup** - Automatically deleted all test resources

## Next Steps

Now that you've run your first test, explore:

### Advanced Configuration
```yaml
tests:
  production-test:
    template: template.yaml
    parameters:
      BucketName: $[taskcat_project_name]-prod
    regions:
      - us-east-1
      - us-west-2
      - eu-west-1
      
  development-test:
    template: template.yaml
    parameters:
      BucketName: $[taskcat_project_name]-dev
    regions:
      - us-east-1
```

### Multiple Templates
```yaml
tests:
  vpc-test:
    template: templates/vpc.yaml
    
  app-test:
    template: templates/application.yaml
    parameters:
      InstanceType: t3.micro
```

### Dynamic Parameters
```yaml
tests:
  secure-test:
    template: template.yaml
    parameters:
      BucketName: $[taskcat_autobucket]
      DatabasePassword: $[taskcat_genpass_16S]
      AvailabilityZones: $[taskcat_genaz_2]
      CurrentRegion: $[taskcat_current_region]
```

## Common Commands

```bash
# Test specific configuration
taskcat test run --config-file custom.yml

# Test specific regions
taskcat test run --regions us-east-1,us-west-2

# Keep resources after testing (for debugging)
taskcat test run --no-delete

# Lint configuration before testing
taskcat lint

# List available tests
taskcat test list
```

## Troubleshooting

**Test fails with permission errors:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check IAM permissions for CloudFormation and S3

**Template validation errors:**
- Run `taskcat lint` to check configuration
- Validate CloudFormation template syntax

**Resources not cleaned up:**
- Check CloudFormation console for failed deletions
- Manually delete stuck stacks if needed

## Learn More

- [Configuration Guide](configuration.md) - Advanced configuration options
- [Dynamic Values](dynamic-values.md) - Runtime-evaluated parameters  
- [Examples](examples.md) - Real-world usage scenarios
- [Schema Reference](schema.md) - Complete configuration reference

Congratulations! You've successfully run your first taskcat test. 🎉

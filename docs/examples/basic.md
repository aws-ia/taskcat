# Basic Usage Examples

This page provides simple, practical examples to help you get started with taskcat.

## Simple S3 Bucket Test

```yaml
# .taskcat.yml
project:
  name: simple-s3-test
  regions:
    - us-east-1
    - us-west-2

tests:
  s3-bucket:
    template: templates/s3-bucket.yaml
    parameters:
      BucketName: $[taskcat_autobucket]
```

```yaml
# templates/s3-bucket.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Simple S3 bucket

Parameters:
  BucketName:
    Type: String
    Description: Name of the S3 bucket

Resources:
  TestBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref BucketName

Outputs:
  BucketName:
    Value: !Ref TestBucket
    Description: Name of the created bucket
```

## Multi-AZ VPC Test

```yaml
# .taskcat.yml
project:
  name: vpc-test
  regions:
    - us-east-1
    - eu-west-1

tests:
  vpc-multi-az:
    template: templates/vpc.yaml
    parameters:
      AvailabilityZones: $[taskcat_genaz_2]
      VpcCidr: 10.0.0.0/16
```

## Running the Tests

```bash
# Run all tests
taskcat test run

# Run specific test
taskcat test run --test-names s3-bucket

# Run with custom output directory
taskcat test run --output-directory ./my-results
```

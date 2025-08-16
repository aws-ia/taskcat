# Troubleshooting

Common issues and solutions for taskcat configuration and execution problems.

## Installation Issues

### Python Version Compatibility

**Problem:** `taskcat requires Python 3.8 or higher`

**Solution:**
```bash
# Check Python version
python --version
python3 --version

# Install Python 3.8+ if needed
# macOS with Homebrew
brew install python@3.9

# Ubuntu/Debian
sudo apt update
sudo apt install python3.9

# Update pip and reinstall
pip3 install --upgrade pip
pip3 install taskcat
```

### Permission Denied Errors

**Problem:** `Permission denied` during installation

**Solution:**
```bash
# Install with user flag
pip install --user taskcat

# Or use virtual environment
python -m venv taskcat-env
source taskcat-env/bin/activate  # Linux/macOS
# taskcat-env\Scripts\activate   # Windows
pip install taskcat
```

### Package Not Found

**Problem:** `No module named 'taskcat'`

**Solution:**
```bash
# Verify installation
pip list | grep taskcat

# Reinstall if missing
pip uninstall taskcat
pip install taskcat

# Check PATH
echo $PATH
which taskcat
```

## AWS Configuration Issues

### Credentials Not Found

**Problem:** `Unable to locate credentials`

**Solution:**
```bash
# Check AWS configuration
aws configure list
aws sts get-caller-identity

# Configure credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

### Insufficient Permissions

**Problem:** `Access Denied` or `User is not authorized`

**Solution:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "iam:ListRoles",
        "iam:PassRole",
        "ec2:Describe*",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### Region Not Available

**Problem:** `Region not supported` or `Service not available`

**Solution:**
```yaml
# Check available regions
tests:
  region-test:
    template: template.yaml
    regions:
      - us-east-1      # Always available
      - us-west-2      # Good alternative
    # Remove unsupported regions
```

## Configuration Issues

### YAML Syntax Errors

**Problem:** `YAML parsing error` or `Invalid configuration`

**Solution:**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.taskcat.yml'))"

# Use proper indentation (spaces, not tabs)
# Check for special characters
# Validate with taskcat lint
taskcat lint
```

### Template Not Found

**Problem:** `Template file not found`

**Solution:**
```yaml
# Use correct relative paths
tests:
  my-test:
    template: templates/app.yaml  # Relative to .taskcat.yml
    # Not: /full/path/to/template.yaml
```

```bash
# Verify file exists
ls -la templates/
ls -la templates/app.yaml
```

### Parameter Validation Errors

**Problem:** `Parameter validation failed`

**Solution:**
```yaml
# Check parameter types and constraints
parameters:
  InstanceType: t3.micro        # String
  Port: 8080                    # Number
  EnableLogging: true           # Boolean
  SecurityGroups:               # Array
    - sg-12345678
    - sg-87654321
```

## Dynamic Values Issues

### Dynamic Value Not Replaced

**Problem:** `$[taskcat_genpass_16S]` appears in CloudFormation

**Solution:**
```yaml
# Check syntax - must be exact
parameters:
  Password: $[taskcat_genpass_16S]  # ✅ Correct
  # Password: $[taskcat_genpass_16s]  # ❌ Wrong case
  # Password: ${taskcat_genpass_16S}  # ❌ Wrong brackets
```

### AWS Service Integration Fails

**Problem:** `$[taskcat_ssm_/path]` returns error

**Solution:**
```bash
# Verify parameter exists
aws ssm get-parameter --name /path/to/parameter

# Check permissions
aws iam get-user
aws iam list-attached-user-policies --user-name your-username

# Verify region
aws ssm get-parameter --name /path/to/parameter --region us-east-1
```

### Availability Zone Issues

**Problem:** `Not enough availability zones`

**Solution:**
```yaml
# Use fewer AZs or check region support
parameters:
  AvailabilityZones: $[taskcat_genaz_2]  # Instead of 3+

# Or exclude problematic AZs
project:
  az_blacklist:
    - use1-az3  # Exclude specific AZ
```

## CloudFormation Issues

### Stack Creation Fails

**Problem:** Stack fails to create resources

**Solution:**
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name stack-name

# Validate template
aws cloudformation validate-template --template-body file://template.yaml

# Test with minimal parameters
taskcat test run --no-delete  # Keep resources for debugging
```

### Resource Limits Exceeded

**Problem:** `LimitExceeded` errors

**Solution:**
```bash
# Check service limits
aws service-quotas list-service-quotas --service-code ec2

# Use different regions
# Request limit increases
# Use smaller instance types for testing
```

### Dependency Issues

**Problem:** Resources created in wrong order

**Solution:**
```yaml
# Add explicit dependencies in template
Resources:
  MyInstance:
    Type: AWS::EC2::Instance
    DependsOn: MySecurityGroup
    Properties:
      SecurityGroupIds:
        - !Ref MySecurityGroup
```

## Test Execution Issues

### Tests Hang or Timeout

**Problem:** Tests never complete

**Solution:**
```bash
# Check CloudFormation console for stuck stacks
# Increase timeout (if available)
# Cancel and retry
taskcat test run --no-delete  # Debug mode

# Clean up manually if needed
aws cloudformation delete-stack --stack-name stuck-stack
```

### Cleanup Failures

**Problem:** Resources not deleted after test

**Solution:**
```bash
# Check for deletion protection
aws cloudformation describe-stacks --stack-name stack-name

# Manual cleanup
aws cloudformation delete-stack --stack-name stack-name

# Force delete if needed (be careful!)
aws s3 rm s3://bucket-name --recursive
aws s3 rb s3://bucket-name
```

### Multiple Region Failures

**Problem:** Some regions fail, others succeed

**Solution:**
```yaml
# Test regions individually
tests:
  us-east-1-test:
    template: template.yaml
    regions:
      - us-east-1
      
  us-west-2-test:
    template: template.yaml
    regions:
      - us-west-2

# Check region-specific issues
# Verify service availability
# Check quotas per region
```

## Performance Issues

### Slow Test Execution

**Problem:** Tests take too long

**Solution:**
```yaml
# Reduce regions for testing
regions:
  - us-east-1  # Single region for development

# Use smaller resources
parameters:
  InstanceType: t3.nano  # Smallest for testing
  
# Parallel execution (if supported)
# Use simpler templates for initial testing
```

### S3 Upload Issues

**Problem:** Template upload fails

**Solution:**
```bash
# Check S3 permissions
aws s3 ls s3://your-bucket/

# Verify bucket exists and is accessible
aws s3 mb s3://your-taskcat-bucket

# Check file sizes (CloudFormation limits)
ls -lh templates/
```

## Debugging Techniques

### Enable Verbose Logging

```bash
# Run with debug output
taskcat test run --debug

# Check log files
ls -la taskcat_outputs/
cat taskcat_outputs/taskcat.log
```

### Validate Before Testing

```bash
# Lint configuration
taskcat lint

# Validate templates
aws cloudformation validate-template --template-body file://template.yaml

# Test parameters
taskcat test run --no-delete
```

### Incremental Testing

```yaml
# Start simple
tests:
  minimal:
    template: minimal-template.yaml
    regions:
      - us-east-1
    parameters:
      InstanceType: t3.nano

# Add complexity gradually
tests:
  basic:
    template: basic-template.yaml
    # Add more parameters
    
  advanced:
    template: full-template.yaml
    # Full configuration
```

## Common Error Messages

### `Template format error`

**Cause:** Invalid CloudFormation template syntax

**Solution:**
- Validate YAML/JSON syntax
- Check CloudFormation template structure
- Verify resource types and properties

### `Parameter validation failed`

**Cause:** Parameter doesn't match template constraints

**Solution:**
- Check parameter types in template
- Verify allowed values
- Ensure required parameters are provided

### `Stack already exists`

**Cause:** Previous test didn't clean up

**Solution:**
```bash
# Delete existing stack
aws cloudformation delete-stack --stack-name existing-stack

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name existing-stack
```

### `Bucket already exists`

**Cause:** S3 bucket name conflict

**Solution:**
```yaml
# Use dynamic bucket names
parameters:
  BucketName: $[taskcat_autobucket]  # Always unique
  # Not: BucketName: my-static-bucket-name
```

## Getting Help

### Check Documentation

- [Configuration Guide](configuration.md)
- [Dynamic Values](dynamic-values.md)
- [Schema Reference](schema.md)

### Community Resources

- [GitHub Issues](https://github.com/aws-ia/taskcat/issues)
- [AWS re:Post](https://repost.aws/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/taskcat)

### Debug Information to Collect

When reporting issues, include:

```bash
# System information
taskcat --version
python --version
aws --version

# Configuration
cat .taskcat.yml

# Error logs
cat taskcat_outputs/taskcat.log

# CloudFormation events
aws cloudformation describe-stack-events --stack-name failing-stack
```

### Create Minimal Reproduction

```yaml
# Minimal .taskcat.yml that reproduces the issue
project:
  name: debug-issue
  regions:
    - us-east-1

tests:
  reproduce-issue:
    template: minimal-template.yaml
    parameters:
      TestParameter: test-value
```

This troubleshooting guide covers the most common issues encountered when using taskcat. For additional help, consult the community resources or create a detailed issue report with the debugging information outlined above.

# Troubleshooting Guide

Having issues with taskcat? This comprehensive troubleshooting guide will help you diagnose and resolve common problems.

## 🔍 Quick Diagnostics

Before diving into specific issues, run these diagnostic commands:

```bash
# Check taskcat version and installation
taskcat --version

# Validate your configuration
taskcat test run --dry-run

# Check AWS credentials
aws sts get-caller-identity

# Verify CloudFormation permissions
aws cloudformation describe-stacks --region us-east-1
```

## 🚨 Common Issues

### Installation Problems

#### Python Version Issues
**Problem**: `taskcat requires Python 3.8 or higher`

**Solution**:
```bash
# Check Python version
python3 --version

# Install Python 3.8+ if needed
# macOS: brew install python@3.9
# Ubuntu: sudo apt-get install python3.9
# Windows: Download from python.org
```

#### Permission Denied During Installation
**Problem**: `Permission denied` when running `pip install taskcat`

**Solution**:
```bash
# Install for current user only
pip install --user taskcat

# Or use virtual environment (recommended)
python3 -m venv taskcat-env
source taskcat-env/bin/activate  # Linux/macOS
# taskcat-env\Scripts\activate   # Windows
pip install taskcat
```

### AWS Credentials Issues

#### No Credentials Found
**Problem**: `Unable to locate credentials`

**Solutions**:
```bash
# Option 1: Configure AWS CLI
aws configure

# Option 2: Set environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1

# Option 3: Use IAM roles (for EC2/Lambda)
# Attach appropriate IAM role to your instance
```

#### Insufficient Permissions
**Problem**: `Access Denied` errors during testing

**Required Permissions**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "s3:*",
                "iam:PassRole",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "ec2:Describe*",
                "ssm:GetParameter*",
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "*"
        }
    ]
}
```

### Configuration Issues

#### Invalid YAML Syntax
**Problem**: `YAML syntax error in .taskcat.yml`

**Solution**:
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('.taskcat.yml'))"

# Common issues:
# - Incorrect indentation (use spaces, not tabs)
# - Missing colons after keys
# - Unquoted special characters
```

**Example of correct syntax**:
```yaml
project:
  name: my-project          # ✅ Correct
  regions:
    - us-east-1            # ✅ Correct indentation
    - us-west-2

tests:
  test1:
    template: templates/main.yaml  # ✅ Quoted path with spaces
    parameters:
      Key: "Value with spaces"     # ✅ Quoted value
```

#### Template Not Found
**Problem**: `Template file not found`

**Solutions**:
```bash
# Check file path
ls -la templates/

# Use relative paths from project root
template: templates/main.yaml  # ✅ Correct
template: ./templates/main.yaml # ✅ Also correct
template: /full/path/main.yaml  # ❌ Avoid absolute paths
```

### Template Issues

#### CloudFormation Validation Errors
**Problem**: Template fails CloudFormation validation

**Debugging Steps**:
```bash
# Validate template syntax
aws cloudformation validate-template \
  --template-body file://templates/main.yaml

# Check for common issues:
# - Invalid resource types
# - Missing required properties
# - Circular dependencies
# - Invalid parameter constraints
```

#### Parameter Issues
**Problem**: `Parameter validation failed`

**Common Causes**:
- Missing required parameters
- Invalid parameter values
- Type mismatches
- Constraint violations

**Solution**:
```yaml
# Ensure all required parameters are provided
tests:
  test1:
    template: templates/main.yaml
    parameters:
      RequiredParam1: value1
      RequiredParam2: value2
```

### Pseudo-Parameter Issues

#### Git Branch Parameter Fails
**Problem**: `Project root is not a git repository`

**Solution**:
```bash
# Initialize git repository
git init
git add .
git commit -m "Initial commit"

# Or avoid using $[taskcat_git_branch]
```

#### Availability Zone Issues
**Problem**: `Not enough availability zones in region`

**Solutions**:
```yaml
# Reduce number of AZs requested
parameters:
  AvailabilityZones: $[taskcat_genaz_2]  # Instead of _3 or higher

# Or test in regions with more AZs
project:
  regions:
    - us-east-1  # Has 6 AZs
    - us-west-2  # Has 4 AZs
```

#### SSM Parameter Not Found
**Problem**: `Parameter /path/to/param not found`

**Solutions**:
```bash
# Verify parameter exists
aws ssm get-parameter --name "/path/to/param" --region us-east-1

# Check parameter path spelling
parameters:
  AMI: $[taskcat_ssm_/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2]
```

### Deployment Issues

#### Stack Creation Fails
**Problem**: CloudFormation stack creation fails

**Debugging Steps**:
1. Check CloudFormation console for detailed error messages
2. Review stack events for failure points
3. Validate resource limits and quotas
4. Check for naming conflicts

```bash
# View stack events
aws cloudformation describe-stack-events \
  --stack-name your-stack-name \
  --region us-east-1
```

#### Resource Limits Exceeded
**Problem**: `LimitExceeded` errors

**Solutions**:
- Check AWS service limits
- Use different instance types
- Test in fewer regions simultaneously
- Clean up unused resources

#### Timeout Issues
**Problem**: Stack creation times out

**Solutions**:
```yaml
# Increase timeout in template
Resources:
  MyResource:
    Type: AWS::EC2::Instance
    CreationPolicy:
      ResourceSignal:
        Timeout: PT15M  # 15 minutes
```

### Performance Issues

#### Slow Test Execution
**Problem**: Tests take too long to complete

**Optimization Strategies**:
```yaml
# Test in fewer regions initially
project:
  regions:
    - us-east-1  # Start with one region

# Use smaller instance types
parameters:
  InstanceType: t3.nano  # Faster launch times

# Parallel execution (default)
# taskcat runs tests in parallel automatically
```

#### Memory Issues
**Problem**: taskcat runs out of memory

**Solutions**:
```bash
# Increase available memory
# For Docker: docker run -m 4g taskcat

# Reduce concurrent tests
# Split large test suites into smaller batches
```

## 🔧 Advanced Debugging

### Enable Debug Logging
```bash
# Enable verbose logging
taskcat test run --debug

# Save logs to file
taskcat test run --debug > taskcat-debug.log 2>&1
```

### Template Preprocessing Debug
```bash
# See processed templates
taskcat test run --keep-failed

# Check generated parameters
ls taskcat_outputs/
cat taskcat_outputs/*/parameters.json
```

### AWS CloudTrail Integration
```bash
# Monitor AWS API calls
aws logs filter-log-events \
  --log-group-name CloudTrail/taskcatTesting \
  --start-time $(date -d '1 hour ago' +%s)000
```

## 🆘 Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide**
2. **Search existing GitHub issues**
3. **Enable debug logging**
4. **Gather system information**:
   ```bash
   taskcat --version
   python3 --version
   aws --version
   uname -a  # Linux/macOS
   ```

### Where to Get Help

#### GitHub Issues
- **Bug Reports**: [Create an issue](https://github.com/aws-ia/taskcat/issues/new?template=bug_report.md)
- **Feature Requests**: [Request a feature](https://github.com/aws-ia/taskcat/issues/new?template=feature_request.md)
- **Questions**: [Ask a question](https://github.com/aws-ia/taskcat/discussions)

#### Community Support
- **AWS re:Post**: Tag questions with `taskcat`
- **Stack Overflow**: Use the `taskcat` tag
- **AWS Forums**: CloudFormation section

### Creating Effective Bug Reports

Include this information:

```markdown
## Environment
- taskcat version: X.X.X
- Python version: X.X.X
- Operating System: OS name and version
- AWS CLI version: X.X.X

## Configuration
```yaml
# Your .taskcat.yml (remove sensitive data)
```

## Template
```yaml
# Minimal template that reproduces the issue
```

## Error Output
```
# Full error message and stack trace
```

## Steps to Reproduce
1. Step one
2. Step two
3. Step three
```

## 📚 Additional Resources

- [AWS CloudFormation User Guide](https://docs.aws.amazon.com/cloudformation/)
- [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [taskcat GitHub Repository](https://github.com/aws-ia/taskcat)
- [AWS Quick Start Program](https://aws.amazon.com/quickstart/)

## 🔄 Still Having Issues?

If this guide doesn't resolve your issue:

1. **Search GitHub Issues**: Someone might have encountered the same problem
2. **Check AWS Service Health**: Verify AWS services are operational
3. **Try a Minimal Example**: Isolate the problem with a simple test case
4. **Contact Support**: Create a detailed GitHub issue with all relevant information

Remember: The more information you provide, the faster we can help resolve your issue! 🚀

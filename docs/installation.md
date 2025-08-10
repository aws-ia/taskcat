# Installation

Get taskcat installed and running on your system quickly and easily.

## Prerequisites

Before installing taskcat, ensure you have:

- **Python 3.8+** - taskcat requires Python 3.8 or higher
- **AWS CLI** - Configured with appropriate credentials  
- **Git** - For cloning repositories and version control
- **AWS Permissions** - See [Required Permissions](#required-permissions)

## Installation Methods

### PyPI (Recommended)

Install taskcat from the Python Package Index:

```bash
pip install taskcat
```

### Development Installation

Install the latest development version:

```bash
pip install git+https://github.com/aws-ia/taskcat.git
```

### Docker

Use the official Docker image:

```bash
# Pull the image
docker pull public.ecr.aws/aws-ia/taskcat:latest

# Run taskcat in a container
docker run -it --rm \
  -v $(pwd):/workspace \
  -v ~/.aws:/root/.aws \
  public.ecr.aws/aws-ia/taskcat:latest --help
```

## Verification

Verify your installation:

```bash
# Check version
taskcat --version

# Display help
taskcat --help

# Test basic functionality
taskcat lint --help
```

## AWS Configuration

### Configure Credentials

taskcat uses AWS credentials from your environment. Choose one method:

#### AWS CLI Configuration
```bash
aws configure
```

#### Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

#### IAM Roles (Recommended)
For EC2 instances or Lambda functions, taskcat automatically uses attached IAM roles.

### Required Permissions

taskcat requires these AWS permissions:

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
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

!!! warning "Security Note"
    These are broad permissions for testing. In production, use more restrictive policies based on your specific templates.

## Troubleshooting

### Common Issues

**Python version error:**
```bash
# Check Python version
python --version
# or
python3 --version
```

**Permission denied:**
```bash
# Install with user flag
pip install --user taskcat
```

**AWS credentials not found:**
```bash
# Verify AWS configuration
aws sts get-caller-identity
```

### Getting Help

- Check the [Troubleshooting Guide](troubleshooting.md)
- Visit our [GitHub Issues](https://github.com/aws-ia/taskcat/issues)
- Join the community discussions

## Next Steps

Once installed, proceed to:

1. [Quick Start](quickstart.md) - Run your first test
2. [Configuration](configuration.md) - Learn configuration options
3. [Dynamic Values](dynamic-values.md) - Master runtime parameters

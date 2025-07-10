# Installation Guide

Get taskcat installed and running on your system with our comprehensive installation guide.

## Prerequisites

Before installing taskcat, ensure you have:

- **Python 3.8+**: taskcat requires Python 3.8 or higher
- **AWS CLI**: Configured with appropriate credentials
- **Git**: For cloning repositories and version control
- **Sufficient AWS Permissions**: See [Required Permissions](#required-permissions)

## Installation Methods

### Method 1: PyPI (Recommended)

The easiest way to install taskcat is via PyPI:

```bash
pip install taskcat
```

For the latest development version:

```bash
pip install --upgrade taskcat
```

### Method 2: From Source

For development or the latest features:

```bash
git clone https://github.com/aws-ia/taskcat.git
cd taskcat
pip install -e .
```

### Method 3: Docker

Use our pre-built Docker images:

```bash
docker pull public.ecr.aws/aws-ia/taskcat:latest
docker run -it --rm -v $(pwd):/workspace taskcat --help
```

## Verification

Verify your installation:

```bash
taskcat --version
taskcat --help
```

## AWS Configuration

### Configure AWS Credentials

taskcat uses AWS credentials from your environment. Configure using:

#### AWS CLI
```bash
aws configure
```

#### Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

#### IAM Roles (Recommended for EC2/Lambda)
taskcat automatically uses IAM roles when running on AWS services.

### Required Permissions

taskcat requires the following AWS permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "s3:*",
                "iam:*",
                "ec2:Describe*",
                "ssm:GetParameter*",
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "*"
        }
    ]
}
```

## Next Steps

Once installed, continue to the [Quick Start Guide](quickstart.md) to run your first test.

## Troubleshooting

### Common Issues

**Python version too old:**
```bash
python3 --version  # Should be 3.8+
```

**Permission denied:**
```bash
pip install --user taskcat
```

**AWS credentials not found:**
```bash
aws configure list
```

For more help, see our [Troubleshooting Guide](../support/troubleshooting.md).

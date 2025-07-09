#!/bin/bash
#
# taskcat Documentation Generator Script
#
# This script automates the generation of taskcat documentation using MkDocs with
# Material theme. It provides options for local preview, building, and deployment.
#
# Usage:
#     ./gendocs.sh [OPTIONS]
#
# Options:
#     --preview, -p    Start local development server for preview
#     --build, -b      Build documentation for production
#     --deploy, -d     Deploy to GitHub Pages
#     --clean, -c      Clean build artifacts
#     --install, -i    Install documentation dependencies
#     --help, -h       Show this help message
#
# Examples:
#     ./gendocs.sh --preview     # Preview locally at http://localhost:8000
#     ./gendocs.sh --build       # Build static site to ./site/
#     ./gendocs.sh --deploy      # Deploy to GitHub Pages
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Documentation configuration
DOCS_DIR="$PROJECT_ROOT/docs"
SITE_DIR="$PROJECT_ROOT/site"
MKDOCS_CONFIG="$PROJECT_ROOT/mkdocs.yml"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python and pip
check_python() {
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    if ! command_exists pip3; then
        print_error "pip3 is required but not installed"
        exit 1
    fi
    
    print_status "Python $(python3 --version) detected"
}

# Function to install documentation dependencies
install_deps() {
    print_status "Installing documentation dependencies..."
    
    # Create requirements file for docs with enhanced packages
    cat > "$PROJECT_ROOT/docs-requirements.txt" << EOF
mkdocs>=1.5.0
mkdocs-material>=9.4.0
mkdocstrings[python]>=0.23.0
mkdocs-gen-files>=0.5.0
mkdocs-literate-nav>=0.6.0
mkdocs-section-index>=0.3.0
mkdocs-minify-plugin>=0.7.0
mkdocs-git-revision-date-localized-plugin>=1.2.0
pymdown-extensions>=10.0.0
pillow>=10.0.0
cairosvg>=2.7.0
EOF
    
    pip3 install -r "$PROJECT_ROOT/docs-requirements.txt"
    print_success "Documentation dependencies installed"
}

# Function to create MkDocs configuration
create_mkdocs_config() {
    print_status "Creating MkDocs configuration..."
    
    cat > "$MKDOCS_CONFIG" << 'EOF'
site_name: taskcat Documentation
site_description: AWS CloudFormation Template Testing Tool
site_author: taskcat Team
site_url: https://aws-ia.github.io/taskcat/

repo_name: aws-ia/taskcat
repo_url: https://github.com/aws-ia/taskcat
edit_uri: edit/main/docs/

theme:
  name: material
  palette:
    # Palette toggle for light mode
    - scheme: default
      primary: blue
      accent: orange
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    # Palette toggle for dark mode
    - scheme: slate
      primary: blue
      accent: orange
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.path
    - navigation.top
    - search.highlight
    - search.share
    - toc.integrate
    - content.code.copy
    - content.code.annotate
  icon:
    repo: fontawesome/brands/github
  logo: assets/images/tcat.png
  favicon: assets/images/tcat.png

plugins:
  - search:
      lang: en
  - gen-files:
      scripts:
        - docs/gen_ref_pages.py
  - literate-nav:
      nav_file: SUMMARY.md
  - section-index
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google
            show_source: true
            show_root_heading: true
            show_root_toc_entry: false
            merge_init_into_class: true
            separate_signature: true
            show_signature_annotations: true

markdown_extensions:
  - abbr
  - admonition
  - attr_list
  - def_list
  - footnotes
  - md_in_html
  - toc:
      permalink: true
  - pymdownx.arithmatex:
      generic: true
  - pymdownx.betterem:
      smart_enable: all
  - pymdownx.caret
  - pymdownx.details
  - pymdownx.emoji:
      emoji_generator: !!python/name:materialx.emoji.to_svg
      emoji_index: !!python/name:materialx.emoji.twemoji
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.keys
  - pymdownx.magiclink:
      repo_url_shorthand: true
      user: aws-ia
      repo: taskcat
  - pymdownx.mark
  - pymdownx.smartsymbols
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.tasklist:
      custom_checkbox: true
  - pymdownx.tilde

nav:
  - Home: index.md
  - Getting Started:
    - Installation: installation.md
    - Quick Start: quickstart.md
    - Configuration: configuration.md
  - User Guide:
    - Template Testing: user-guide/template-testing.md
    - Multi-Region Testing: user-guide/multi-region.md
    - Parameter Overrides: user-guide/parameter-overrides.md
    - Pseudo Parameters: user-guide/pseudo-parameters.md
  - API Reference: reference/
  - Examples:
    - Basic Usage: examples/basic.md
    - Advanced Scenarios: examples/advanced.md
  - Contributing: contributing.md

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/aws-ia/taskcat
    - icon: fontawesome/brands/python
      link: https://pypi.org/project/taskcat/

copyright: Copyright &copy; 2023 Amazon Web Services
EOF
    
    print_success "MkDocs configuration created"
}

# Function to create documentation structure
create_docs_structure() {
    print_status "Creating comprehensive documentation structure..."
    
    # Create all necessary directories
    mkdir -p "$DOCS_DIR"/{getting-started,user-guide,examples,support,overrides}
    mkdir -p "$DOCS_DIR/assets"/{images,css,js}
    
    # Download taskcat logo if not present
    if [ ! -f "$DOCS_DIR/assets/images/tcat.png" ]; then
        print_status "Downloading taskcat logo..."
        curl -o "$DOCS_DIR/assets/images/tcat.png" https://raw.githubusercontent.com/aws-ia/taskcat/main/assets/docs/images/tcat.png
        if [ $? -eq 0 ]; then
            print_success "taskcat logo downloaded successfully"
        else
            print_warning "Failed to download taskcat logo, using placeholder"
        fi
    fi
    
    # Copy existing documentation files if they exist
    if [ -f "$PROJECT_ROOT/docs/usage/GENERAL_USAGE.md" ]; then
        print_status "Preserving existing usage documentation..."
        # Usage docs are already in place
    fi
    
    if [ -f "$PROJECT_ROOT/docs/usage/PSUEDO_PARAMETERS.md" ]; then
        print_status "Preserving enhanced pseudo-parameters documentation..."
        # Already updated with comprehensive content
    fi
    
    if [ -f "$PROJECT_ROOT/docs/usage/PARAMETER_OVERRIDES.md" ]; then
        print_status "Preserving parameter overrides documentation..."
        # Already in place
    fi
    
    # Create enhanced installation guide
    cat > "$DOCS_DIR/getting-started/installation.md" << 'EOF'
# Installation Guide

Get TaskCat installed and running on your system with our comprehensive installation guide.

## Prerequisites

Before installing TaskCat, ensure you have:

- **Python 3.8+**: TaskCat requires Python 3.8 or higher
- **AWS CLI**: Configured with appropriate credentials
- **Git**: For cloning repositories and version control
- **Sufficient AWS Permissions**: See [Required Permissions](#required-permissions)

## Installation Methods

### Method 1: PyPI (Recommended)

The easiest way to install TaskCat is via PyPI:

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

TaskCat uses AWS credentials from your environment. Configure using:

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
TaskCat automatically uses IAM roles when running on AWS services.

### Required Permissions

TaskCat requires the following AWS permissions:

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
EOF

    # Create quick start guide
    cat > "$DOCS_DIR/getting-started/quickstart.md" << 'EOF'
# Quick Start Guide

Get up and running with TaskCat in just a few minutes! This guide will walk you through creating and running your first TaskCat test.

## Step 1: Create a Simple Template

First, let's create a basic CloudFormation template to test:

```yaml
# templates/simple-s3.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Simple S3 bucket for TaskCat testing'

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

## Step 2: Create TaskCat Configuration

Create a TaskCat configuration file:

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

TaskCat will:
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

TaskCat performed these actions:

1. **Template Processing**: Replaced pseudo-parameters with actual values
2. **Multi-Region Deployment**: Created CloudFormation stacks in us-east-1 and us-west-2
3. **Validation**: Verified successful deployment and resource creation
4. **Reporting**: Generated comprehensive HTML and JSON reports
5. **Cleanup**: Automatically deleted test resources

## Next Steps

Now that you've run your first test, explore:

- [Configuration Guide](configuration.md) - Advanced configuration options
- [Pseudo-Parameters](../usage/PSUEDO_PARAMETERS.md) - Dynamic parameter generation
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

Congratulations! You've successfully run your first TaskCat test. 🎉
EOF

    # Create configuration guide
    cat > "$DOCS_DIR/getting-started/configuration.md" << 'EOF'
# Configuration Guide

Learn how to configure TaskCat for your specific testing needs with comprehensive configuration options.

## Configuration File Structure

TaskCat uses YAML configuration files (`.taskcat.yml`) with this structure:

```yaml
project:
  name: string                    # Project name
  regions: [list]                 # AWS regions to test
  s3_bucket: string              # Optional: Custom S3 bucket
  s3_key_prefix: string          # Optional: S3 key prefix
  
tests:
  test-name:                     # Test identifier
    template: string             # Path to CloudFormation template
    parameters: {}               # Parameter overrides
    regions: [list]              # Optional: Test-specific regions
    
global:
  parameters: {}                 # Global parameter overrides
```

## Project Configuration

### Basic Project Settings

```yaml
project:
  name: my-cloudformation-project
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
```

### Advanced Project Settings

```yaml
project:
  name: enterprise-infrastructure
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
    - ap-southeast-1
  s3_bucket: my-custom-taskcat-bucket
  s3_key_prefix: testing/templates/
  tags:
    Environment: Testing
    Project: TaskCat
    Owner: DevOps-Team
```

## Test Configuration

### Single Test

```yaml
tests:
  basic-test:
    template: templates/main.yaml
    parameters:
      InstanceType: t3.micro
      Environment: test
```

### Multiple Tests

```yaml
tests:
  small-deployment:
    template: templates/small.yaml
    parameters:
      InstanceType: t3.micro
      
  large-deployment:
    template: templates/large.yaml
    parameters:
      InstanceType: m5.xlarge
      
  multi-az-test:
    template: templates/multi-az.yaml
    regions:
      - us-east-1
      - us-west-2
    parameters:
      AvailabilityZones: $[taskcat_genaz_3]
```

## Parameter Management

### Global Parameters

Parameters that apply to all tests:

```yaml
global:
  parameters:
    KeyPairName: my-keypair
    VpcCidr: 10.0.0.0/16
    Environment: testing

tests:
  test1:
    template: templates/app.yaml
    # Inherits global parameters
  test2:
    template: templates/db.yaml
    # Also inherits global parameters
```

### Test-Specific Parameters

Override global parameters for specific tests:

```yaml
global:
  parameters:
    Environment: testing
    InstanceType: t3.micro

tests:
  production-test:
    template: templates/app.yaml
    parameters:
      Environment: production    # Overrides global
      InstanceType: m5.large    # Overrides global
```

### Pseudo-Parameters

Use dynamic parameters for flexible testing:

```yaml
tests:
  dynamic-test:
    template: templates/app.yaml
    parameters:
      # Generate random values
      DatabasePassword: $[taskcat_genpass_16S]
      S3Bucket: $[taskcat_autobucket]
      
      # Use current context
      Region: $[taskcat_current_region]
      ProjectName: $[taskcat_project_name]
      
      # Generate availability zones
      AvailabilityZones: $[taskcat_genaz_2]
      
      # Reference other parameters
      PasswordConfirm: $[taskcat_getval_DatabasePassword]
```

## Region Configuration

### Project-Level Regions

All tests use these regions by default:

```yaml
project:
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
```

### Test-Specific Regions

Override regions for specific tests:

```yaml
project:
  regions:
    - us-east-1
    - us-west-2

tests:
  global-test:
    template: templates/global.yaml
    regions:
      - us-east-1
      - us-west-2
      - eu-west-1
      - ap-southeast-1
      
  us-only-test:
    template: templates/us-specific.yaml
    regions:
      - us-east-1
      - us-west-2
```

## Advanced Configuration

### Custom S3 Configuration

```yaml
project:
  name: my-project
  s3_bucket: my-custom-bucket-${AWS::Region}
  s3_key_prefix: taskcat-tests/
  s3_object_acl: private
```

### Authentication Configuration

```yaml
project:
  auth:
    us-east-1: profile1
    us-west-2: profile2
    default: default-profile
```

### Template Processing

```yaml
project:
  template:
    transforms:
      - AWS::Serverless-2016-10-31
    capabilities:
      - CAPABILITY_IAM
      - CAPABILITY_NAMED_IAM
```

## Configuration Examples

### Microservices Architecture

```yaml
project:
  name: microservices-platform
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1

global:
  parameters:
    Environment: testing
    VpcCidr: 10.0.0.0/16

tests:
  vpc-infrastructure:
    template: templates/vpc.yaml
    
  application-tier:
    template: templates/app-tier.yaml
    parameters:
      InstanceType: t3.medium
      
  database-tier:
    template: templates/db-tier.yaml
    parameters:
      DBInstanceClass: db.t3.micro
      
  monitoring:
    template: templates/monitoring.yaml
    regions:
      - us-east-1  # Only deploy monitoring in primary region
```

### Multi-Environment Testing

```yaml
project:
  name: multi-env-app
  regions:
    - us-east-1
    - us-west-2

tests:
  development:
    template: templates/app.yaml
    parameters:
      Environment: dev
      InstanceType: t3.micro
      
  staging:
    template: templates/app.yaml
    parameters:
      Environment: staging
      InstanceType: t3.small
      
  production:
    template: templates/app.yaml
    parameters:
      Environment: prod
      InstanceType: m5.large
```

## Best Practices

### 1. Use Meaningful Names
```yaml
tests:
  vpc-with-public-subnets:     # ✅ Descriptive
    template: templates/vpc.yaml
    
  test1:                       # ❌ Not descriptive
    template: templates/vpc.yaml
```

### 2. Organize Parameters
```yaml
global:
  parameters:
    # Common across all tests
    Environment: testing
    Owner: devops-team
    
tests:
  web-tier:
    parameters:
      # Specific to this test
      InstanceType: t3.medium
      MinSize: 2
      MaxSize: 10
```

### 3. Use Pseudo-Parameters
```yaml
parameters:
  # ✅ Dynamic and flexible
  DatabasePassword: $[taskcat_genpass_16S]
  S3Bucket: $[taskcat_autobucket]
  
  # ❌ Static and potentially conflicting
  DatabasePassword: hardcoded-password
  S3Bucket: my-static-bucket-name
```

## Validation

Validate your configuration:

```bash
# Check configuration syntax
taskcat test run --dry-run

# Lint CloudFormation templates
taskcat lint

# Generate configuration schema
taskcat schema
```

## Next Steps

- [Pseudo-Parameters Guide](../usage/PSUEDO_PARAMETERS.md)
- [Parameter Overrides](../usage/PARAMETER_OVERRIDES.md)
- [Advanced Examples](../examples/advanced.md)
EOF

    print_success "Comprehensive documentation structure created"
}

# Function to build documentation
build_docs() {
    print_status "Building documentation..."
    
    if [ ! -f "$MKDOCS_CONFIG" ]; then
        print_error "MkDocs configuration not found. Run with --install first."
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    mkdocs build --clean
    
    print_success "Documentation built successfully"
    print_status "Static site available in: $SITE_DIR"
}

# Function to serve documentation locally
serve_docs() {
    print_status "Starting local documentation server..."
    
    if [ ! -f "$MKDOCS_CONFIG" ]; then
        print_error "MkDocs configuration not found. Run with --install first."
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    print_success "Documentation server starting..."
    print_status "Open your browser to: http://localhost:8000"
    print_status "Press Ctrl+C to stop the server"
    
    mkdocs serve --dev-addr=localhost:8000
}

# Function to deploy to GitHub Pages
deploy_docs() {
    print_status "Deploying documentation to GitHub Pages..."
    
    if [ ! -f "$MKDOCS_CONFIG" ]; then
        print_error "MkDocs configuration not found. Run with --install first."
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    mkdocs gh-deploy --clean
    
    print_success "Documentation deployed to GitHub Pages"
}

# Function to clean build artifacts
clean_docs() {
    print_status "Cleaning documentation build artifacts..."
    
    if [ -d "$SITE_DIR" ]; then
        rm -rf "$SITE_DIR"
        print_status "Removed $SITE_DIR"
    fi
    
    if [ -f "$PROJECT_ROOT/docs-requirements.txt" ]; then
        rm "$PROJECT_ROOT/docs-requirements.txt"
        print_status "Removed docs-requirements.txt"
    fi
    
    print_success "Clean completed"
}

# Function to show help
show_help() {
    cat << 'EOF'
taskcat Documentation Generator

Usage: ./gendocs.sh [OPTIONS]

Options:
    --preview, -p    Start local development server for preview
    --build, -b      Build documentation for production
    --deploy, -d     Deploy to GitHub Pages
    --clean, -c      Clean build artifacts
    --install, -i    Install documentation dependencies and setup
    --help, -h       Show this help message

Examples:
    ./gendocs.sh --install     # First time setup
    ./gendocs.sh --preview     # Preview locally at http://localhost:8000
    ./gendocs.sh --build       # Build static site to ./site/
    ./gendocs.sh --deploy      # Deploy to GitHub Pages
    ./gendocs.sh --clean       # Clean build artifacts

Workflow:
    1. Run --install to set up dependencies and configuration
    2. Run --preview to develop and test documentation locally
    3. Run --build to create production build
    4. Run --deploy to publish to GitHub Pages
EOF
}

# Main script logic
main() {
    case "${1:-}" in
        --preview|-p)
            check_python
            serve_docs
            ;;
        --build|-b)
            check_python
            build_docs
            ;;
        --deploy|-d)
            check_python
            deploy_docs
            ;;
        --clean|-c)
            clean_docs
            ;;
        --install|-i)
            check_python
            install_deps
            create_mkdocs_config
            create_docs_structure
            print_success "Documentation setup completed!"
            print_status "Next steps:"
            print_status "  1. Run './gendocs.sh --preview' to preview locally"
            print_status "  2. Edit documentation files in the docs/ directory"
            print_status "  3. Run './gendocs.sh --deploy' to publish to GitHub Pages"
            ;;
        --help|-h|"")
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"

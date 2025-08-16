# taskcat Documentation

<div class="hero">
  <div class="hero-logo">
    <img src="assets/images/tcat.png" alt="taskcat Logo" width="64" height="64">
  </div>
  <h1>taskcat</h1>
  <p>Test your AWS CloudFormation templates across multiple regions with confidence. taskcat automates the deployment and validation of your infrastructure as code, ensuring your templates work reliably everywhere.</p>
  <div class="hero-buttons">
    <a href="getting-started/quickstart/" class="hero-button">Get Started</a>
    <a href="getting-started/installation/" class="hero-button hero-button--secondary">Install Now</a>
  </div>
</div>

## What is taskcat?

taskcat is a powerful testing framework for AWS CloudFormation templates that helps you validate your infrastructure as code across multiple AWS regions simultaneously. Built by AWS Solutions Architects, taskcat ensures your templates are robust, reliable, and ready for production deployment.

<div class="feature-grid">
  <div class="feature-card multi-region">
    <h3>Multi-Region Testing</h3>
    <p>Deploy and test your CloudFormation templates across multiple AWS regions simultaneously to ensure global compatibility and resilience.</p>
  </div>
  
  <div class="feature-card automation">
    <h3>Automated Validation</h3>
    <p>Comprehensive automated testing with detailed pass/fail reporting, stack validation, and resource verification.</p>
  </div>
  
  <div class="feature-card dynamic-values">
    <h3>Dynamic Values</h3>
    <p>Runtime-evaluated parameters that pull values from your AWS environment, generate random data, and provide context-aware configurations.</p>
  </div>
  
  <div class="feature-card reporting">
    <h3>Rich Reporting</h3>
    <p>Generate detailed HTML reports with deployment status, logs, and visual dashboards to track your testing results.</p>
  </div>
  
  <div class="feature-card integration">
    <h3>CI/CD Integration</h3>
    <p>Seamlessly integrate with your continuous integration pipelines using GitHub Actions, Jenkins, or AWS CodePipeline.</p>
  </div>
</div>

## Key Features

### 🚀 **Quick Setup**
Get started in minutes with simple configuration files and intuitive CLI commands.

### 🌍 **Global Testing**
Test across all AWS regions or specify custom region sets for your deployment requirements.

### ⚡ **Dynamic Values**
Runtime-evaluated parameters that can pull values from your AWS environment, generate random data, and provide context-aware configurations for flexible testing.

### 📊 **Comprehensive Reports**
Generate detailed reports with stack outputs, resource details, and deployment timelines.

### 🔒 **Security First**
Built-in security best practices with IAM role management and secure parameter handling.

## Quick Start Example

<div class="code-example">
  <div class="code-example-header">Basic taskcat Configuration</div>
  
=== "taskcat.yml"

    ```yaml
    project:
      name: my-cloudformation-project
      regions:
        - us-east-1
        - us-west-2
        - eu-west-1

    tests:
      default:
        template: templates/main.yaml
        parameters:
          InstanceType: t3.micro
          AvailabilityZones: $[taskcat_genaz_2]
          DatabasePassword: $[taskcat_genpass_16S]
          S3Bucket: $[taskcat_autobucket]
    ```

=== "Advanced Configuration"

    ```yaml
    project:
      name: enterprise-app
      regions:
        - us-east-1
        - us-west-2
        - eu-west-1

    global:
      parameters:
        ProjectName: $[taskcat_project_name]
        Environment: production

    tests:
      vpc-infrastructure:
        template: templates/vpc.yaml
        parameters:
          VpcName: $[taskcat_project_name]-vpc-$[taskcat_current_region]
          AvailabilityZones: $[taskcat_genaz_3]
          
      database-tier:
        template: templates/rds.yaml
        parameters:
          DBInstanceId: $[taskcat_project_name]-db-$[taskcat_genuuid]
          MasterPassword: $[taskcat_secretsmanager_prod/db/password]
          DBSubnetGroup: $[taskcat_getval_VpcName]-db-subnets
          
      application-tier:
        template: templates/app.yaml
        parameters:
          AppName: $[taskcat_project_name]-app
          S3Bucket: $[taskcat_autobucket]
          ApiKey: $[taskcat_ssm_/app/api/key]
          CurrentRegion: $[taskcat_current_region]
    ```

=== "CLI Commands"

    ```bash
    # Install taskcat
    pip install taskcat

    # Initialize a new project
    taskcat init

    # Test your templates
    taskcat test run

    # Generate reports
    taskcat test run --output-directory ./reports
    ```

=== "GitHub Actions"

    ```yaml
    name: taskcat Tests
    on: [push, pull_request]
    
    jobs:
      taskcat:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
          - name: Setup Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.9'
          - name: Install taskcat
            run: pip install taskcat
          - name: Run Tests
            run: taskcat test run
    ```
</div>

## Why Choose taskcat?

<div class="callout info">
<strong>🏆 AWS Solutions Architecture Team Approved</strong><br>
taskcat is developed and maintained by the AWS Solutions Architecture team and is used internally by AWS for testing CloudFormation templates in AWS Quick Starts and Solutions.
</div>

### **Proven at Scale**
- Used by AWS internally for testing hundreds of CloudFormation templates
- Powers the AWS Quick Start program with over 150+ tested solutions
- Trusted by enterprises worldwide for production deployments

### **Developer Friendly**
- Simple YAML configuration
- Intuitive command-line interface
- Rich documentation and examples
- Active community support

### **Enterprise Ready**
- Multi-account testing support
- Advanced parameter management
- Comprehensive logging and reporting
- Integration with AWS services

## Getting Help

<div class="feature-grid">
  <div class="aws-card">
    <div class="aws-card-header">📚 Documentation</div>
    <p>Comprehensive guides, tutorials, and API reference to help you get the most out of taskcat.</p>
    <a href="getting-started/" class="md-button">Browse Docs</a>
  </div>
  
  <div class="aws-card">
    <div class="aws-card-header">💬 Community</div>
    <p>Join our community discussions, ask questions, and share your taskcat experiences.</p>
    <a href="support/community/" class="md-button">Join Community</a>
  </div>
  
  <div class="aws-card">
    <div class="aws-card-header">🐛 Issues</div>
    <p>Report bugs, request features, or contribute to the taskcat project on GitHub.</p>
    <a href="https://github.com/aws-ia/taskcat/issues" class="md-button">Report Issue</a>
  </div>
</div>

## What's New

<div class="callout success">
<strong>🎉 Latest Updates</strong><br>
Check out the latest features including enhanced pseudo-parameters, improved AWS service integrations, and better CI/CD support.
</div>

### Recent Improvements
- **Enhanced Pseudo-Parameters**: New AWS service integrations and improved parameter handling
- **Better Error Reporting**: More detailed error messages and troubleshooting guidance  
- **Performance Optimizations**: Faster template processing and parallel execution
- **Extended AWS Service Support**: Support for latest AWS services and regions

## Next Steps

Ready to start testing your CloudFormation templates? Here's your path forward:

1. **[Install taskcat](getting-started/installation.md)** - Get taskcat up and running in minutes
2. **[Quick Start Guide](getting-started/quickstart.md)** - Run your first test
3. **[Configuration Guide](getting-started/configuration.md)** - Learn about advanced configuration options
4. **[Dynamic Values](usage/DYNAMIC_VALUES.md)** - Master runtime-evaluated parameters and AWS environment integration
5. **[Examples](examples/)** - Explore real-world usage scenarios

<div class="callout info">
<strong>💡 Pro Tip</strong><br>
Start with the Quick Start guide to run your first test, then explore Dynamic Values to make your templates flexible with runtime-evaluated parameters that pull from your AWS environment.
</div>

---

<div style="text-align: center; margin: 2rem 0; color: #687078;">
  <p><strong>taskcat</strong> - Making CloudFormation testing simple, reliable, and scalable.</p>
  <p>Built with ❤️ by the AWS Solutions Architecture Team</p>
</div>

# Getting Started with taskcat

Welcome to taskcat! This section will get you up and running with AWS CloudFormation template testing in minutes.

## What You'll Learn

<div class="feature-grid">
  <div class="feature-card">
    <h3>📦 Installation</h3>
    <p>Multiple installation methods including pip, Docker, and from source.</p>
    <a href="installation/" class="md-button">Install taskcat</a>
  </div>
  
  <div class="feature-card">
    <h3>🚀 Quick Start</h3>
    <p>Run your first test in under 5 minutes with our step-by-step guide.</p>
    <a href="quickstart/" class="md-button">Quick Start</a>
  </div>
  
  <div class="feature-card">
    <h3>⚙️ Configuration</h3>
    <p>Master taskcat configuration for advanced testing scenarios.</p>
    <a href="configuration/" class="md-button">Configure</a>
  </div>
</div>

## Learning Path

Follow this recommended path to master taskcat:

### 1. **Installation** (5 minutes)
Get taskcat installed on your system with your preferred method.

### 2. **Quick Start** (10 minutes)
Create and run your first test to understand the basics.

### 3. **Configuration** (20 minutes)
Learn about advanced configuration options and best practices.

### 4. **Dynamic Values** (15 minutes)
Master runtime-evaluated parameters for flexible testing.

## Prerequisites

Before you begin, ensure you have:

- **AWS Account** with appropriate permissions
- **Python 3.8+** installed on your system
- **AWS CLI** configured with credentials
- **Basic CloudFormation knowledge**

## Quick Installation

```bash
# Install taskcat via pip
pip install taskcat

# Verify installation
taskcat --version

# Get help
taskcat --help
```

## Your First Test

```yaml
# .taskcat.yml
project:
  name: my-first-test
  regions:
    - us-east-1

tests:
  basic:
    template: template.yaml
    parameters:
      BucketName: $[taskcat_autobucket]
```

```bash
# Run the test
taskcat test run
```

## Need Help?

- 📚 **[Documentation](../usage/GENERAL_USAGE.md)** - Comprehensive guides
- 💬 **[Community](../support/troubleshooting.md)** - Get help from other users
- 🐛 **[Issues](https://github.com/aws-ia/taskcat/issues)** - Report bugs or request features

Ready to begin? Start with [Installation](installation.md)!

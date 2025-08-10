# API Reference

Complete reference for taskcat's Python API and command-line interface.

## Command Line Interface

### Main Commands

#### `taskcat test run`

Execute taskcat tests with specified configuration.

```bash
taskcat test run [OPTIONS]
```

**Options:**
- `--config-file, -c` - Path to configuration file (default: `.taskcat.yml`)
- `--regions` - Comma-separated list of regions to test
- `--tests` - Comma-separated list of tests to run
- `--no-delete` - Skip resource cleanup (for debugging)
- `--project-root` - Path to project root directory
- `--output-directory` - Directory for test outputs

**Examples:**
```bash
# Run all tests
taskcat test run

# Run specific test
taskcat test run --tests vpc-test

# Run in specific regions
taskcat test run --regions us-east-1,us-west-2

# Keep resources for debugging
taskcat test run --no-delete
```

#### `taskcat lint`

Validate taskcat configuration and CloudFormation templates.

```bash
taskcat lint [OPTIONS]
```

**Options:**
- `--config-file, -c` - Path to configuration file
- `--templates` - Validate CloudFormation templates only
- `--strict` - Enable strict validation mode

**Examples:**
```bash
# Lint configuration
taskcat lint

# Lint specific file
taskcat lint -c custom.yml

# Validate templates only
taskcat lint --templates
```

#### `taskcat test list`

List available tests in configuration.

```bash
taskcat test list [OPTIONS]
```

**Options:**
- `--config-file, -c` - Path to configuration file

#### `taskcat upload`

Upload templates and artifacts to S3.

```bash
taskcat upload [OPTIONS]
```

**Options:**
- `--config-file, -c` - Path to configuration file
- `--bucket` - S3 bucket name
- `--key-prefix` - S3 key prefix

### Global Options

Available for all commands:

- `--help, -h` - Show help message
- `--version` - Show version information
- `--debug` - Enable debug logging
- `--quiet, -q` - Suppress output

## Python API

### Core Classes

#### `TaskCat`

Main class for programmatic access to taskcat functionality.

```python
from taskcat import TaskCat

# Initialize TaskCat
tc = TaskCat(
    config_file='.taskcat.yml',
    project_root='/path/to/project',
    regions=['us-east-1', 'us-west-2']
)

# Run tests
results = tc.test()

# Get test results
for test_name, result in results.items():
    print(f"Test {test_name}: {result.status}")
```

#### `Config`

Configuration management class.

```python
from taskcat.config import Config

# Load configuration
config = Config.create(
    project_root='/path/to/project',
    config_file='.taskcat.yml'
)

# Access configuration
print(config.project.name)
print(config.tests.keys())
```

#### `TestResult`

Test execution result container.

```python
# Access test results
result = tc.test()['test-name']

print(result.status)        # PASS, FAIL, or ERROR
print(result.region)        # AWS region
print(result.stack_name)    # CloudFormation stack name
print(result.outputs)       # Stack outputs
print(result.events)        # CloudFormation events
```

### Configuration Objects

#### `ProjectConfig`

Project-level configuration.

```python
project = config.project

print(project.name)                    # Project name
print(project.regions)                 # Default regions
print(project.parameters)              # Default parameters
print(project.s3_bucket)              # S3 bucket
print(project.lambda_source_path)      # Lambda source path
```

#### `TestConfig`

Individual test configuration.

```python
test = config.tests['test-name']

print(test.template)        # Template path
print(test.parameters)      # Test parameters
print(test.regions)         # Test regions
print(test.auth)           # Authentication settings
```

### Utility Functions

#### Parameter Generation

```python
from taskcat._template_params import ParamGen

# Generate parameters
param_gen = ParamGen(
    project_root='/path/to/project',
    param_dict={'Password': '$[taskcat_genpass_16S]'},
    bucket_name='my-bucket',
    region='us-east-1',
    boto_client=boto3.client('cloudformation'),
    project_name='my-project',
    test_name='my-test'
)

# Access generated parameters
generated_params = param_gen.results
print(generated_params['Password'])  # Generated password
```

#### Template Processing

```python
from taskcat._cfn_lint import CfnLint

# Validate CloudFormation template
linter = CfnLint()
results = linter.lint_file('template.yaml')

for result in results:
    print(f"{result.level}: {result.message}")
```

### Exception Handling

#### `TaskCatException`

Base exception for taskcat errors.

```python
from taskcat.exceptions import TaskCatException

try:
    tc = TaskCat(config_file='invalid.yml')
    results = tc.test()
except TaskCatException as e:
    print(f"TaskCat error: {e}")
```

#### Common Exceptions

- `TaskCatException` - Base taskcat exception
- `ConfigError` - Configuration validation errors
- `TemplateError` - CloudFormation template errors
- `RegionError` - AWS region-related errors

### Advanced Usage

#### Custom Hooks

```python
from taskcat import TaskCat

class CustomTaskCat(TaskCat):
    def pre_test_hook(self, test_name, region):
        """Execute before each test"""
        print(f"Starting test {test_name} in {region}")
        
    def post_test_hook(self, test_name, region, result):
        """Execute after each test"""
        print(f"Test {test_name} completed: {result.status}")

# Use custom class
tc = CustomTaskCat(config_file='.taskcat.yml')
results = tc.test()
```

#### Parallel Execution

```python
import concurrent.futures
from taskcat import TaskCat

def run_test(test_config):
    tc = TaskCat(config_file=test_config)
    return tc.test()

# Run tests in parallel
configs = ['test1.yml', 'test2.yml', 'test3.yml']

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(run_test, config) for config in configs]
    results = [future.result() for future in futures]
```

#### Custom Parameter Generation

```python
from taskcat._template_params import ParamGen

class CustomParamGen(ParamGen):
    def custom_function(self):
        """Custom parameter generation function"""
        return "custom-value"
        
    def transform_parameter(self):
        # Call parent method
        super().transform_parameter()
        
        # Add custom transformations
        if '$[custom_function]' in self.param_value:
            self.param_value = self.param_value.replace(
                '$[custom_function]', 
                self.custom_function()
            )
```

## Integration Examples

### CI/CD Integration

```python
#!/usr/bin/env python3
"""CI/CD integration script"""

import sys
from taskcat import TaskCat
from taskcat.exceptions import TaskCatException

def main():
    try:
        # Initialize TaskCat
        tc = TaskCat(
            config_file='.taskcat.yml',
            regions=['us-east-1', 'us-west-2']
        )
        
        # Run tests
        results = tc.test()
        
        # Check results
        failed_tests = [
            name for name, result in results.items() 
            if result.status != 'PASS'
        ]
        
        if failed_tests:
            print(f"Failed tests: {failed_tests}")
            sys.exit(1)
        else:
            print("All tests passed!")
            sys.exit(0)
            
    except TaskCatException as e:
        print(f"TaskCat error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Custom Reporting

```python
import json
from taskcat import TaskCat

def generate_custom_report(results):
    """Generate custom test report"""
    report = {
        'summary': {
            'total_tests': len(results),
            'passed': sum(1 for r in results.values() if r.status == 'PASS'),
            'failed': sum(1 for r in results.values() if r.status == 'FAIL'),
        },
        'details': []
    }
    
    for test_name, result in results.items():
        report['details'].append({
            'test_name': test_name,
            'status': result.status,
            'region': result.region,
            'stack_name': result.stack_name,
            'duration': result.duration,
            'outputs': result.outputs
        })
    
    return report

# Run tests and generate report
tc = TaskCat(config_file='.taskcat.yml')
results = tc.test()
report = generate_custom_report(results)

# Save report
with open('test-report.json', 'w') as f:
    json.dump(report, f, indent=2)
```

## Environment Variables

TaskCat recognizes these environment variables:

- `AWS_PROFILE` - AWS profile to use
- `AWS_REGION` - Default AWS region
- `TASKCAT_CONFIG_FILE` - Default configuration file path
- `TASKCAT_PROJECT_ROOT` - Default project root directory
- `TASKCAT_DEBUG` - Enable debug logging (set to `1`)

## Return Codes

Command-line return codes:

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Template validation error
- `4` - Test execution error

## Version Information

```bash
# Get version
taskcat --version

# Get detailed version info
taskcat --version --verbose
```

```python
# Get version programmatically
import taskcat
print(taskcat.__version__)
```

For more detailed API documentation, see the inline docstrings and type hints in the source code.

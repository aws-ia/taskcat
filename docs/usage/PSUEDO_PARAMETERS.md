# Pseudo-Parameters

To increase the flexibility of taskcat, we've built-in support for **pseudo-parameters** that are dynamically replaced at runtime with actual values. These parameters allow you to create more flexible and reusable CloudFormation templates without hardcoding environment-specific values.

## How Pseudo-Parameters Work

Pseudo-parameters use the syntax `$[parameter_name]` and are processed by taskcat before the CloudFormation template is deployed. They are replaced with actual values based on the current test context, AWS environment, or generated data.

## Available Pseudo-Parameters

### 🪣 S3 Bucket Parameters

| Pseudo-Parameter | Example Value | Description |
|------------------|---------------|-------------|
| `$[taskcat_autobucket]` | `taskcat-tag-sample-taskcat-project-5fba6597` | Creates a unique S3 bucket for the test. The bucket is automatically created and managed by taskcat. |
| `$[taskcat_autobucket_prefix]` | `taskcat-tag-sample-taskcat-project` | Returns the prefix portion of the auto-generated bucket name (without the random suffix). |

### 🌍 Availability Zone Parameters

| Pseudo-Parameter | Example Value | Description |
|------------------|---------------|-------------|
| `$[taskcat_genaz_1]` | `"us-east-1a"` | Returns a single available Availability Zone in the current region. |
| `$[taskcat_genaz_2]` | `"us-east-1a,us-east-1b"` | Returns two available Availability Zones in the current region, comma-separated. |
| `$[taskcat_genaz_3]` | `"us-east-1a,us-east-1b,us-east-1c"` | Returns three available Availability Zones in the current region, comma-separated. |
| `$[taskcat_genaz_N]` | `"us-east-1a,us-east-1b,..."` | Returns N available Availability Zones (replace N with desired number). |
| `$[taskcat_gensingleaz_1]` | `"us-east-1a"` | Returns a single AZ by index (1-based). Useful for consistent AZ selection. |
| `$[taskcat_gensingleaz_2]` | `"us-east-1b"` | Returns the second AZ in the region. |

### 🔐 Password Generation Parameters

| Pseudo-Parameter | Example Value | Description |
|------------------|---------------|-------------|
| `$[taskcat_genpass_8A]` | `tI8zN3iX` | Generates an 8-character alphanumeric password (letters + numbers). |
| `$[taskcat_genpass_12A]` | `vGceIP8EHCmn` | Generates a 12-character alphanumeric password. |
| `$[taskcat_genpass_8S]` | `mA5@cB5!` | Generates an 8-character password with special characters. |
| `$[taskcat_genpass_16S]` | `kL9#nM2$pQ4&rS6*` | Generates a 16-character password with special characters. |

**Password Types:**
- **A** = Alphanumeric (letters + numbers)
- **S** = Special characters (letters + numbers + symbols: `!#$&{*:[=,]-_%@+`)
- **Length** = Any number from 1-99

### 🎲 Random Data Generation

| Pseudo-Parameter | Example Value | Description |
|------------------|---------------|-------------|
| `$[taskcat_random-string]` | `yysuawpwubvotiqgwjcu` | Generates a 20-character random lowercase string. |
| `$[taskcat_random-numbers]` | `56188163597280820763` | Generates a 20-digit random number string. |
| `$[taskcat_genuuid]` | `1c2e3483-2c99-45bb-801d-8af68a3b907b` | Generates a UUID (Universally Unique Identifier). |

### 📍 Context Information Parameters

| Pseudo-Parameter | Example Value | Description |
|------------------|---------------|-------------|
| `$[taskcat_current_region]` | `"us-east-2"` | Returns the AWS region where the current test is being executed. |
| `$[taskcat_project_name]` | `"my-example-project"` | Returns the name of the taskcat project being tested. |
| `$[taskcat_test_name]` | `"cluster-with-windows-ad"` | Returns the name of the specific test being executed. |
| `$[taskcat_git_branch]` | `"main"` | Returns the current Git branch name (requires project to be a Git repository). |

### 🔗 Parameter Reference

| Pseudo-Parameter | Example Value | Description |
|------------------|---------------|-------------|
| `$[taskcat_getval_ParameterName]` | `tI8zN3iX` | Retrieves the value of another parameter. Useful for password confirmation fields. |

### ☁️ AWS Service Integration

| Pseudo-Parameter | Example Value | Description |
|------------------|---------------|-------------|
| `$[taskcat_ssm_/path/to/parameter]` | `ami-12345678` | Retrieves a value from AWS Systems Manager Parameter Store. |
| `$[taskcat_secretsmanager_SecretName]` | `{"username":"admin","password":"secret"}` | Retrieves a secret value from AWS Secrets Manager using secret name or ARN. |

### 🔧 Legacy/Deprecated Parameters

| Pseudo-Parameter | Example Value | Description |
|------------------|---------------|-------------|
| `$[taskcat_getkeypair]` | `cikey` | Returns a default keypair name. **Deprecated** - use parameter overrides instead. |
| `$[taskcat_getlicensebucket]` | `override_this` | Placeholder for license bucket. **Deprecated** - use parameter overrides instead. |
| `$[taskcat_getmediabucket]` | `override_this` | Placeholder for media bucket. **Deprecated** - use parameter overrides instead. |

## Usage Examples

### Basic Configuration (taskcat.yml)
```yaml
project:
  name: my-cloudformation-project
  regions:
    - us-east-1
    - us-west-2

tests:
  default:
    template: templates/main.yaml
    parameters:
      InstanceType: t3.micro
      AvailabilityZones: $[taskcat_genaz_2]
      DatabasePassword: $[taskcat_genpass_16S]
      ConfirmPassword: $[taskcat_getval_DatabasePassword]
      S3Bucket: $[taskcat_autobucket]
      CurrentRegion: $[taskcat_current_region]
      ProjectName: $[taskcat_project_name]
      RandomIdentifier: $[taskcat_genuuid]
```

### Runtime Transformation
**Before (in taskcat.yml):**
```yaml
parameters:
  InstanceType: t3.micro
  AvailabilityZones: $[taskcat_genaz_2]
  DatabasePassword: $[taskcat_genpass_16S]
  ConfirmPassword: $[taskcat_getval_DatabasePassword]
  S3Bucket: $[taskcat_autobucket]
  AMIId: $[taskcat_ssm_/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2]
```

**After (passed to CloudFormation):**
```yaml
parameters:
  InstanceType: t3.micro
  AvailabilityZones: "us-east-1a,us-east-1b"
  DatabasePassword: "kL9#nM2$pQ4&rS6*"
  ConfirmPassword: "kL9#nM2$pQ4&rS6*"
  S3Bucket: "taskcat-my-project-a1b2c3d4"
  AMIId: "ami-0abcdef1234567890"
```

## Advanced Usage

### SSM Parameter Store Integration
```yaml
parameters:
  LatestAMI: $[taskcat_ssm_/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2]
  DatabaseEndpoint: $[taskcat_ssm_/myapp/prod/database/endpoint]
  APIKey: $[taskcat_ssm_/myapp/prod/api/key]
```

### Secrets Manager Integration
```yaml
parameters:
  DatabaseCredentials: $[taskcat_secretsmanager_prod/database/credentials]
  APISecret: $[taskcat_secretsmanager_arn:aws:secretsmanager:us-east-1:123456789012:secret:MySecret-AbCdEf]
```

### Multi-AZ Deployment
```yaml
parameters:
  PublicSubnetAZs: $[taskcat_genaz_2]      # For public subnets
  PrivateSubnetAZs: $[taskcat_genaz_2]     # Same AZs for private subnets
  DatabaseAZ1: $[taskcat_gensingleaz_1]    # Specific AZ for primary DB
  DatabaseAZ2: $[taskcat_gensingleaz_2]    # Specific AZ for standby DB
```

## Best Practices

1. **Use Consistent Naming**: Choose descriptive parameter names that clearly indicate their purpose.

2. **Password Security**: Always use `$[taskcat_genpass_XS]` for production passwords to include special characters.

3. **Parameter Reuse**: Use `$[taskcat_getval_ParameterName]` for password confirmation fields to ensure consistency.

4. **Region Awareness**: Use `$[taskcat_current_region]` when you need region-specific logic in your templates.

5. **AZ Planning**: Use `$[taskcat_genaz_N]` for resources that need multiple AZs, and `$[taskcat_gensingleaz_N]` for resources that need specific AZ placement.

6. **External Dependencies**: Use SSM and Secrets Manager pseudo-parameters for values that change between environments or contain sensitive data.

## Troubleshooting

### Common Issues

- **Git Branch Parameter**: `$[taskcat_git_branch]` requires the project to be in a Git repository
- **AZ Availability**: Some regions may not have enough AZs for high numbers (e.g., `$[taskcat_genaz_5]`)
- **SSM Permissions**: Ensure taskcat has permissions to read from Parameter Store and Secrets Manager
- **Parameter Dependencies**: When using `$[taskcat_getval_X]`, ensure the referenced parameter is defined in the same test

### Error Messages
- `"Project root is not a git repository"` - Use Git or avoid `$[taskcat_git_branch]`
- `"Not enough availability zones"` - Reduce the number in `$[taskcat_genaz_N]` or choose a different region
- `"Parameter not found"` - Check SSM parameter paths and permissions

# Examples

Explore real-world taskcat configurations and learn from practical implementations. These examples demonstrate best practices, advanced features, and common use cases.

## Quick Reference

<div class="feature-grid">
  <div class="feature-card">
    <h3>🚀 Basic Usage</h3>
    <p>Simple configurations to get you started with taskcat testing.</p>
    <a href="basic/" class="md-button">View Examples</a>
  </div>
  
  <div class="feature-card">
    <h3>⚡ Advanced Scenarios</h3>
    <p>Complex multi-tier applications and enterprise-grade configurations.</p>
    <a href="advanced/" class="md-button">Explore Advanced</a>
  </div>
</div>

## Featured Examples

### Multi-Region Web Application

```yaml
project:
  name: web-application
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
      
  web-tier:
    template: templates/web-tier.yaml
    parameters:
      ApplicationName: $[taskcat_project_name]-web
      InstanceType: t3.medium
      S3Bucket: $[taskcat_autobucket]
      SSLCertificate: $[taskcat_ssm_/ssl/certificate/arn]
```

### Serverless Application

```yaml
project:
  name: serverless-api
  regions:
    - us-east-1
    - us-west-2

tests:
  api-gateway:
    template: templates/api-gateway.yaml
    parameters:
      ApiName: $[taskcat_project_name]-api-$[taskcat_current_region]
      StageName: $[taskcat_test_name]
      
  lambda-functions:
    template: templates/lambda.yaml
    parameters:
      FunctionName: $[taskcat_project_name]-function
      Runtime: python3.9
      S3Bucket: $[taskcat_autobucket]
      DatabasePassword: $[taskcat_secretsmanager_prod/db/password]
```

### Database Cluster

```yaml
project:
  name: database-cluster
  regions:
    - us-east-1
    - us-west-2

tests:
  aurora-cluster:
    template: templates/aurora.yaml
    parameters:
      ClusterIdentifier: $[taskcat_project_name]-cluster-$[taskcat_genuuid]
      MasterUsername: admin
      MasterUserPassword: $[taskcat_genpass_32S]
      DatabaseName: $[taskcat_project_name]
      BackupRetentionPeriod: 7
      PreferredBackupWindow: "03:00-04:00"
      PreferredMaintenanceWindow: "sun:04:00-sun:05:00"
```

## Browse All Examples

- **[Basic Usage](basic.md)** - Simple, straightforward examples
- **[Advanced Scenarios](advanced.md)** - Complex, production-ready configurations

## Contributing Examples

Have a great taskcat configuration to share? We'd love to include it! Examples should:

- ✅ Follow taskcat best practices
- ✅ Include clear documentation
- ✅ Demonstrate real-world use cases
- ✅ Use Dynamic Values appropriately
- ✅ Be production-ready

Submit your examples via [GitHub Issues](https://github.com/aws-ia/taskcat/issues) or [Pull Requests](https://github.com/aws-ia/taskcat/pulls).

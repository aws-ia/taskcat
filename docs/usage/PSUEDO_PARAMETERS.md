To increase the flexibility of taskcat, we've built-in support for _psuedo-parameters_ that are transposed at runtime for actual values.

Following table describes the supported **psuedo-parameters**.

| Psuedo-Parameter | Example Value passed to the CloudFormation stack | Details |
| ------------- | ------------- | ------------- |
| `$[taskcat_autobucket]` | taskcat-tag-sample-taskcat-project-5fba6597 | _Note: The S3 Bucket is created_ |
| `$[taskcat_genaz_1]` | "us-east-1a"  | Fetches a single  Availability Zone within the region being launched in |
| `$[taskcat_genaz_2]` | "us-east-1a,us-east-1b"  | Fetches two AvailabilityZones within the region being launched in |
| `$[taskcat_genaz_3]` | "us-east-1a,us-east-1b,us-east-1c"  | Fetches three AvailabilityZones within the region being launched in |
| `$[taskcat_genpass_8A]`  | tI8zN3iX8 | An alphanumberic 8-charater random password. The length is customizable. |
| `$[taskcat_genpass_8S]`  | mA5@cB5! | An alphanumberic 8-charater random password. The length is customizable. |
| `$[taskcat_random-string]` | yysuawpwubvotiqgwjcu | Generates a random string |
| `$[taskcat_random-numbers]` | 56188163597280820763 | Generates random numbers. |
| `$[taskcat_genuuid]` | 1c2e3483-2c99-45bb-801d-8af68a3b907b | Generates a UUID |
| `$[taskcat_getval_MyAppPassword]` | _Dynamically generated password for the MyAppPassword parameter_ | Retreives another parameter value.|
|  $[taskcat_current_region] | "us-east-2" | Region the test is being prepared for |
|  $[taskcat_project_name] | "my-example-project" | Name of the project being tested |
|  $[taskcat_test_name] | "cluster-with-windows-ad" | Name of the test being tested |
|  $[taskcat_ssm_/path/to/ssm/parameter] | _SSM Parameter Value_ | Retreives values from SSM |
|  $[taskcat_secretsmanager_SecretNameOrARN] |_Value from SecretsManager_ |  Retreives a secret value from SecretsManager given an name or ARN|

#### From: (defined in taskcat.yaml')
```
     InstanceType: t2.small
     AvailablityZones: $[taskcat_genaz_2]
     RandomString: $[taskcat_random-string]
     RandomNumbers: $[taskcat_random-numbers]
     GenerateUUID: $[taskcat_genuuid]
     Password: $[taskcat_genpass_8A]
     PasswordConfirm: $[taskcat_getval_Password]
```

#### To: (At runtime passed to cloudformation API)
```
     InstanceType: t2.small
     AvailablityZones: us-east-1a: us-east1b
     RandomString: yysuawpwubvotiqgwjcu
     RandomNumbers: 56188163597280820763
     GenerateUUID: 1c2e3483-2c99-45bb-801d-8af68a3b907b
     Password: tI8zN3iX8
     PasswordConfirm: tI8zN3iX8
```

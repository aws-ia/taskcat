## TaskCat FAQ

### FAQ
Error: `botocore.exceptions.ClientError: An error occurred (IllegalLocationConstraintException) when calling the CreateBucket operation: The unspecified location constraint is incompatible for the region specific endpoint this request was sent to.`

Solution: Set your default region to `us-east-1`

For boto profile set the default to `us-east-1`

```
[profile default]
output = json
region = us-east-1```


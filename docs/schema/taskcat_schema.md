* `general` *type:* `object` General configuration settings.
  * `auth` *type:* `object` AWS authentication section
    * `<AUTH_NAME>` *type:* `object` 
  * `parameters` *type:* `object` Parameter key-values to pass to CloudFormation, parameters provided in global config take precedence
    * `<PARAMETER_NAME>` *type:* `object` 
  * `posthooks` *type:* `array` hooks to execute after executing tests
  * `prehooks` *type:* `array` hooks to execute prior to executing tests
  * `regions` *type:* `array` List of AWS regions
  * `s3_bucket` *type:* `string` Name of S3 bucket to upload project to, if left out a bucket will be auto-generated
  * `s3_regional_buckets` *type:* `boolean` Enable regional auto-buckets.
  * `tags` *type:* `object` Tags to apply to CloudFormation template
    * `<TAG_NAME>` *type:* `object` 
* `project` *type:* `object` Project specific configuration section
  * `auth` *type:* `object` AWS authentication section
    * `<AUTH_NAME>` *type:* `object` 
  * `az_blacklist` *type:* `array` List of Availablilty Zones ID's to exclude when generating availability zones
  * `build_submodules` *type:* `boolean` Build Lambda zips recursively for submodules, set to false to disable
  * `lambda_source_path` *type:* `string` Path relative to the project root containing Lambda zip files, default is 'lambda_functions/source'
  * `lambda_zip_path` *type:* `string` Path relative to the project root to place Lambda zip files, default is 'lambda_functions/zips'
  * `name` *type:* `string` Project name, used as s3 key prefix when uploading objects
  * `owner` *type:* `string` email address for project owner (not used at present)
  * `package_lambda` *type:* `boolean` Package Lambda functions into zips before uploading to s3, set to false to disable
  * `parameters` *type:* `object` Parameter key-values to pass to CloudFormation, parameters provided in global config take precedence
    * `<PARAMETER_NAME>` *type:* `object` 
  * `posthooks` *type:* `array` hooks to execute after executing tests
  * `prehooks` *type:* `array` hooks to execute prior to executing tests
  * `regions` *type:* `array` List of AWS regions
  * `role_name` *type:* `string` Role name to use when launching CFN Stacks.
  * `s3_bucket` *type:* `string` Name of S3 bucket to upload project to, if left out a bucket will be auto-generated
  * `s3_enable_sig_v2` *type:* `boolean` Enable (deprecated) sigv2 access to auto-generated buckets
  * `s3_object_acl` *type:* `string` ACL for uploaded s3 objects, defaults to 'private'
  * `s3_regional_buckets` *type:* `boolean` Enable regional auto-buckets.
  * `shorten_stack_name` *type:* `boolean` Shorten stack names generated for tests, set to true to enable
  * `tags` *type:* `object` Tags to apply to CloudFormation template
    * `<TAG_NAME>` *type:* `object` 
  * `template` *type:* `string` path to template file relative to the project config file path
* `tests` *type:* `object` 
  * `auth` *type:* `object` AWS authentication section
    * `<AUTH_NAME>` *type:* `object` 
  * `az_blacklist` *type:* `array` List of Availablilty Zones ID's to exclude when generating availability zones
  * `parameters` *type:* `object` Parameter key-values to pass to CloudFormation, parameters provided in global config take precedence
    * `<PARAMETER_NAME>` *type:* `object` 
  * `posthooks` *type:* `array` hooks to execute after executing tests
  * `prehooks` *type:* `array` hooks to execute prior to executing tests
  * `regions` *type:* `array` List of AWS regions
  * `role_name` *type:* `string` Role name to use when launching CFN Stacks.
  * `s3_bucket` *type:* `string` Name of S3 bucket to upload project to, if left out a bucket will be auto-generated
  * `s3_regional_buckets` *type:* `boolean` Enable regional auto-buckets.
  * `stack_name` *type:* `string` Cloudformation Stack Name
  * `stack_name_prefix` *type:* `string` Prefix to apply to generated CFN Stack Name
  * `stack_name_suffix` *type:* `string` Suffix to apply to generated CFN Stack Name
  * `tags` *type:* `object` Tags to apply to CloudFormation template
    * `<TAG_NAME>` *type:* `object` 
  * `template` *type:* `string` path to template file relative to the project config file path

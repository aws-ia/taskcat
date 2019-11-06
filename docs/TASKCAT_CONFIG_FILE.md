* `general` _General configuration settings._
    * `auth` _AWS authentication section_
        * `<AUTH_NAME>` 
    * `parameters` _Parameter key-values to pass to CloudFormation, parameters provided in global config take precedence_
        * `<PARAMETER_NAME>` 
    * `s3_bucket` _Name of S3 bucket to upload project to, if left out a bucket will be auto-generated_
    * `tags` _Tags to apply to CloudFormation template_
        * `<TAG_NAME>` 
* `project` _Project specific configuration section_
    * `auth` _AWS authentication section_
        * `<AUTH_NAME>` 
    * `az_blacklist` _List of Availablilty Zones ID's to exclude when generating availability zones_
    * `build_submodules` _Build Lambda zips recursively for submodules, set to false to disable_
    * `lambda_source_path` _Path relative to the project root containing Lambda zip files, default is 'lambda_functions/source'_
    * `lambda_zip_path` _Path relative to the project root to place Lambda zip files, default is 'lambda_functions/zips'_
    * `name` _Project name, used as s3 key prefix when uploading objects_
    * `owner` _email address for project owner (not used at present)_
    * `package_lambda` _Package Lambda functions into zips before uploading to s3, set to false to disable_
    * `parameters` _Parameter key-values to pass to CloudFormation, parameters provided in global config take precedence_
        * `<PARAMETER_NAME>` 
    * `regions` _List of AWS regions_
    * `s3_bucket` _Name of S3 bucket to upload project to, if left out a bucket will be auto-generated_
    * `s3_enable_sig_v2` _Enable (deprecated) sigv2 access to auto-generated buckets_
    * `s3_object_acl` _ACL for uploaded s3 objects, defaults to 'private'_
    * `tags` _Tags to apply to CloudFormation template_
        * `<TAG_NAME>` 
    * `template` _path to template file relative to the project config file path_
* `tests` 
    * `auth` _AWS authentication section_
        * `<AUTH_NAME>` 
    * `az_blacklist` _List of Availablilty Zones ID's to exclude when generating availability zones_
    * `parameters` _Parameter key-values to pass to CloudFormation, parameters provided in global config take precedence_
        * `<PARAMETER_NAME>` 
    * `regions` _List of AWS regions_
    * `s3_bucket` _Name of S3 bucket to upload project to, if left out a bucket will be auto-generated_
    * `tags` _Tags to apply to CloudFormation template_
        * `<TAG_NAME>` 
    * `template` _path to template file relative to the project config file path_

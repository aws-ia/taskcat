### Parameter overrides

Parameter Overrides were added to the taskcat to solve a couple of common problems. First, many
templates share common parameters that are unique to an AWS account, like a KeyPair name
or an S3 Bucket, overrides provided a way to store those centrally for all your projects.
Second, we didn't want to add sensitive data (usernames, passwords, tokens) to a git
repository. The idea was to store sensitive/unique data outside of a git repository, but still
execute a test using this data. To that end, *any parameter defined in the global config
will take precedence over the same parameter in a project-level config*.

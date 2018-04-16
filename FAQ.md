## TaskCat FAQ

### FAQ
#### CommonErrors

Error:

 
```
botocore.exceptions.ClientError: An error occurred (IllegalLocationConstraintException) when calling the CreateBucket operation: The unspecified location constraint is incompatible for the region specific endpoint this request was sent to.
```

Solution: Set your default region to `us-east-1`
For boto profile set the default to `us-east-1`
```
[profile default]
output = json
region = us-east-1

```
------
#### Critial failure with version all version below 2018.416.143234

Error: 
```
Traceback (most recent call last):
  File "/var/lib/jenkins/.local/bin/taskcat", line 58, in <module>
    main()
  File "/var/lib/jenkins/.local/bin/taskcat", line 22, in main
    tcat_instance.welcome('taskcat')
  File "/var/lib/jenkins/.local/lib/python3.6/site-packages/taskcat/stacker.py", line 2192, in welcome
    self.checkforupdate()
  File "/var/lib/jenkins/.local/lib/python3.6/site-packages/taskcat/stacker.py", line 2173, in checkforupdate
    if version in current_version:
TypeError: argument of type 'NoneType' is not iterable
```
> Due to infrastructure changes in https://pypi.org version check will fail for older versions :-( please update to latest version

Solution: (Get latest version)

> To upgrade pip version    [ pip install --upgrade taskcat]

> To upgrade docker version [ docker pull taskcat/taskcat ]


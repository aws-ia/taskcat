

# *AMIUpdater README*



## General Usage.

`amiupdater <flags> </path/to/template_directory|template_file>`

For a current list of options, see..

`amiupdater -h`

## Leveraging the Upstream Config File

### Upstream Mappings

By default, AMIUpdater uses a config file bundled with `taskcat`. This config file is populated with common AMI Mappings, such as *Amazon Linux AMI* and *Ubuntu Server 18.04*. To see all of the mappings available, [check out the config file](https://github.com/aws-quickstart/taskcat/blob/master/taskcat/cfg/amiupdater.cfg.yml)

To utilize these upstream mappings, simply leverage them in your templates.

_Note: The AMI IDs are here for example purposes. When first configuring the Mapping, you can filll them with arbitrary data._

- JSON

```json
{
(...)
    "Mappings": {
        "AWSAMIRegionMap": {
            "ap-northeast-1": {
                "AMZNLINUXHVM": "ami-00a5245b4816c38e6",
                "CENTOS7HVM": "ami-8e8847f1",
                "US1404HVM": "ami-0be9269b44d4b26c1",
                "US1604HVM": "ami-0d5e82481c5fd4ad5",
                "SLES15HVM": "ami-09161bc9964f46a98"
            },
            "ap-northeast-2": {
                "AMZNLINUXHVM": "ami-00dc207f8ba6dc919",
                "CENTOS7HVM": "ami-bf9c36d1",
                "US1404HVM": "ami-017332df4b882edd2",
                "US1604HVM": "ami-0507b772e2c9b8c15",
                "SLES15HVM": "ami-04ecb44b7d8e8d354"
            },
            "ap-south-1": {
                "AMZNLINUXHVM": "ami-0ad42f4f66f6c1cc9",
                "CENTOS7HVM": "ami-1780a878",
                "US1404HVM": "ami-09dcf5653a185f5df",
                "US1604HVM": "ami-0c8810f694cbe10ba",
                "SLES15HVM": "ami-025d8258d76079367"
            }
            (...)
            }
        }
    }
}
```

- YAML
```yaml
Mappings:
  AWSAMIRegionMap:
    ap-northeast-1:
      AMZNLINUXHVM: ami-00a5245b4816c38e6,
      CENTOS7HVM: ami-8e8847f1,
      US1404HVM: ami-0be9269b44d4b26c1,
      US1604HVM: ami-0d5e82481c5fd4ad5,
      SLES15HVM: ami-09161bc9964f46a98
    ap-northeast-2:
      AMZNLINUXHVM: ami-00dc207f8ba6dc919,
      CENTOS7HVM: ami-bf9c36d1,
      US1404HVM: ami-017332df4b882edd2,
      US1604HVM: ami-0507b772e2c9b8c15,
      SLES15HVM: ami-04ecb44b7d8e8d354
    ap-south-1:
      AMZNLINUXHVM: ami-0ad42f4f66f6c1cc9,
      CENTOS7HVM: ami-1780a878,
      US1404HVM: ami-09dcf5653a185f5df,
      US1604HVM: ami-0c8810f694cbe10ba,
      SLES15HVM: ami-025d8258d76079367
```
## Defining your own AMI Mappings

### Custom Config File
Functionally the same as the upstream config file, a local config file can be created and used in deployment pipelines.

For a full list of filters, available, [please see the AWS EC2 API Documentation](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeImages.html).

```yaml
# Owner-id must be in quotes
# Whereas, all other filters do not need quotes,
# because they are not in a number format

global:
  AMIs:
    CUSTOM_MAPPING_1:
      name: my_super_awesome_name-*
      owner-id: 1234567890
    CUSTOM_MAPPING_2:
      name: my_super_other_awesome_name ???? *
      owner-id: 1234567890
      architecture: arm64
```

### Template Inline Config
- JSON
```json
    "Metadata": {
        "AWSAMIRegionMap":{
            "Filters":{
                "<MAPPING_NAME>":{
                    "name":"my awesome AMI NAME",
                    "owner-id":"01234567890"
                }
            }
        }
```
- YAML
```yaml
Metadata:
  AWSAMIRegionMap:
    Filters:
      <MAPPING_NAME>:
        name: my awesome AMI NAME
        owner-id: 01234567890
```

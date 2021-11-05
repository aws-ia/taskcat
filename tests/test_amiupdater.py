import logging
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, sentinel

import requests

from taskcat._amiupdater import (
    REGION_REGEX,
    AMIUpdater,
    AMIUpdaterCommitNeededException,
    AMIUpdaterFatalException,
    Config as AUConfig,
    EC2FilterValue,
    RegionalCodename,
    Template,
    _construct_filters,
    _image_timestamp,
    build_codenames,
    query_codenames,
    reduce_api_results,
)
from taskcat._config import Config
from taskcat.exceptions import TaskCatException

logger = logging.getLogger("taskcat")


class TestAMIUpdater(unittest.TestCase):
    image_query_results = [
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-11-28T21:08:11.000Z",
            "ImageId": "ami-0080e4c5bc078760e",
            "ImageLocation": "amazon/amzn-ami-hvm-2018.03.0.20181129-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-01d81204beb02804b",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2018.03.0.20181129 x86_64 HVM gp2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2018.03.0.20181129-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-11-17T00:54:53.000Z",
            "ImageId": "ami-09479453c5cde9639",
            "ImageLocation": "amazon/amzn-ami-hvm-2018.03.0.20181116-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-01d81204beb02804b",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2018.03.0.20181116 x86_64 HVM gp2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2018.03.0.20181116-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-01-20T23:39:56.000Z",
            "ImageId": "ami-0b33d91d",
            "ImageLocation": "amazon/amzn-ami-hvm-2016.09.1.20170119-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-037f1f9e6c8ea4d65",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2016.09.1.20170119 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2016.09.1.20170119-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-08-11T02:30:11.000Z",
            "ImageId": "ami-0ff8a91507f77f867",
            "ImageLocation": "amazon/amzn-ami-hvm-2018.03.0.20180811-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-09ccbc8bc8ae7e4e9",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2018.03.0.20180811 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2018.03.0.20180811-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-05-08T18:06:53.000Z",
            "ImageId": "ami-14c5486b",
            "ImageLocation": "amazon/amzn-ami-hvm-2018.03.0.20180508-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-086b6d892c1edbbb2",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2018.03.0.20180508 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2018.03.0.20180508-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-03-07T06:59:59.000Z",
            "ImageId": "ami-1853ac65",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.09.1.20180307-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-01d62e4cbe7d0ddd0",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.09.1.20180307 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.09.1.20180307-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-04-02T05:53:05.000Z",
            "ImageId": "ami-22ce4934",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.03.0.20170401-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-0f2b695076fc43043",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.03.0.20170401 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.03.0.20170401-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-04-13T00:32:59.000Z",
            "ImageId": "ami-467ca739",
            "ImageLocation": "amazon/amzn-ami-hvm-2018.03.0.20180412-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-0699d9f527c416066",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2018.03.0.20180412 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2018.03.0.20180412-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-08-13T02:35:49.000Z",
            "ImageId": "ami-4fffc834",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.03.1.20170812-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-083018866ac6b06eb",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.03.1.20170812 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.03.1.20170812-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-01-03T19:04:51.000Z",
            "ImageId": "ami-5583d42f",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.09.1.20180103-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-084cb269d55295d27",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.09.1.20180103 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.09.1.20180103-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-11-20T22:29:51.000Z",
            "ImageId": "ami-55ef662f",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.09.1.20171120-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-055cf1cfc1dda99fe",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.09.1.20171120 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.09.1.20171120-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-11-03T23:21:01.000Z",
            "ImageId": "ami-6057e21a",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.09.1.20171103-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-089ba67abbc06b72a",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.09.1.20171103 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.09.1.20171103-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-06-17T21:56:53.000Z",
            "ImageId": "ami-643b1972",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.03.1.20170617-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-073f6727ec0ecc75b",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.03.1.20170617 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.03.1.20170617-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-10-01T09:13:01.000Z",
            "ImageId": "ami-8c1be5f6",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.09.0.20170930-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-080eb3cb2eda29974",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.09.0.20170930 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.09.0.20170930-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-01-15T19:14:50.000Z",
            "ImageId": "ami-97785bed",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.09.1.20180115-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-0fae6f7252388fc12",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.09.1.20180115 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.09.1.20180115-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2016-12-20T23:24:45.000Z",
            "ImageId": "ami-9be6f38c",
            "ImageLocation": "amazon/amzn-ami-hvm-2016.09.1.20161221-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-08a02ddbc6c4aecc0",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2016.09.1.20161221 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2016.09.1.20161221-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-06-23T23:35:49.000Z",
            "ImageId": "ami-a4c7edb2",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.03.1.20170623-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-0a9551026a7f15871",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.03.1.20170623 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.03.1.20170623-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2016-10-29T00:49:47.000Z",
            "ImageId": "ami-b73b63a0",
            "ImageLocation": "amazon/amzn-ami-hvm-2016.09.0.20161028-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-fe8a3c04",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2016.09.0.20161028 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2016.09.0.20161028-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2016-09-23T10:19:14.000Z",
            "ImageId": "ami-c481fad3",
            "ImageLocation": "amazon/amzn-ami-hvm-2016.09.0.20160923-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-2a2a8752",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2016.09.0.20160923 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2016.09.0.20160923-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2017-04-17T08:14:59.000Z",
            "ImageId": "ami-c58c1dd3",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.03.0.20170417-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-0120309fef406aa90",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.03.0.20170417 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.03.0.20170417-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-01-08T18:43:48.000Z",
            "ImageId": "ami-cb9ec1b1",
            "ImageLocation": "amazon/amzn-ami-hvm-2017.09.1.20180108-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-0e6d1e06d131ff774",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2017.09.1.20180108 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2017.09.1.20180108-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
        {
            "Architecture": "x86_64",
            "CreationDate": "2018-06-22T22:26:53.000Z",
            "ImageId": "ami-cfe4b2b0",
            "ImageLocation": "amazon/amzn-ami-hvm-2018.03.0.20180622-x86_64-gp2",
            "ImageType": "machine",
            "Public": "true",
            "OwnerId": "137112412989",
            "State": "available",
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": "true",
                        "SnapshotId": "snap-07ad5635357af8b3e",
                        "VolumeSize": 8,
                        "VolumeType": "gp2",
                        "Encrypted": "false",
                    },
                }
            ],
            "Description": "Amazon Linux AMI 2018.03.0.20180622 x86_64 HVM GP2",
            "EnaSupport": "true",
            "Hypervisor": "xen",
            "ImageOwnerAlias": "amazon",
            "Name": "amzn-ami-hvm-2018.03.0.20180622-x86_64-gp2",
            "RootDeviceName": "/dev/xvda",
            "RootDeviceType": "ebs",
            "SriovNetSupport": "simple",
            "VirtualizationType": "hvm",
        },
    ]
    ami_regex_pattern = re.compile("ami-([0-9a-z]{8}|[0-9a-z]{17})")

    def create_ephemeral_template_object(self, template_type="generic"):
        test_proj = (
            Path(__file__).parent / f"./data/update_ami/{template_type}"
        ).resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        templates = c.get_templates()
        return templates

    def test_query_codenames_raises(self):
        with self.assertRaises(AMIUpdaterFatalException):
            query_codenames([], {})

    def test_query_codenames(self):
        mock_boto_cache = Mock("taskcat._client_factory.Boto3Cache", autospec=True)()
        mock_client = Mock()
        mock_client.describe_images.return_value = {"Images": []}
        mock_boto_cache.client.return_value = mock_client
        mock_regional_codename = Mock(
            "taskcat._amiupdater.RegionalCodename", autospec=True
        )()
        mock_regional_codename.region = "us-east-1"
        mock_regional_codename.cn = "MOCK_CN"
        mock_regional_codename.filters = []
        actual = query_codenames(
            {mock_regional_codename}, {"us-east-1": mock_boto_cache}
        )
        expected = [{"api_results": [], "cn": "MOCK_CN", "region": "us-east-1"}]
        self.assertEqual(actual, expected)

    def test_reduce_api_results(self):
        sample_raw_results = [
            {
                "api_results": self.image_query_results,
                "cn": "MOCK_CN",
                "region": "us-east-1",
            }
        ]
        actual = reduce_api_results(sample_raw_results)
        result = actual[0]
        self.assertEqual(result.codename, "MOCK_CN")
        self.assertEqual(result.ami_id, "ami-0080e4c5bc078760e")
        self.assertEqual(result.creation_date, 1543439291)
        self.assertEqual(result.region, "us-east-1")

    def test__image_timestamp(self):
        sample_timestamp = "2018-06-22T22:26:53.000Z"
        expected_value = 1529706413
        actual_value = _image_timestamp(sample_timestamp)
        self.assertEqual(expected_value, actual_value)

    def test_construct_filters(self):
        example_config_obj = AUConfig
        example_config_obj.raw_dict = {
            "global": {
                "AMIs": {
                    "FOOBAR": {
                        "name": "amzn-ami-hvm-????.??.?.*-x86_64-gp2",
                        "owner-alias": "amazon",
                    }
                }
            }
        }
        expected = [
            EC2FilterValue("name", ["amzn-ami-hvm-????.??.?.*-x86_64-gp2"]),
            EC2FilterValue("owner-alias", ["amazon"]),
            EC2FilterValue("state", ["available"]),
        ]
        actual = _construct_filters("FOOBAR", example_config_obj)
        self.assertEqual(expected, actual)

    def test_build_codenames(self):
        example_tc_template = self.create_ephemeral_template_object()
        au_template = Template(example_tc_template["taskcat-json"])
        example_config_obj = AUConfig
        example_config_obj.raw_dict = {
            "global": {
                "AMIs": {
                    "AMZNLINUXHVM": {
                        "name": "amzn-ami-hvm-????.??.?.*-x86_64-gp2",
                        "owner-alias": "amazon",
                    }
                }
            }
        }
        expected = [
            RegionalCodename(
                region="us-east-1",
                cn="AMZNLINUXHVM",
                filters=[
                    EC2FilterValue("name", ["amzn-ami-hvm-????.??.?.*-x86_64-gp2"]),
                    EC2FilterValue("owner-alias", ["amazon"]),
                    EC2FilterValue("state", ["available"]),
                ],
            ),
            RegionalCodename(
                region="us-east-2",
                cn="AMZNLINUXHVM",
                filters=[
                    EC2FilterValue("name", ["amzn-ami-hvm-????.??.?.*-x86_64-gp2"]),
                    EC2FilterValue("owner-alias", ["amazon"]),
                    EC2FilterValue("state", ["available"]),
                ],
            ),
        ]
        actual = build_codenames(au_template, example_config_obj)
        _mocked_dt = datetime.now()
        for r1 in expected:
            r1._creation_dt = _mocked_dt
        for r2 in actual:
            r2._creation_dt = _mocked_dt
        self.assertEqual(expected, actual)

    def test_APIResults_lessthan_comparison_standard(self):
        from taskcat._amiupdater import APIResultsData

        instance_args = {
            "codename": "foo",
            "ami_id": "ami-12345abcde",
            "creation_date": datetime(2010, 1, 23),
            "region": "us-east-1",
            "custom_comparisons": False,
        }
        a = APIResultsData(**instance_args)

        instance_args["ami_id"] = "ami-abcde12345"
        instance_args["creation_date"] = datetime(2012, 1, 23)
        b = APIResultsData(**instance_args)

        with self.assertRaises(TypeError):
            a < b  # noqa: B015

    def test_APIResults_greaterthan_comparison_standard(self):
        from taskcat._amiupdater import APIResultsData

        APIResultsData.custom_comparisons = False
        instance_args = {
            "codename": "foo",
            "ami_id": "ami-12345abcde",
            "creation_date": datetime(2010, 1, 23),
            "region": "us-east-1",
            "custom_comparisons": False,
        }
        a = APIResultsData(**instance_args)

        instance_args["ami_id"] = "ami-abcde12345"
        instance_args["creation_date"] = datetime(2012, 1, 23)
        b = APIResultsData(**instance_args)

        with self.assertRaises(TypeError):
            a > b  # noqa: B015

    def test_APIResults_lessthan_comparison_custom(self):
        from taskcat._amiupdater import APIResultsData

        instance_args = {
            "codename": "foo",
            "ami_id": "ami-12345abcde",
            "creation_date": datetime(2010, 1, 23),
            "region": "us-east-1",
        }
        a = APIResultsData(**instance_args)

        instance_args["ami_id"] = "ami-abcde12345"
        instance_args["creation_date"] = datetime(2012, 1, 23)
        b = APIResultsData(**instance_args)

        self.assertTrue(a < b)

    def test_APIResults_greaterthan_comparison_custom(self):
        from taskcat._amiupdater import APIResultsData

        instance_args = {
            "codename": "foo",
            "ami_id": "ami-12345abcde",
            "creation_date": datetime(2012, 1, 23),
            "region": "us-east-1",
        }
        a = APIResultsData(**instance_args)

        instance_args["ami_id"] = "ami-abcde12345"
        instance_args["creation_date"] = datetime(2010, 1, 23)
        b = APIResultsData(**instance_args)

        self.assertTrue(a > b)

    def test_template_set_codename_ami(self):
        tc_template = self.create_ephemeral_template_object()["taskcat-json"]
        au_template = Template(underlying=tc_template)
        actual = au_template.set_codename_ami(
            "AMZNLINUXHVM", "us-east-1", "slkdfjskldfj"
        )
        self.assertTrue(actual)

    def test_template_write(self):
        mock_temp = Mock("taskcat._cfn.template.Template", autospec=True)()
        mock_temp.raw_template = "some-template-data"
        au_template = Template(underlying=mock_temp)
        au_template._ls = "some-other-data"
        au_template.write()
        mock_temp.write.assert_called_once()

    def test_template_set_codename_ami_no_region(self):
        tc_template = self.create_ephemeral_template_object()["taskcat-json"]
        au_template = Template(underlying=tc_template)
        actual = au_template.set_codename_ami(
            "AMZNLINUXHVM", "us-west-1", "slkdfjskldfj"
        )
        self.assertFalse(actual)

    def test_amiupdater_region_regex_matches_all_published_regions(self):
        ip_ranges = requests.get(
            "https://ip-ranges.amazonaws.com/ip-ranges.json"
        ).json()
        regions = list(set([x["region"] for x in ip_ranges["prefixes"]]))  # noqa: C403
        _ridx = regions.index("GLOBAL")
        _ = regions.pop(_ridx)
        for region in regions:
            with self.subTest(region=region):
                self.assertRegex(region, REGION_REGEX)

    def test_config_load_invalid_config(self):
        # invalid, but yaml is valid
        config_file = tempfile.NamedTemporaryFile(mode="w")
        config_file.write('{"this-is-invalid": 1}')
        config_file.file.close()
        with self.assertRaises(AMIUpdaterFatalException):
            AUConfig.load(config_file.name)
        config_file.close()
        # invalid, but yaml is valid
        config_file = tempfile.NamedTemporaryFile(mode="w")
        config_file.write('{"this-is-totally-invalid": 1')
        config_file.file.close()
        with self.assertRaises(AMIUpdaterFatalException):
            AUConfig.load(config_file.name)
        config_file.close()

    def test_config_load_valid_config(self):
        config_file = tempfile.NamedTemporaryFile(mode="w")
        config_file.write('{"global": {"AMIs": {"some_ami": {}}}}')
        config_file.file.close()
        AUConfig.load(config_file.name)
        config_file.close()
        self.assertEqual({"some_ami"}, AUConfig.codenames)

    def test_config_update_filter(self):
        AUConfig.raw_dict = {"global": {"AMIs": {"some_ami": {}}}}
        AUConfig.update_filter({"some__other_ami": {}})
        self.assertEqual(
            {"global": {"AMIs": {"some__other_ami": {}, "some_ami": {}}}},
            AUConfig.raw_dict,
        )

    @patch("taskcat._amiupdater.AMIUpdater._determine_templates", autospec=True)
    @patch("taskcat._amiupdater.AMIUpdater._get_regions", autospec=True)
    @patch("taskcat._amiupdater.Config", autospec=True)
    def test_amiupdater__init__(
        self, mock_config, mock_get_regions, mock_det_templates
    ):
        AMIUpdater(sentinel.config)
        mock_config.load.assert_called_once()
        mock_det_templates.assert_called_once()
        mock_get_regions.assert_called_once()

    def test_amiupdater_commit_needed_exception(self):
        e = AMIUpdaterCommitNeededException("foobar")
        self.assertEqual("foobar", e.message)
        self.assertTrue(isinstance(e, TaskCatException))

    def test_regional_codename__hash__(self):
        rc = RegionalCodename(
            region="us-east-1",
            cn="AMZNLINUXHVM",
            filters=[
                EC2FilterValue("name", ["amzn-ami-hvm-????.??.?.*-x86_64-gp2"]),
                EC2FilterValue("owner-alias", ["amazon"]),
                EC2FilterValue("state", ["available"]),
            ],
        )
        self.assertTrue(isinstance(rc.__hash__(), int))

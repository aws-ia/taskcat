import json
import logging
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime

import yaml

logger = logging.getLogger("taskcat")


class MockClientFactory:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get(self, service, region, **xxrgs):
        return MockEC2(**self.kwargs)


class MockEC2:
    def __init__(self, **kwargs):

        self.describe_regions_response = {
            "Regions": [
                {
                    "Endpoint": "ec2.eu-north-1.amazonaws.com",
                    "RegionName": "eu-north-1",
                },
                {
                    "Endpoint": "ec2.ap-south-1.amazonaws.com",
                    "RegionName": "ap-south-1",
                },
                {"Endpoint": "ec2.eu-west-3.amazonaws.com", "RegionName": "eu-west-3"},
                {"Endpoint": "ec2.eu-west-2.amazonaws.com", "RegionName": "eu-west-2"},
                {"Endpoint": "ec2.eu-west-1.amazonaws.com", "RegionName": "eu-west-1"},
                {
                    "Endpoint": "ec2.ap-northeast-3.amazonaws.com",
                    "RegionName": "ap-northeast-3",
                },
                {
                    "Endpoint": "ec2.ap-northeast-2.amazonaws.com",
                    "RegionName": "ap-northeast-2",
                },
                {
                    "Endpoint": "ec2.ap-northeast-1.amazonaws.com",
                    "RegionName": "ap-northeast-1",
                },
                {"Endpoint": "ec2.sa-east-1.amazonaws.com", "RegionName": "sa-east-1"},
                {
                    "Endpoint": "ec2.ca-central-1.amazonaws.com",
                    "RegionName": "ca-central-1",
                },
                {
                    "Endpoint": "ec2.ap-southeast-1.amazonaws.com",
                    "RegionName": "ap-southeast-1",
                },
                {
                    "Endpoint": "ec2.ap-southeast-2.amazonaws.com",
                    "RegionName": "ap-southeast-2",
                },
                {
                    "Endpoint": "ec2.eu-central-1.amazonaws.com",
                    "RegionName": "eu-central-1",
                },
                {"Endpoint": "ec2.us-east-1.amazonaws.com", "RegionName": "us-east-1"},
                {"Endpoint": "ec2.us-east-2.amazonaws.com", "RegionName": "us-east-2"},
                {"Endpoint": "ec2.us-west-1.amazonaws.com", "RegionName": "us-west-1"},
                {"Endpoint": "ec2.us-west-2.amazonaws.com", "RegionName": "us-west-2"},
            ]
        }

        self.describe_images_response = {
            "Images": [
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
        }

    def describe_regions(self):
        outp = self.describe_regions_response
        return outp

    def describe_images(self, Filters):
        outp = self.describe_images_response
        return outp


class TestAMIUpdater(unittest.TestCase):
    def _module_loader(self, return_module=False):
        try:
            del sys.modules["taskcat._amiupdater"]
        except KeyError:
            pass
        from taskcat._amiupdater import AMIUpdater, AMIUpdaterException

        if return_module:
            import taskcat._amiupdater

            return AMIUpdater, AMIUpdaterException, taskcat._amiupdater
        else:
            return AMIUpdater, AMIUpdaterException

    generic_skeleton_template = {
        "Mappings": {
            "AWSAMIRegionMap": {
                "us-east-1": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-east-2": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-west-1": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-west-2": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
            }
        }
    }

    inline_skeleton_template = {
        "Metadata": {
            "AWSAMIRegionMap": {
                "Filters": {
                    "NON_STANDARD_TEST": {
                        "name": "amzn-ami-hvm-????.??.?.*-x86_64-gp2",
                        "owner-alias": "amazon",
                    }
                }
            }
        },
        "Mappings": {
            "AWSAMIRegionMap": {
                "us-east-1": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-east-2": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-west-1": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-west-2": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
            }
        },
    }

    no_mapping_skeleton_template = {
        "Mappings": {
            "AWSAMIRegionMap": {
                "us-east-1": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-east-2": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-west-1": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-west-2": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
            }
        }
    }

    invalid_region_skeleton_template = {
        "Mappings": {
            "AWSAMIRegionMap": {
                "ASKDJSALKD": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-east-2": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-west-1": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
                "us-west-2": {
                    "AMZNLINUXHVM": "FOOBAR",
                    "AMZNLINUXHVM_CUSTOM_CONFIG": "FOOBAR",
                    "NON_STANDARD_TEST": "FOOBAR",
                },
            }
        }
    }

    ami_regex_pattern = re.compile("ami-([0-9a-z]{8}|[0-9a-z]{17})")

    def create_ephemeral_template(self, template_type="generic"):
        if template_type == "generic":
            data = self.generic_skeleton_template
        elif template_type == "inline":
            data = self.inline_skeleton_template
        elif template_type == "no_mapping":
            data = self.no_mapping_skeleton_template
        elif template_type == "invalid_region":
            data = self.invalid_region_skeleton_template

        fd, file = tempfile.mkstemp()
        with open(file, "w") as f:
            f.write(json.dumps(data))
        os.close(fd)
        return file

    def load_modified_template(self, fn):
        with open(fn) as f:
            t = f.read()
        return json.loads(t)

    def client_factory_handler(self):
        return MockClientFactory()

    def test_upstream_config_ALAMI(self):
        au, AMIUpdaterException, tcau = self._module_loader(return_module=True)
        cf = self.client_factory_handler()
        mapping_name = "AMZNLINUXHVM"
        template_file = self.create_ephemeral_template()
        amiupdater_args = {"path_to_templates": template_file, "client_factory": cf}
        au.upstream_config_file = "{}/{}".format(
            os.path.dirname(tcau.__file__), "cfg/amiupdater.cfg.yml"
        )
        a = au(**amiupdater_args)
        a.update_amis()

        template_result = self.load_modified_template(template_file)
        for region, mapping_data in template_result["Mappings"][
            "AWSAMIRegionMap"
        ].items():
            for codename, ami_id in mapping_data.items():
                if codename == mapping_name:
                    with self.subTest(
                        i="Verifying Updated AMI: [{}] / [{}]".format(
                            mapping_name, region
                        )
                    ):
                        self.assertRegex(ami_id, self.ami_regex_pattern)

    def test_local_config_ALAMI(self):
        au, AMIUpdaterException = self._module_loader()
        cf = self.client_factory_handler()
        config_file_dict = {
            "global": {
                "AMIs": {
                    "AMZNLINUXHVM_CUSTOM_CONFIG": {
                        "name": "amzn-ami-hvm-????.??.?.*-x86_64-gp2",
                        "owner-alias": "amazon",
                    }
                }
            }
        }
        user_config_file = tempfile.mkstemp()[1]
        with open(user_config_file, "w") as f:
            f.write(yaml.dump(config_file_dict))
        mapping_name = "AMZNLINUXHVM_CUSTOM_CONFIG"
        template_file = self.create_ephemeral_template()

        amiupdater_args = {
            "use_upstream_mappings": False,
            "path_to_templates": template_file,
            "user_config_file": user_config_file,
            "client_factory": cf,
        }
        a = au(**amiupdater_args)
        a.update_amis()

        template_result = self.load_modified_template(template_file)
        for region, mapping_data in template_result["Mappings"][
            "AWSAMIRegionMap"
        ].items():
            for codename, ami_id in mapping_data.items():
                if codename == mapping_name:
                    with self.subTest(
                        i="Verifying Updated AMI: [{}] / [{}]".format(
                            mapping_name, region
                        )
                    ):
                        self.assertRegex(ami_id, self.ami_regex_pattern)

    def test_in_template_ALAMI(self):
        au, AMIUpdaterException = self._module_loader()
        cf = self.client_factory_handler()
        mapping_name = "NON_STANDARD_TEST"
        template_file = self.create_ephemeral_template(template_type="inline")
        amiupdater_args = {
            "path_to_templates": template_file,
            "use_upstream_mappings": False,
            "client_factory": cf,
        }
        a = au(**amiupdater_args)
        a.update_amis()

        template_result = self.load_modified_template(template_file)
        for region, mapping_data in template_result["Mappings"][
            "AWSAMIRegionMap"
        ].items():
            for codename, ami_id in mapping_data.items():
                if codename == mapping_name:
                    with self.subTest(
                        i="Verifying Updated AMI: [{}] / [{}]".format(
                            mapping_name, region
                        )
                    ):
                        self.assertRegex(ami_id, self.ami_regex_pattern)

    def test_invalid_region_exception(self):
        au, AMIUpdaterException = self._module_loader()
        cf = self.client_factory_handler()
        template_file = self.create_ephemeral_template(template_type="invalid_region")
        amiupdater_args = {
            "path_to_templates": template_file,
            "use_upstream_mappings": False,
            "client_factory": cf,
        }
        a = au(**amiupdater_args)

        self.assertRaises(AMIUpdaterException, a.update_amis)

    def test_no_filters_exception(self):
        au, AMIUpdaterException = self._module_loader()
        cf = self.client_factory_handler()
        template_file = self.create_ephemeral_template()
        amiupdater_args = {
            "path_to_templates": template_file,
            "use_upstream_mappings": False,
            "client_factory": cf,
        }
        a = au(**amiupdater_args)
        self.assertRaises(AMIUpdaterException, a.update_amis)

    def test_APIResults_lessthan_comparison_standard(self):
        from taskcat._amiupdater import APIResultsData

        instance_args = {
            "codename": "foo",
            "ami_id": "ami-12345abcde",
            "creation_date": datetime(2010, 1, 23),
            "region": "us-east-1",
            "custom_comparisions": False,
        }
        a = APIResultsData(**instance_args)

        instance_args["ami_id"] = "ami-abcde12345"
        instance_args["creation_date"] = datetime(2012, 1, 23)
        b = APIResultsData(**instance_args)

        self.assertRaises(TypeError, a < b)

    def test_APIResults_greaterthan_comparison_standard(self):
        from taskcat._amiupdater import APIResultsData

        APIResultsData.custom_comparisons = False
        instance_args = {
            "codename": "foo",
            "ami_id": "ami-12345abcde",
            "creation_date": datetime(2010, 1, 23),
            "region": "us-east-1",
            "custom_comparisions": False,
        }
        a = APIResultsData(**instance_args)

        instance_args["ami_id"] = "ami-abcde12345"
        instance_args["creation_date"] = datetime(2012, 1, 23)
        b = APIResultsData(**instance_args)

        self.assertRaises(TypeError, a > b)

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

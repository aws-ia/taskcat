#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Tony Vattathil <tonynv@amazon.com>, <avattathil@gmail.com>
# Santiago Cardenas <sancard@amazon.com>, <santiago[dot]cardenas[at]outlook[dot]com>
# Shivansh Singh <sshvans@amazon.com>,
# Jay McConnell <jmmccon@amazon.com>,
# Andrew Glenn <andglenn@amazon.com>
from __future__ import print_function
import botocore
from botocore.exceptions import ClientError
import logging

debug = ''
error = ''
check = ''
fail = ''
info = ''
header = '\x1b[1;41;0m'
hightlight = '\x1b[0;30;47m'
name_color = '\x1b[0;37;44m'
aqua = '\x1b[0;30;46m'
green = '\x1b[0;30;42m'
white = '\x1b[0;30;47m'
orange = '\x1b[0;30;43m'
red = '\x1b[0;30;41m'
rst_color = '\x1b[0m'
E = '{1}[ERROR {0} ]{2} :'.format(error, red, rst_color)
D = '{1}[DEBUG {0} ]{2} :'.format(debug, aqua, rst_color)
P = '{1}[PASS  {0} ]{2} :'.format(check, green, rst_color)
F = '{1}[FAIL  {0} ]{2} :'.format(fail, red, rst_color)
I = '{1}[INFO  {0} ]{2} :'.format(info, orange, rst_color)

# create logger
logger = logging.getLogger('Reaper')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


# Reaper class provide functions to delete the AWS resources as per the
# defined rules.


# noinspection PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class Reaper(object):
    # Given an s3 bucket name, this function deletes all the versions of the bucket
    # Param:
    #   bucket_name - Name of the bucket to delete

    def __delete_s3_bucket(self, bucket_name):
        s3_resource = self.session.resource('s3')
        logger.info('Working on bucket [%s]', bucket_name)
        bucket_resource = s3_resource.Bucket(bucket_name)
        logger.info("Getting and deleting all object versions")
        try:
            object_versions = bucket_resource.object_versions.all()
            for object_version in object_versions:
                # TODO: Delete sets of 1000 object versions to reduce delete
                # requests
                object_version.delete()
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                logger.warning("Unable to delete object versions. (AccessDenied)")
            if e.response['Error']['Code'] == 'NoSuchBucket':
                logger.warning("Unable to get versions. (NoSuchBucket)")
            else:
                print(e)
        logger.info('Deleting bucket [%s]', bucket_name)
        try:
            bucket_resource.delete()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                logger.warning("Bucket was already deleted. (NoSuchBucket)")
            else:
                print(e)

    # Given a volume id, this function deletes the volume with given id
    # Param:
    #   volume_id - Id of the volume to be deleted

    def __delete_volume(self, volume_id):
        ec2_client = self.session.client('ec2')
        logger.info('Deleting EBS Volume [%s]', volume_id)
        try:
            ec2_client.delete_volume(VolumeId=volume_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                logger.warning("Unable to delete volume. (AccessDenied)")
            else:
                print(e)

    # Given a Security Group Id, this function deletes the security group with given Id.
    # Param:
    # sg_id - Id of the Security Group which needs to be deleted

    def __delete_sg(self, sg_id):
        ec2_client = self.session.client('ec2')
        logger.info('Deleting Security Group [%s]', sg_id)
        try:
            ec2_client.delete_security_group(GroupId=sg_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidGroup.InUse':
                logger.warning("Unable to delete Security group. It is in-use.")
            if e.response['Error']['Code'] == 'InvalidGroup.NotFound':
                logger.warning(
                    "Unable to delete Security group. (not found).")
            else:
                print(e)

    # Given a list of dictionary items where each dictionary item contains a resource list,
    # this function deletes all the resources given.
    # Param:
    #   list - List of dictionary items in the format shown below
    #
    #       [
    #           {
    #               'stackId': 'string',
    #               'resources': [
    #                   {
    #                       'logicalId': 'string',
    #                       'physicalId': 'string',
    #                       'resourceType': 'String'
    #                   },
    #               ]
    #           },
    #       ]

    def delete_all(self, stack_list):
        logger.info("Deleting all resources")
        for stack in stack_list:
            for resource in stack['resources']:
                self.__delete_resource(
                    resource['logicalId'], resource['resourceType'], resource['physicalId'])

    # Give a resource logical id and resource type, this function deletes the resource
    # Param:
    #   lid - logical id of the resource to be deleted
    #   type - resource type

    def __delete_resource(self, lid, rtype, pid):
        if rtype == "AWS::EC2::SecurityGroup":
            logger.debug("Found Security Group resource")
            self.__delete_sg(lid)
        if rtype == "AWS::EC2::Volume":
            logger.debug("Found Volume resource")
            self.__delete_volume(lid)
        if rtype == "AWS::S3::Bucket":
            logger.debug("Found Bucket resource")
            self.__delete_s3_bucket(pid)

    # Constructor

    def __init__(self, session):
        self.session = session

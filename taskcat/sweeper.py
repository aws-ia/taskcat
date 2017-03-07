#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# authors:
# Shivansh Singh sshvans@amazon.com

import boto3
import botocore
import logging

# create logger
logger = logging.getLogger('Sweeper')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# Sweeper class provide functions to delete the AWS resources as per the defined rules.

class Sweeper(object):

    # Given an s3 bucket name, this function deletes all the versions of the bucket
    # Param:
    #   bucket_name - Name of the bucket to delete

    def delete_s3_bucket(self, bucket_name):
        s3_resource = self.session.resource('s3')
        logger.info('Working on bucket [%s]', bucket_name)
        bucket_resource = s3_resource.Bucket(bucket_name)
        logger.info("Getting and deleting all object versions")
        try:
            object_versions = bucket_resource.object_versions.all()
            for object_version in object_versions:
                # TODO: Delete sets of 1000 object versions to reduce delete requests
                object_version.delete()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                logger.warn("Unable to delete object versions. (AccessDenied)")
            if e.response['Error']['Code'] == 'NoSuchBucket':
                logger.warn("Unable to get versions. (NoSuchBucket)")
            else:
                print(e)
        logger.info('Deleting bucket [%s]', bucket_name)
        try:
            bucket_resource.delete()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                logger.warn("Bucket was already deleted. (NoSuchBucket)")
            else:
                print(e)

    # Given a volume id, this function deletes the volume with given id
    # Param:
    #   volume_id - Id of the volume to be deleted

    def delete_volume(self, volume_id):
        ec2_client = self.session.client('ec2')
        logger.info('Deleting EBS Volume [%s]', volume_id)
        try:
            ec2_client.delete_volume(VolumeId=volume_id)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                logger.warn("Unable to delete volume. (AccessDenied)")
            else:
                print(e)

    # Given a Security Group Id, this function deletes the security group with given Id.
    # Param:
    # sg_id - Id of the Security Group which needs to be deleted

    def delete_sg(self, sg_id):
        ec2_client = self.session.client('ec2')
        logger.info('Deleting Security Group [%s]', sg_id)
        try:
            ec2_client.delete_security_group(GroupId=sg_id)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvalidGroup.InUse':
                logger.warn("Unable to delete Security group. It is in-use.")
            if e.response['Error']['Code'] == 'InvalidGroup.NotFound':
                logger.warn("Unable to delete Security group. Security group not found.")
            else:
                print(e)

    # Constructor

    def __init__(self, session):
        self.session = session

# session = boto3.session.Session()
# s = Sweeper(session)
# s.delete_sg("sg-faf2dd82")
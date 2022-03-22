# -*- coding: utf-8 -*-

import boto3

boto_ses = boto3.session.Session()
sts_client = boto3.client("sts")

aws_account_id = sts_client.get_caller_identity()["Account"]
aws_region = boto_ses.region_name

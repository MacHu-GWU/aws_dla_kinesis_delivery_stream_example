# -*- coding: utf-8 -*-

"""
Basic dependencies to make infrastructure as code works.

Including:

- a S3 bucket to store cloudformation template artifacts
"""

import cottonformation as cft
from cottonformation.res import s3

from ..boto_ses import aws_account_id, aws_region
from ..config import config

tpl = cft.Template()

artifacts_s3_bucket_name = f"{aws_account_id}-{aws_region}-cottonformation"
s3_bucket_for_artifacts = s3.Bucket(
    "S3BucketForCottonFormation",
    p_BucketName=artifacts_s3_bucket_name,
)
tpl.add(s3_bucket_for_artifacts)
tpl.batch_tagging(ProjectName=config.project_name_slug)

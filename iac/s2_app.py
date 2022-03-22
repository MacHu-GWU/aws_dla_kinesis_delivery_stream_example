# -*- coding: utf-8 -*-

import cottonformation as cft
from kds_example.iac.s1_dependency import artifacts_s3_bucket_name
from kds_example.iac.s2_app import stack
from kds_example.boto_ses import boto_ses, aws_account_id, aws_region

# create cloudformation template
tpl = cft.Template()

# partial deployment handling
tpl.add(stack.rg1_data_bucket)
tpl.add(stack.rg2_iam_permission)
tpl.add(stack.rg3_opensearch)
tpl.add(stack.rg4_kinesis_data_stream)
tpl.add(stack.rg5_kinesis_delivery_stream_to_s3)
tpl.add(stack.rg6_kinesis_delivery_stream_to_oss)

tpl.batch_tagging(ProjectName=stack.project_name)

# deploy stack
env = cft.Env(boto_ses=boto_ses)
env.deploy(
    template=tpl,
    stack_name=stack.stack_name,
    bucket_name=artifacts_s3_bucket_name,
    include_iam=True,
)

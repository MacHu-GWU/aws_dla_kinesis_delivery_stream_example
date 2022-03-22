# -*- coding: utf-8 -*-

import cottonformation as cft
from kds_example.iac.s1_dependency import tpl
from kds_example.boto_ses import boto_ses, aws_account_id, aws_region

env = cft.Env(boto_ses=boto_ses)

env.deploy(
    template=tpl,
    stack_name=f"cottonformation-deps-{aws_account_id}-{aws_region}",
)

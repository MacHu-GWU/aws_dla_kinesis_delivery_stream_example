# -*- coding: utf-8 -*-

from .boto_ses import boto_ses, aws_region
from .oss_utils import create_opensearch_connection
from .iac.s2_app import stack

oss_domain_endpoint = stack.get_output_value(
    boto_ses, stack.out_opensearch_domain_endpoint.id,
)

oss = create_opensearch_connection(
    boto_ses=boto_ses,
    aws_region=aws_region,
    es_endpoint=oss_domain_endpoint,
    test=True,
)

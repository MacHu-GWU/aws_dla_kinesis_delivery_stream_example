# -*- coding: utf-8 -*-

"""
This is the Kinesis data stream application stack.

Prerequisite:

1. An AWS Account with default VPC
2. Choose an AWS Region, all resource include S3 bucket, OpenSearch Cluster,
    Kinesis Data Stream, Kinesis Delivery Stream, Lambda Function are on the same
    AWS Region.
3. Manually create a S3 bucket so you can upload Infrastructure as Code to it
    and then deploy from S3
4. Manually create a IAM Role for Cloud 9 dev environment. Cloud 9 will be
    "Your laptop on AWS", give it sufficient IAM permission to (Give it IAM permission equivalent to your AWS login):
    - deploy cloudformation
    - put records to kinesis stream
    - run query to OpenSearch
5. Manually create a c5.4xlarge Cloud 9 dev environment using default VPC.

Resources:

1. a S3 bucket to store kinesis stream backup / success / error data.
2. a IAM Role for:
    - cloud 9 dev ec2 machine
    - transformation lambda function
    - kinesis firehose
"""

from typing import List, Tuple
import attr
import cottonformation as cft
from cottonformation.res import (
    s3, iam, opensearchservice, kinesis, kinesisfirehose, awslambda,
)

from ..config import config
from ..boto_ses import aws_account_id, aws_region


def ensure_endswith_slash(s3_prefix: str) -> str:
    """
    For kinesis stream s3 backup / s3 destination, the s3 prefix has to ends
    with "/". This function can ensure that.
    """
    if s3_prefix.endswith("/"):
        return s3_prefix
    else:
        return s3_prefix + "/"


def create_delivery_stream_iam_policy_statements(
    delivery_stream_name: str,
    aws_account_id: str,
    aws_region: str,
    backup_s3_bucket: str,
    source_kinesis_data_stream_name: str,
    destination_s3_bucket: str = None,
    destination_oss_domain_name: str = None,
    transformation_lbd_func_name: str = None,
    add_shared_statement=True,
) -> List[dict]:
    """

    :param delivery_stream_name:
    :param aws_account_id:
    :param aws_region:
    :param backup_s3_bucket:
    :param source_kinesis_data_stream_name:
    :param destination_s3_bucket:
    :param destination_oss_domain_name:
    :param transformation_lbd_func_name:
    :param add_shared_statement:
    :return:
    """
    shared_ec2_statement = {
        "Sid": "",
        "Effect": "Allow",
        "Action": [
            "ec2:DescribeVpcs",
            "ec2:DescribeVpcAttribute",
            "ec2:DescribeSubnets",
            "ec2:DescribeSecurityGroups",
            "ec2:DescribeNetworkInterfaces",
            "ec2:CreateNetworkInterface",
            "ec2:CreateNetworkInterfacePermission",
            "ec2:DeleteNetworkInterface",
        ],
        "Resource": "*",
    }
    shared_cloudwatch_statement = {
        "Sid": "",
        "Effect": "Allow",
        "Action": [
            "logs:PutLogEvents"
        ],
        "Resource": f"arn:aws:logs:{aws_region}:{aws_account_id}:log-group:%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%:log-stream:*",
    }

    def create_s3_statement(bucket_name: str) -> dict:
        return {
            "Sid": "",
            "Effect": "Allow",
            "Action": [
                "s3:AbortMultipartUpload",
                "s3:GetBucketLocation",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:PutObject",
            ],
            "Resource": [
                f"arn:aws:s3:::{bucket_name}",
                f"arn:aws:s3:::{bucket_name}/*",
            ],
        }

    def create_cloudwatch_statement(delivery_stream_name: str) -> dict:
        return {
            "Sid": "",
            "Effect": "Allow",
            "Action": [
                "logs:PutLogEvents"
            ],
            "Resource": f"arn:aws:logs:{aws_region}:{aws_account_id}:log-group:/aws/kinesisfirehose/{delivery_stream_name}:log-stream:*",
        }

    def create_kms_statement(source_kinesis_data_stream_name: str) -> List[dict]:
        return [
            {
                "Effect": "Allow",
                "Action": [
                    "kms:GenerateDataKey",
                    "kms:Decrypt"
                ],
                "Resource": [
                    f"arn:aws:kms:{aws_region}:{aws_account_id}:key/%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%"
                ],
                "Condition": {
                    "StringEquals": {
                        "kms:ViaService": f"s3.{aws_region}.amazonaws.com"
                    },
                    "StringLike": {
                        "kms:EncryptionContext:aws:s3:arn": [
                            "arn:aws:s3:::%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%/*",
                            "arn:aws:s3:::%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%"
                        ]
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "kms:Decrypt"
                ],
                "Resource": [
                    f"arn:aws:kms:{aws_region}:{aws_account_id}:key/%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%"
                ],
                "Condition": {
                    "StringEquals": {
                        "kms:ViaService": f"kinesis.{aws_region}.amazonaws.com"
                    },
                    "StringLike": {
                        "kms:EncryptionContext:aws:kinesis:arn": f"arn:aws:kinesis:{aws_region}:{aws_account_id}:stream/{source_kinesis_data_stream_name}"
                    }
                }
            }
        ]

    def create_kinesis_statement(source_kinesis_data_stream_name: str) -> dict:
        return {
            "Sid": "",
            "Effect": "Allow",
            "Action": [
                "kinesis:DescribeStream",
                "kinesis:GetShardIterator",
                "kinesis:GetRecords",
                "kinesis:ListShards"
            ],
            "Resource": f"arn:aws:kinesis:{aws_region}:{aws_account_id}:stream/{source_kinesis_data_stream_name}"
        }

    def create_lambda_statement(transformation_lbd_func_name: str) -> dict:
        return {
            "Sid": "",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:GetFunctionConfiguration"
            ],
            "Resource": f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{transformation_lbd_func_name}:$LATEST"
        }

    def create_opensearch_statements(
        oss_domain_name: str,
        oss_index_name: str,
    ) -> List[dict]:
        return [
            {
                "Sid": "",
                "Effect": "Allow",
                "Action": [
                    "es:DescribeElasticsearchDomain",
                    "es:DescribeElasticsearchDomains",
                    "es:DescribeElasticsearchDomainConfig",
                    "es:ESHttpPost",
                    "es:ESHttpPut",
                ],
                "Resource": [
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}",
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}/*",
                ],
            },
            {
                "Sid": "",
                "Effect": "Allow",
                "Action": [
                    "es:ESHttpGet",
                ],
                "Resource": [
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}/_all/_settings",
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}/_cluster/stats",
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}/_nodes",
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}/_nodes/*/stats",
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}/_stats",
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}/{oss_index_name}/_stats",
                    f"arn:aws:es:{aws_region}:{aws_account_id}:domain/{oss_domain_name}/{oss_index_name}/_mapping/%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%",
                ],
            },
        ]

    statement = []
    if add_shared_statement:
        statement.append(shared_ec2_statement)
        statement.append(shared_cloudwatch_statement)

    statement.append(create_s3_statement(bucket_name=backup_s3_bucket))
    statement.append(create_cloudwatch_statement(delivery_stream_name=delivery_stream_name))
    statement.extend(create_kms_statement(source_kinesis_data_stream_name=source_kinesis_data_stream_name))
    statement.append(create_kinesis_statement(source_kinesis_data_stream_name=source_kinesis_data_stream_name))

    if create_lambda_statement:
        statement.append(create_lambda_statement(transformation_lbd_func_name=transformation_lbd_func_name))

    if destination_s3_bucket:
        statement.append(create_s3_statement(bucket_name=destination_s3_bucket))

    if destination_oss_domain_name:
        statement.extend(create_opensearch_statements(
            oss_domain_name=destination_oss_domain_name,
            oss_index_name=destination_oss_domain_name,
        ))

    return statement


def create_delivery_stream_with_s3_destination(
    logic_id: str,
    aws_account_id: str,
    aws_region: str,
    delivery_stream_name: str,
    kinesis_data_stream: kinesis.Stream,
    delivery_stream_iam_role: iam.Role,
    destination_s3_bucket: str,
    destination_s3_prefix_success: str,
    destination_s3_prefix_failed: str,
    backup_s3_bucket: str,
    backup_s3_prefix_success: str,
    backup_s3_prefix_failed: str,
    transformation_lbd_func_name: str,
    delivery_stream_buffer_hint_size_in_mb: int,
    delivery_stream_buffer_hint_interval_in_sec: int,
    s3_backup_buffer_hint_size_in_mb: int,
    s3_backup_buffer_hint_interval_in_sec: int,
    lambda_buffer_hint_size_in_mb: int,
    lambda_buffer_hint_interval_in_sec: int,
) -> Tuple[
    kinesisfirehose.DeliveryStream,
    awslambda.Permission,
]:
    """
    The Lambda Function should be deployed by AWS Chalice, not by CloudFormation.

    :param logic_id:
    :param aws_account_id:
    :param aws_region:
    :param delivery_stream_name:
    :param kinesis_data_stream:
    :param delivery_stream_iam_role:
    :param destination_s3_bucket:
    :param destination_s3_prefix_success:
    :param destination_s3_prefix_failed:
    :param backup_s3_bucket:
    :param backup_s3_prefix_success:
    :param backup_s3_prefix_failed:
    :param transformation_lbd_func_name:
    :param delivery_stream_buffer_hint_size_in_mb:
    :param delivery_stream_buffer_hint_interval_in_sec:
    :param s3_backup_buffer_hint_size_in_mb:
    :param s3_backup_buffer_hint_interval_in_sec:
    :param lambda_buffer_hint_size_in_mb:
    :param lambda_buffer_hint_interval_in_sec:
    :return:
    """
    destination_s3_prefix_success = ensure_endswith_slash(destination_s3_prefix_success)
    destination_s3_prefix_failed = ensure_endswith_slash(destination_s3_prefix_failed)
    backup_s3_prefix_success = ensure_endswith_slash(backup_s3_prefix_success)
    backup_s3_prefix_failed = ensure_endswith_slash(backup_s3_prefix_failed)

    delivery_stream = kinesisfirehose.DeliveryStream(
        logic_id,
        p_DeliveryStreamName=delivery_stream_name,
        p_DeliveryStreamType="KinesisStreamAsSource",
        p_KinesisStreamSourceConfiguration=kinesisfirehose.PropDeliveryStreamKinesisStreamSourceConfiguration(
            rp_KinesisStreamARN=kinesis_data_stream.rv_Arn,
            rp_RoleARN=delivery_stream_iam_role.rv_Arn,
        ),
        p_ExtendedS3DestinationConfiguration=kinesisfirehose.PropDeliveryStreamExtendedS3DestinationConfiguration(
            rp_BucketARN=f"arn:aws:s3:::{destination_s3_bucket}",
            rp_RoleARN=delivery_stream_iam_role.rv_Arn,
            p_Prefix=destination_s3_prefix_success,
            p_ErrorOutputPrefix=destination_s3_prefix_failed,
            p_BufferingHints=kinesisfirehose.PropDeliveryStreamBufferingHints(
                p_IntervalInSeconds=delivery_stream_buffer_hint_interval_in_sec,
                p_SizeInMBs=delivery_stream_buffer_hint_size_in_mb,
            ),
            p_CloudWatchLoggingOptions=kinesisfirehose.PropDeliveryStreamCloudWatchLoggingOptions(
                p_Enabled=True,
                p_LogGroupName=f"/aws/kinesis/firehose/{delivery_stream_name}",
                p_LogStreamName="BackupDelivery",
            ),
            p_S3BackupMode="Enabled",
            p_S3BackupConfiguration=kinesisfirehose.PropDeliveryStreamS3DestinationConfiguration(
                rp_BucketARN=f"arn:aws:s3:::{backup_s3_bucket}",
                rp_RoleARN=delivery_stream_iam_role.rv_Arn,
                p_Prefix=backup_s3_prefix_success,
                p_ErrorOutputPrefix=backup_s3_prefix_failed,
                p_BufferingHints=kinesisfirehose.PropDeliveryStreamBufferingHints(
                    p_SizeInMBs=s3_backup_buffer_hint_interval_in_sec,
                    p_IntervalInSeconds=s3_backup_buffer_hint_size_in_mb,
                ),
            ),
            p_ProcessingConfiguration=kinesisfirehose.PropDeliveryStreamProcessingConfiguration(
                p_Enabled=True,
                p_Processors=[
                    kinesisfirehose.PropDeliveryStreamProcessor(
                        rp_Type="Lambda",
                        p_Parameters=[
                            kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                rp_ParameterName="LambdaArn",
                                rp_ParameterValue=f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{transformation_lbd_func_name}",
                            ),
                            kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                rp_ParameterName="NumberOfRetries",
                                rp_ParameterValue="1",
                            ),
                            kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                rp_ParameterName="RoleArn",
                                rp_ParameterValue=delivery_stream_iam_role.rv_Arn,
                            ),
                            kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                rp_ParameterName="BufferIntervalInSeconds",
                                rp_ParameterValue=f"{lambda_buffer_hint_interval_in_sec}",
                            ),
                            kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                rp_ParameterName="BufferSizeInMBs",
                                rp_ParameterValue=f"{lambda_buffer_hint_size_in_mb}",
                            ),
                        ]
                    )
                ]
            )
        ),
        ra_DependsOn=[
            delivery_stream_iam_role,
            kinesis_data_stream,
        ]
    )

    delivery_stream_to_lbd_permission = awslambda.Permission(
        "DeliveryStreamToS3LbdPermission",
        rp_Action="lambda:InvokeFunction",
        rp_FunctionName=f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{transformation_lbd_func_name}",
        rp_Principal="firehose.amazonaws.com",
        p_SourceArn=kinesis_data_stream.rv_Arn,
    )

    return delivery_stream, delivery_stream_to_lbd_permission


@attr.s
class Stack(cft.Stack):
    project_name: str = attr.ib()
    stage: str = attr.ib()
    aws_account_id: str = attr.ib()
    aws_region: str = attr.ib()
    oss_index_name: str = attr.ib(default="bank_account")

    @property
    def project_name_slug(self) -> str:
        return self.project_name.replace("_", "-")

    @property
    def stack_name(self) -> str:
        return self.project_name_slug

    @property
    def chalice_app_name(self):
        return self.project_name_slug

    @property
    def s3_data_bucket_name(self) -> str:
        return f"{self.aws_account_id}-{self.aws_region}-{self.project_name_slug}"

    @property
    def iam_role_name_for_lbd(self) -> str:
        return f"{self.project_name_slug}-for-lambda"

    @property
    def iam_role_name_for_firehose(self) -> str:
        return f"{self.project_name_slug}-for-firehose"

    @property
    def lbd_func_name_transformation_for_s3(self) -> str:
        return f"{self.chalice_app_name}-{self.stage}-to_s3"

    @property
    def lbd_func_name_transformation_for_oss(self) -> str:
        return f"{self.chalice_app_name}-{self.stage}-to_oss"

    @property
    def all_lbd_func_name(self) -> List[str]:
        return [
            self.lbd_func_name_transformation_for_s3,
            self.lbd_func_name_transformation_for_oss,
        ]

    @property
    def kinesis_data_stream_name(self) -> str:
        return f"{self.project_name_slug}"

    @property
    def kinesis_delivery_stream_name_for_s3(self) -> str:
        return f"{self.project_name_slug}-to-s3"

    @property
    def kinesis_delivery_stream_name_for_oss(self) -> str:
        return f"{self.project_name_slug}-to-oss"

    @property
    def all_kinesis_delivery_stream_name(self) -> List[str]:
        return [
            self.kinesis_delivery_stream_name_for_s3,
            self.kinesis_delivery_stream_name_for_oss,
        ]

    @property
    def oss_domain_name(self) -> str:
        return f"{self.project_name_slug}"

    def mk_rg1_data_bucket(self):
        self.rg1_data_bucket = cft.ResourceGroup("RG1")

        self.s3_data_bucket = s3.Bucket(
            "S3BucketForData",
            p_BucketName=self.s3_data_bucket_name,
            ra_DeletionPolicy=cft.constant.DeletionPolicy.Delete,
        )
        self.rg1_data_bucket.add(self.s3_data_bucket)

    def mk_rg2_iam_permission(self):
        self.rg2_iam_permission = cft.ResourceGroup("RG2")

        self.iam_role_for_lbd = iam.Role(
            "IamRoleForLambda",
            rp_AssumeRolePolicyDocument=cft.helpers.iam.AssumeRolePolicyBuilder(
                cft.helpers.iam.ServicePrincipal.awslambda(),
            ).build(),
            p_RoleName=self.iam_role_name_for_lbd,
            p_ManagedPolicyArns=[
                cft.helpers.iam.AwsManagedPolicy.AWSLambdaBasicExecutionRole,
            ]
        )
        self.rg2_iam_permission.add(self.iam_role_for_lbd)

        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": [
                        "s3:AbortMultipartUpload",
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:ListBucketMultipartUploads",
                        "s3:PutObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self.s3_data_bucket_name}",
                        f"arn:aws:s3:::{self.s3_data_bucket_name}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kms:GenerateDataKey",
                        "kms:Decrypt"
                    ],
                    "Resource": [
                        f"arn:aws:kms:{self.aws_region}:{self.aws_account_id}:key/%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%"
                    ],
                    "Condition": {
                        "StringEquals": {
                            "kms:ViaService": f"s3.{self.aws_region}.amazonaws.com"
                        },
                        "StringLike": {
                            "kms:EncryptionContext:aws:s3:arn": [
                                "arn:aws:s3:::%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%/*",
                                "arn:aws:s3:::%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%"
                            ]
                        }
                    }
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": [
                        "ec2:DescribeVpcs",
                        "ec2:DescribeVpcAttribute",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateNetworkInterfacePermission",
                        "ec2:DeleteNetworkInterface"
                    ],
                    "Resource": "*"
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": [
                        "es:DescribeElasticsearchDomain",
                        "es:DescribeElasticsearchDomains",
                        "es:DescribeElasticsearchDomainConfig",
                        "es:ESHttpPost",
                        "es:ESHttpPut"
                    ],
                    "Resource": [
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}",
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/*"
                    ]
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": [
                        "es:ESHttpGet"
                    ],
                    "Resource": [
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/_all/_settings",
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/_cluster/stats",
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/{self.oss_index_name}/_mapping/%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%",
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/_nodes",
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/_nodes/*/stats",
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/_stats",
                        f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/{self.oss_index_name}/_stats"
                    ]
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": [
                        "logs:PutLogEvents"
                    ],
                    "Resource": f"arn:aws:logs:{self.aws_region}:{self.aws_account_id}:log-group:%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%:log-stream:*"
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": [
                        "logs:PutLogEvents"
                    ],
                    "Resource": [
                        f"arn:aws:logs:{self.aws_region}:{self.aws_account_id}:log-group:/aws/kinesisfirehose/{name}:log-stream:*"
                        for name in self.all_kinesis_delivery_stream_name
                    ]
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Action": [
                        "kinesis:DescribeStream",
                        "kinesis:GetShardIterator",
                        "kinesis:GetRecords",
                        "kinesis:ListShards"
                    ],
                    "Resource": f"arn:aws:kinesis:{self.aws_region}:{self.aws_account_id}:stream/{self.kinesis_data_stream_name}"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kms:Decrypt"
                    ],
                    "Resource": [
                        f"arn:aws:kms:{self.aws_region}:{self.aws_account_id}:key/%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%"
                    ],
                    "Condition": {
                        "StringEquals": {
                            "kms:ViaService": f"kinesis.{self.aws_region}.amazonaws.com"
                        },
                        "StringLike": {
                            "kms:EncryptionContext:aws:kinesis:arn": f"arn:aws:kinesis:{self.aws_region}:{self.aws_account_id}:stream/{self.kinesis_data_stream_name}"
                        }
                    }
                }
            ]
        }
        for name in self.all_lbd_func_name:
            policy_document["Statement"].append({
                "Sid": "",
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction",
                    "lambda:GetFunctionConfiguration"
                ],
                "Resource": f"arn:aws:lambda:{self.aws_region}:{self.aws_account_id}:function:{name}:$LATEST"
            })

        self.iam_policy_for_firehose = iam.ManagedPolicy(
            "IamPolicyForKinesisDeliveryStream",
            p_ManagedPolicyName=f"{self.project_name_slug}-for-firehose",
            rp_PolicyDocument=policy_document,
        )
        self.rg2_iam_permission.add(self.iam_policy_for_firehose)

        self.iam_role_for_firehose = iam.Role(
            "IamRoleForKinesisDeliveryStream",
            rp_AssumeRolePolicyDocument=cft.helpers.iam.AssumeRolePolicyBuilder(
                cft.helpers.iam.ServicePrincipal.firehose(),
            ).build(),
            p_RoleName=self.iam_role_name_for_firehose,
            p_ManagedPolicyArns=[
                self.iam_policy_for_firehose.ref(),
                "arn:aws:iam::aws:policy/AWSLambda_FullAccess",
            ],
        )
        self.rg2_iam_permission.add(self.iam_role_for_firehose)

    def mk_rg3_opensearch(self):
        self.rg3_opensearch = cft.ResourceGroup("RG3")

        self.opensearch_cluster = opensearchservice.Domain(
            "OpenSearchDomain",
            p_DomainName=self.oss_domain_name,
            p_ClusterConfig=opensearchservice.PropDomainClusterConfig(
                p_InstanceCount=3,
                p_InstanceType="r6g.large.search",
                p_DedicatedMasterEnabled=True,
                p_DedicatedMasterCount=3,
                p_DedicatedMasterType="r6g.large.search",
                p_ZoneAwarenessEnabled=True,
                p_ZoneAwarenessConfig=opensearchservice.PropDomainZoneAwarenessConfig(
                    p_AvailabilityZoneCount=3,
                )
            ),
            p_EBSOptions=opensearchservice.PropDomainEBSOptions(
                p_EBSEnabled=True,
                p_VolumeType="gp2",
                p_VolumeSize=100,
            ),
            p_AccessPolicies={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": [
                                f"arn:aws:iam::{self.aws_account_id}:user/sanhe",
                                self.iam_role_for_firehose.rv_Arn,
                            ]
                        },
                        "Action": "es:*",
                        "Resource": f"arn:aws:es:{self.aws_region}:{self.aws_account_id}:domain/{self.oss_domain_name}/*"
                    }
                ]
            },
            p_CognitoOptions=opensearchservice.PropDomainCognitoOptions(
                p_Enabled=False,
            ),
            ra_DependsOn=[
                self.iam_role_for_firehose,
            ],
            ra_DeletionPolicy="Delete",
        )
        self.rg3_opensearch.add(self.opensearch_cluster)

        self.out_opensearch_domain_endpoint = cft.Output(
            "OpenSearchDomainEndpoint",
            Value=self.opensearch_cluster.rv_DomainEndpoint,
            DependsOn=self.opensearch_cluster
        )
        self.rg3_opensearch.add(self.out_opensearch_domain_endpoint)

    def mk_rg4_kinesis_data_stream(self):
        self.rg4_kinesis_data_stream = cft.ResourceGroup("RG4")

        self.kinesis_data_stream = kinesis.Stream(
            "KinesisDataStream",
            p_Name=self.kinesis_data_stream_name,
            p_ShardCount=10,
            p_StreamModeDetails=kinesis.PropStreamStreamModeDetails(
                rp_StreamMode="PROVISIONED",
            ),
        )
        self.rg4_kinesis_data_stream.add(self.kinesis_data_stream)

    def mk_rg5_kinesis_delivery_stream_to_s3(self):
        self.rg5_kinesis_delivery_stream_to_s3 = cft.ResourceGroup("RG5")

        # self.kinesis_delivery_stream_to_s3 = kinesisfirehose.DeliveryStream(
        #     "KinesisDeliveryStreamToS3",
        #     p_DeliveryStreamName=self.kinesis_delivery_stream_name_for_s3,
        #     p_DeliveryStreamType="KinesisStreamAsSource",
        #     p_KinesisStreamSourceConfiguration=kinesisfirehose.PropDeliveryStreamKinesisStreamSourceConfiguration(
        #         rp_KinesisStreamARN=self.kinesis_data_stream.rv_Arn,
        #         rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
        #     ),
        #     p_ExtendedS3DestinationConfiguration=kinesisfirehose.PropDeliveryStreamExtendedS3DestinationConfiguration(
        #         rp_BucketARN=self.s3_data_bucket.rv_Arn,
        #         rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
        #         p_Prefix="to-s3/03-success/",
        #         p_ErrorOutputPrefix="to-s3/04-failed/",
        #         p_BufferingHints=kinesisfirehose.PropDeliveryStreamBufferingHints(
        #             p_IntervalInSeconds=60,
        #             p_SizeInMBs=5,
        #         ),
        #         p_CloudWatchLoggingOptions=kinesisfirehose.PropDeliveryStreamCloudWatchLoggingOptions(
        #             p_Enabled=True,
        #             p_LogGroupName=f"/aws/kinesis/firehose/{self.kinesis_delivery_stream_name_for_s3}",
        #             p_LogStreamName="BackupDelivery",
        #         ),
        #         p_S3BackupMode="Enabled",
        #         p_S3BackupConfiguration=kinesisfirehose.PropDeliveryStreamS3DestinationConfiguration(
        #             rp_BucketARN=self.s3_data_bucket.rv_Arn,
        #             rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
        #             p_Prefix="to-s3/01-backup/",
        #             p_ErrorOutputPrefix="to-s3/02-backup-failed/",
        #             p_BufferingHints=kinesisfirehose.PropDeliveryStreamBufferingHints(
        #                 p_IntervalInSeconds=60,
        #                 p_SizeInMBs=5,
        #             ),
        #         ),
        #         p_ProcessingConfiguration=kinesisfirehose.PropDeliveryStreamProcessingConfiguration(
        #             p_Enabled=True,
        #             p_Processors=[
        #                 kinesisfirehose.PropDeliveryStreamProcessor(
        #                     rp_Type="Lambda",
        #                     p_Parameters=[
        #                         kinesisfirehose.PropDeliveryStreamProcessorParameter(
        #                             rp_ParameterName="LambdaArn",
        #                             rp_ParameterValue=f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{self.lbd_func_name_transformation_for_s3}",
        #                         ),
        #                         kinesisfirehose.PropDeliveryStreamProcessorParameter(
        #                             rp_ParameterName="NumberOfRetries",
        #                             rp_ParameterValue="1",
        #                         ),
        #                         kinesisfirehose.PropDeliveryStreamProcessorParameter(
        #                             rp_ParameterName="RoleArn",
        #                             rp_ParameterValue=self.iam_role_for_firehose.rv_Arn,
        #                         ),
        #                         kinesisfirehose.PropDeliveryStreamProcessorParameter(
        #                             rp_ParameterName="BufferSizeInMBs",
        #                             rp_ParameterValue="3",
        #                         ),
        #                         kinesisfirehose.PropDeliveryStreamProcessorParameter(
        #                             rp_ParameterName="BufferIntervalInSeconds",
        #                             rp_ParameterValue="60",
        #                         ),
        #                     ]
        #                 )
        #             ]
        #         )
        #     ),
        #     ra_DependsOn=[
        #         self.iam_role_for_firehose,
        #         self.kinesis_data_stream,
        #     ]
        # )

        (
            kinesis_delivery_stream_to_s3,
            delivery_stream_to_s3_lbd_permission,
        ) = create_delivery_stream_with_s3_destination(
            logic_id="KinesisDeliveryStreamToS3",
            aws_account_id=aws_account_id,
            aws_region=aws_region,
            delivery_stream_name=self.kinesis_delivery_stream_name_for_s3,
            kinesis_data_stream=self.kinesis_data_stream,
            delivery_stream_iam_role=self.iam_role_for_firehose,
            destination_s3_bucket=self.s3_data_bucket_name,
            destination_s3_prefix_success="to-s3/03-success/",
            destination_s3_prefix_failed="to-s3/04-failed/",
            backup_s3_bucket=self.s3_data_bucket_name,
            backup_s3_prefix_success="to-s3/01-backup/",
            backup_s3_prefix_failed="to-s3/02-backup-failed/",
            transformation_lbd_func_name=self.lbd_func_name_transformation_for_s3,
            delivery_stream_buffer_hint_size_in_mb=5,
            delivery_stream_buffer_hint_interval_in_sec=60,
            s3_backup_buffer_hint_size_in_mb=5,
            s3_backup_buffer_hint_interval_in_sec=60,
            lambda_buffer_hint_size_in_mb=3,
            lambda_buffer_hint_interval_in_sec=60,
        )
        self.kinesis_delivery_stream_to_s3 = kinesis_delivery_stream_to_s3
        self.rg5_kinesis_delivery_stream_to_s3.add(self.kinesis_delivery_stream_to_s3)

        # self.delivery_stream_to_s3_lbd_permission = awslambda.Permission(
        #     "DeliveryStreamToS3LbdPermission",
        #     rp_Action="lambda:InvokeFunction",
        #     rp_FunctionName=f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{self.lbd_func_name_transformation_for_s3}",
        #     rp_Principal="firehose.amazonaws.com",
        #     p_SourceArn=self.kinesis_delivery_stream_to_s3.rv_Arn,
        # )
        self.delivery_stream_to_s3_lbd_permission = delivery_stream_to_s3_lbd_permission
        self.rg5_kinesis_delivery_stream_to_s3.add(self.delivery_stream_to_s3_lbd_permission)

    def mk_rg6_kinesis_delivery_stream_to_oss(self):
        self.rg6_kinesis_delivery_stream_to_oss = cft.ResourceGroup("RG6")

        self.kinesis_delivery_stream_to_oss = kinesisfirehose.DeliveryStream(
            "KinesisDeliveryStreamToOSS",
            p_DeliveryStreamName=self.kinesis_delivery_stream_name_for_oss,
            p_DeliveryStreamType="KinesisStreamAsSource",
            p_KinesisStreamSourceConfiguration=kinesisfirehose.PropDeliveryStreamKinesisStreamSourceConfiguration(
                rp_KinesisStreamARN=self.kinesis_data_stream.rv_Arn,
                rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
            ),
            p_AmazonopensearchserviceDestinationConfiguration=kinesisfirehose.PropDeliveryStreamAmazonopensearchserviceDestinationConfiguration(
                rp_IndexName=self.oss_index_name,
                rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
                p_DomainARN=self.opensearch_cluster.rv_DomainArn,
                p_IndexRotationPeriod="NoRotation",
                p_RetryOptions=kinesisfirehose.PropDeliveryStreamAmazonopensearchserviceRetryOptions(
                    p_DurationInSeconds=60,
                ),
                p_BufferingHints=kinesisfirehose.PropDeliveryStreamAmazonopensearchserviceBufferingHints(
                    p_IntervalInSeconds=60,
                    p_SizeInMBs=5,
                ),
                p_CloudWatchLoggingOptions=kinesisfirehose.PropDeliveryStreamCloudWatchLoggingOptions(
                    p_Enabled=True,
                    p_LogGroupName=f"/aws/kinesis/firehose/{self.kinesis_delivery_stream_name_for_oss}",
                    p_LogStreamName="BackupDelivery",
                ),
                p_S3BackupMode="AllDocuments",
                rp_S3Configuration=kinesisfirehose.PropDeliveryStreamS3DestinationConfiguration(
                    rp_BucketARN=self.s3_data_bucket.rv_Arn,
                    rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
                    p_Prefix="to-oss/01-backup/",
                    p_ErrorOutputPrefix="to-oss/02-backup-failed/",
                    p_BufferingHints=kinesisfirehose.PropDeliveryStreamBufferingHints(
                        p_IntervalInSeconds=60,
                        p_SizeInMBs=5,
                    ),
                ),
                p_ProcessingConfiguration=kinesisfirehose.PropDeliveryStreamProcessingConfiguration(
                    p_Enabled=True,
                    p_Processors=[
                        kinesisfirehose.PropDeliveryStreamProcessor(
                            rp_Type="Lambda",
                            p_Parameters=[
                                kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                    rp_ParameterName="LambdaArn",
                                    rp_ParameterValue=f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{self.lbd_func_name_transformation_for_oss}",
                                ),
                                kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                    rp_ParameterName="NumberOfRetries",
                                    rp_ParameterValue="1",
                                ),
                                kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                    rp_ParameterName="RoleArn",
                                    rp_ParameterValue=self.iam_role_for_firehose.rv_Arn,
                                ),
                                kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                    rp_ParameterName="BufferSizeInMBs",
                                    rp_ParameterValue="3",
                                ),
                                kinesisfirehose.PropDeliveryStreamProcessorParameter(
                                    rp_ParameterName="BufferIntervalInSeconds",
                                    rp_ParameterValue="60",
                                ),
                            ]
                        )
                    ]
                )
            ),
            ra_DependsOn=[
                self.iam_role_for_firehose,
                self.kinesis_data_stream,
            ]
        )
        self.rg6_kinesis_delivery_stream_to_oss.add(self.kinesis_delivery_stream_to_oss)

        self.delivery_stream_to_oss_lbd_permission = awslambda.Permission(
            "DeliveryStreamToOSSLbdPermission",
            rp_Action="lambda:InvokeFunction",
            rp_FunctionName=f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{self.lbd_func_name_transformation_for_oss}",
            rp_Principal="firehose.amazonaws.com",
            p_SourceArn=self.kinesis_delivery_stream_to_oss.rv_Arn,
        )
        self.rg6_kinesis_delivery_stream_to_oss.add(self.delivery_stream_to_oss_lbd_permission)

    def post_hook(self):
        self.mk_rg1_data_bucket()
        self.mk_rg2_iam_permission()
        self.mk_rg3_opensearch()
        self.mk_rg4_kinesis_data_stream()
        self.mk_rg5_kinesis_delivery_stream_to_s3()
        self.mk_rg6_kinesis_delivery_stream_to_oss()


stack = Stack(
    project_name=config.project_name,
    stage=config.stage,
    aws_account_id=aws_account_id,
    aws_region=aws_region,
    oss_index_name=config.oss_index_name,
)

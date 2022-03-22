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

from typing import List
import attr
import cottonformation as cft
from cottonformation.res import (
    s3, iam, opensearchservice, kinesis, kinesisfirehose, awslambda,
)

from ..config import config
from ..boto_ses import aws_account_id, aws_region


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
        return self.project_name.replace("-", "_")

    @property
    def s3_data_bucket_name(self) -> str:
        return f"{self.aws_account_id}-{self.aws_region}-{self.project_name_slug}"

    @property
    def iam_role_name_for_lbd(self) -> str:
        return f"{self.project_name}-for-lambda"

    @property
    def iam_role_name_for_firehose(self) -> str:
        return f"{self.project_name}-for-firehose"

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
                    "Resource": [
                                    f"arn:aws:logs:{self.aws_region}:{self.aws_account_id}:log-group:/aws/kinesisfirehose/{name}:log-stream:*"
                                    for name in self.all_kinesis_delivery_stream_name
                                ] + [
                                    f"arn:aws:logs:{self.aws_region}:{self.aws_account_id}:log-group:%FIREHOSE_POLICY_TEMPLATE_PLACEHOLDER%:log-stream:*"
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
            p_ManagedPolicyName=f"{self.project_name}-for-firehose",
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

        self.kinesis_delivery_stream_to_s3 = kinesisfirehose.DeliveryStream(
            "KinesisDeliveryStreamToS3",
            p_DeliveryStreamName=self.kinesis_delivery_stream_name_for_s3,
            p_DeliveryStreamType="KinesisStreamAsSource",
            p_KinesisStreamSourceConfiguration=kinesisfirehose.PropDeliveryStreamKinesisStreamSourceConfiguration(
                rp_KinesisStreamARN=self.kinesis_data_stream.rv_Arn,
                rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
            ),
            p_ExtendedS3DestinationConfiguration=kinesisfirehose.PropDeliveryStreamExtendedS3DestinationConfiguration(
                rp_BucketARN=self.s3_data_bucket.rv_Arn,
                rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
                p_Prefix="to-s3/03-success/",
                p_ErrorOutputPrefix="to-s3/04-failed/",
                p_BufferingHints=kinesisfirehose.PropDeliveryStreamBufferingHints(
                    p_IntervalInSeconds=60,
                    p_SizeInMBs=5,
                ),
                p_CloudWatchLoggingOptions=kinesisfirehose.PropDeliveryStreamCloudWatchLoggingOptions(
                    p_Enabled=True,
                    p_LogGroupName=f"/aws/kinesis/firehose/{self.kinesis_delivery_stream_name_for_s3}",
                    p_LogStreamName="BackupDelivery",
                ),
                p_S3BackupMode="Enabled",
                p_S3BackupConfiguration=kinesisfirehose.PropDeliveryStreamS3DestinationConfiguration(
                    rp_BucketARN=self.s3_data_bucket.rv_Arn,
                    rp_RoleARN=self.iam_role_for_firehose.rv_Arn,
                    p_Prefix="to-s3/01-backup/",
                    p_ErrorOutputPrefix="to-s3/02-backup-failed/",
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
                                    rp_ParameterValue=f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{self.lbd_func_name_transformation_for_s3}",
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
        self.rg5_kinesis_delivery_stream_to_s3.add(self.kinesis_delivery_stream_to_s3)

        self.delivery_stream_to_s3_lbd_permission = awslambda.Permission(
            "DeliveryStreamToS3LbdPermission",
            rp_Action="lambda:InvokeFunction",
            rp_FunctionName=f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{self.lbd_func_name_transformation_for_s3}",
            rp_Principal="firehose.amazonaws.com",
            p_SourceArn=self.kinesis_delivery_stream_to_s3.rv_Arn,
        )
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
    project_name=config.project_name_slug,
    stage=config.stage,
    aws_account_id=aws_account_id,
    aws_region=aws_region,
    oss_index_name=config.oss_index_name,
)

#!/bin/bash

func_name="kds-to-oss"
stream_name="kds-to-anything-to-s3"

# https://docs.aws.amazon.com/cli/latest/reference/lambda/index.html#cli-aws-lambda
#aws lambda get-function --function-name ${func_name}
#aws lambda get-function-configuration --function-name ${func_name}
#aws lambda get-function-event-invoke-config --function-name ${func_name}
#aws lambda get-function-event-invoke-config --function-name ${func_name}
#aws lambda get-policy --function-name ${func_name}

# https://docs.aws.amazon.com/cli/latest/reference/firehose/index.html#cli-aws-firehose
aws firehose describe-delivery-stream --delivery-stream-name ${stream_name}
#aws sts get-caller-identity
#aws s3 ls
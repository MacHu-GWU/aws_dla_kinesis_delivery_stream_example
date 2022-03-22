# -*- coding: utf-8 -*-

from chalice import Chalice, AuthResponse
from kds_example import __chalice_app_name__
from kds_example.lbd import to_s3, to_oss

# define a Chalice app
app = Chalice(app_name=__chalice_app_name__)


# a pure native lambda function
# NOTE: if you update the function name, you also need to update the
#  cloudformation template in iac/s2_app.py file,
#  near the kinesis delivery stream code blocks
@app.lambda_function(name="to_s3")
def handler_to_s3(event, context):
    return to_s3.handler(event, context)


@app.lambda_function(name="to_oss")
def handler_to_oss(event, context):
    return to_oss.handler(event, context)

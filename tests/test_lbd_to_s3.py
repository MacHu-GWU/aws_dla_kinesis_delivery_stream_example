# -*- coding: utf-8 -*-

import json
import base64
import pytest
from kds_example.lbd.to_s3 import handler


def test_handler():
    raw_record = {"id": 1}
    event = {
        "invocationId": "invocationIdExample",
        "deliveryStreamArn": "arn:aws:kinesis:EXAMPLE",
        "region": "us-east-1",
        "records": [
            {
                "recordId": "49546986683135544286507457936321625675700192471156785154",
                "approximateArrivalTimestamp": 1495072949453,
                "data": base64.b64encode((json.dumps(raw_record) + "\n").encode("utf-8")).decode("utf-8")
            }
        ]
    }
    response = handler(event=event, context=None)
    output_record = json.loads(base64.b64decode(response["records"][0]["data"]).decode("utf-8"))
    assert raw_record == output_record


if __name__ == "__main__":
    import os

    basename = os.path.basename(__file__)
    pytest.main([basename, "-s", "--tb=native"])

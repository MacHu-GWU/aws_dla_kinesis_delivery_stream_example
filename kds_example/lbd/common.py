# -*- coding: utf-8 -*-

import json
import base64


def delivery_stream_tranformation_handler(
    event: dict,
    transform_func: callable,
):
    output = []
    for record in event["records"]:
        # convert the data back to raw record
        raw_record = json.loads(
            base64.b64decode(
                record["data"].decode("utf-8")
            )
        )

        # Do custom processing on the payload here
        transformed_record = transform_func(raw_record)

        # convert transformed data to output
        output_record = {
            "recordId": record["recordId"],
            "result": "Ok",  # "OK" | "Dropped" | "ProcessingFailed"
            "data": base64.b64encode(
                (json.dumps(transformed_record) + "\n").encode("utf-8")
            )
        }
        output.append(output_record)

    return {"records": output}

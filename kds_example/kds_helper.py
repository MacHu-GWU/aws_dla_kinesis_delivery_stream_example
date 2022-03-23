# -*- coding: utf-8 -*-

import json
import base64
from typing import List, Dict, Iterable, Any, Callable


def put_records(
    kinesis_client,
    records: Iterable[Dict[str, Any]],
    get_pk: Callable[[dict], str],
) -> str:
    kin_records = [
        {
            "Data": (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8"),
            "PartitionKey": get_pk(record),
        }
        for record in records
    ]
    return k_client.put_records(
        Records=kin_records,
        StreamName=stream_name,
    )


class DropIt(Exception): pass


def delivery_stream_tranformation_handler(
    event: dict,
    transform_func: callable,
):
    output = []
    for record in event["records"]:
        # convert the data back to raw record
        raw_record = json.loads(
            base64.b64decode(
                record["data"].encode("utf-8")
            )
        )

        # Do custom processing on the payload here
        try:
            transformed_record = transform_func(raw_record)
            status = "OK"
        except DropIt:
            transformed_record = raw_record
            status = "Dropped"
        except Exception as e:
            transformed_record = raw_record
            status = "ProcessingFailed"

        # convert transformed data to output
        output_record = {
            "recordId": record["recordId"],
            "result": status,
            "data": base64.b64encode(
                (json.dumps(transformed_record) + "\n").encode("utf-8")
            )
        }
        output.append(output_record)

    return {"records": output}

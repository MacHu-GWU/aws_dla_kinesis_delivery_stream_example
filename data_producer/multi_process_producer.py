# -*- coding: utf-8 -*-

"""
This script use multiple CPU core to simulate many data producers for load test.
"""

import time
import json
import uuid
from datetime import datetime
from mpire import WorkerPool
from faker import Faker
from kds_example.boto_ses import boto_ses
from kds_example.iac.s2_app import stack

# print(os.cpu_count())

k_client = boto_ses.client("kinesis")
stream_name = stack.kinesis_data_stream_name
n_records_per_api = 100  # must <= 500

api_invoke_count = list()
st = datetime.now()


def run_producer(api_invoke_count: list, producer_id: int):
    fake = Faker()
    n_sent = 0
    for _ in range(10):
        time.sleep(1)
        raw_records = [
            {
                "id": str(uuid.uuid4()),
                "firstname": fake.first_name(),
                "lastname": fake.last_name(),
                "description": fake.sentence(nb_words=10),
                "balance": 0,
            }
            for _ in range(n_records_per_api)
        ]
        kin_records = [
            dict(
                Data=(json.dumps(raw_record) + "\n").encode("utf-8"),
                PartitionKey=raw_record["id"],
            )
            for raw_record in raw_records
        ]
        response = k_client.put_records(
            Records=kin_records,
            StreamName=stream_name,
        )

        api_invoke_count.append(1)
        n_sent += n_records_per_api
        et = datetime.now()
        elapse = (et - st).total_seconds()
        total_n_sent = len(api_invoke_count) * n_records_per_api
        tps = int(total_n_sent / elapse)
        print(f"this is producer: {producer_id}, has sent {n_sent} records. all producer has sent {total_n_sent} records. tps = {tps} records / sec")


if __name__ == "__main__":
    n_jobs = 8
    args = [
        dict(producer_id=i)
        for i in range(1, 1 + n_jobs)
    ]

    st = datetime.now()

    with WorkerPool(
        n_jobs=n_jobs,
        shared_objects=api_invoke_count,
        start_method="threading",
    ) as pool:
        results = pool.map(run_producer, args)

    et = datetime.now()
    elapse = (et - st).total_seconds()
    print("elapse %.2f sec" % elapse)
    print(f"has sent {len(api_invoke_count) * n_records_per_api}")

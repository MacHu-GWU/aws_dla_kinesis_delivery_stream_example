# -*- coding: utf-8 -*-

"""
Test opensearch connection.
"""

from kds_example.oss_conn import oss
from rich import print as rprint
from kds_example import oss_utils

def create_index_with_mapping():
    """
    Create the test index with proper settings and mappings
    """
    index = "bank_account"
    body = {
        "settings": {
            "number_of_shards": 24,
            "number_of_replicas": 2,
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "firstname": {"type": "keyword"},
                "lastname": {"type": "keyword"},
                "balance": {"type": "integer"},
                "description": {"type": "text"},
            },
        },
    }
    res = oss.indices.create(index=index, body=body, ignore=[400,])
    rprint(res)

#--- Test if the OpenSearch
index = "test_index"
# rprint(oss.index(index=index, id=1, body={"id": 1, "name": "Alice"}))
# rprint(oss.count(index=index, body={"query": {"match_all": {}}}))
# rprint(oss.delete_by_query(index=index, body={"query": {"match_all": {}}}))

#--- Create the test index with proper settings and mappings
create_index_with_mapping()

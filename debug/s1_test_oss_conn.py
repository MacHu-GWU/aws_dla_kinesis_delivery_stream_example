# -*- coding: utf-8 -*-

"""
Test opensearch connection.
"""

from kds_example.oss_conn import oss
from rich import print as rprint
from kds_example import oss_utils

index = "test_index"
rprint(oss.index(index=index, id=1, body={"id": 1, "name": "Alice"}))
rprint(oss.count(index=index, body={"query": {"match_all": {}}}))
rprint(oss.delete_by_query(index=index, body={"query": {"match_all": {}}}))

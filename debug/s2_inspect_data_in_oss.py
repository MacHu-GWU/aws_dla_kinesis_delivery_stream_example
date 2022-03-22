# -*- coding: utf-8 -*-

"""
Test opensearch connection.
"""

from kds_example.oss_conn import oss
from kds_example.config import config
from rich import print as rprint
from kds_example import oss_utils

index = config.oss_index_name

# rprint(oss.search(index=index, body={"query": {"match_all": {}}}))
# rprint(oss_utils.count_documents(oss, index=index))
# rprint(oss_utils.delete_all_documents(oss, index=index))

# -*- coding: utf-8 -*-

"""
Opensearch helpers
"""

import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection


def create_opensearch_connection(
    boto_ses: boto3.session.Session,
    aws_region: str,
    es_endpoint: str,
    test: bool = True,
) -> OpenSearch:
    """
    Create an AWS Opensearch connection to a domain.
    """
    if es_endpoint.startswith("https://"):
        es_endpoint = es_endpoint.replace("https://", "", 1)
    credentials = boto_ses.get_credentials()
    aws_auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        aws_region,
        "es",
        session_token=credentials.token,
    )
    oss = OpenSearch(
        hosts=[{"host": es_endpoint, "port": 443}],
        http_auth=aws_auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    if test:
        oss.info()
    return oss


match_all_query = {"query": {"match_all": {}}}


def count_documents(oss: OpenSearch, index: str) -> dict:
    return oss.count(index=index, body=match_all_query)


def delete_all_documents(oss: OpenSearch, index: str) -> dict:
    return oss.delete_by_query(index=index, body=match_all_query)


def delete_index_if_exists(oss: OpenSearch, index: str) -> dict:
    return oss.indices.delete(index=index, ignore=[400, 404])


def create_index_if_not_exists(
    oss: OpenSearch,
    index: str,
    body: dict = None,
):
    return oss.indices.create(index=index, body=body)

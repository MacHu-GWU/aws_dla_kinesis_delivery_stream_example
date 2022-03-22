# -*- coding: utf-8 -*-

from .common import delivery_stream_tranformation_handler


def transform(dct: dict) -> dict:
    return dct


def handler(event, context):
    return delivery_stream_tranformation_handler(event, transform)

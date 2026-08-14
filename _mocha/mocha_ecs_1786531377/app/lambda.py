"""API Gateway REST API (Lambda proxy integration, v1) handler.

The proxy integration passes the raw HTTP request in a flat structure and
expects a response shaped like {statusCode, headers, body}.
"""

import base64
import json
import logging

import boto3
from boto3.dynamodb.conditions import Key, Attr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_resource(region="us-east-1"):
    return boto3.resource("dynamodb", region_name=region)


def ddbr_put_item(resource, table, item):
    """item uses plain Python types, e.g. {"id": "1", "n": 5}."""
    return resource.Table(table).put_item(Item=item)

def _parse_body(event):
    body = event.get("body")
    if body is None:
        return None
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return body


def lambda_handler(event, context):
    method = event.get("httpMethod")
    path = event.get("path")
    path_params = event.get("pathParameters") or {}
    query = event.get("queryStringParameters") or {}
    body = _parse_body(event)
    
    logger.info("%s %s params=%s query=%s", method, path, path_params, query)
    resource = get_resource()
    table = "green-tree"

    data = {
        "treeId": body.get("treeId"),
        "treeName": body.get("treeName")
    }
    
    result = ddbr_put_item(resource, table, data)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "ok", "received": result}),
    }

"""API Gateway REST API (Lambda proxy integration, v1) handler.

The proxy integration passes the raw HTTP request in a flat structure and
expects a response shaped like {statusCode, headers, body}.
"""

import base64
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    payload = {
        "method": method,
        "path": path,
        "orderId": path_params.get("orderId"),
        "query": query,
        "body": body,
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "ok", "received": payload}),
    }

"""API Gateway HTTP API (payload format v2) handler.

The v2 payload nests HTTP details under requestContext.http and, with the
simple response format enabled, you can return a plain dict/string and API
Gateway will serialize it. Here we return the explicit structured form.
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
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method")
    path = http.get("path")
    path_params = event.get("pathParameters") or {}
    query = event.get("queryStringParameters") or {}
    body = _parse_body(event)

    logger.info("%s %s route=%s", method, path, event.get("routeKey"))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": "ok",
                "orderId": path_params.get("orderId"),
                "query": query,
                "body": body,
            }
        ),
    }

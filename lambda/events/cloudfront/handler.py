"""CloudFront → Lambda Function URL origin handler.

When CloudFront uses a Function URL as the origin, Lambda does *not* get a
Lambda@Edge `Records[0].cf` event. It gets the same payload shape as API
Gateway HTTP API v2 / Function URL (`version: "2.0"`).

CloudFront fingerprints in the event:
  - headers.via contains "(CloudFront)"
  - cloudfront-* viewer headers (country, device type, address, …)
  - x-amz-cf-id is the CloudFront request id
  - with OAC (AWS_IAM auth on the URL), requestContext.authorizer.iam is set
  - requestContext.http.sourceIp is a CloudFront edge IP, not the viewer;
    use x-forwarded-for / cloudfront-viewer-address for the client

Return the Function URL response shape: {statusCode, headers, body}.
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


def _viewer_ip(event):
    headers = event.get("headers") or {}
    # Prefer the CloudFront-specific header when present.
    address = headers.get("cloudfront-viewer-address")
    if address:
        return address.rsplit(":", 1)[0]
    xff = headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return event.get("requestContext", {}).get("http", {}).get("sourceIp")


def lambda_handler(event, context):
    headers = event.get("headers") or {}
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method")
    path = http.get("path") or event.get("rawPath")
    query = event.get("queryStringParameters") or {}
    body = _parse_body(event)

    via = headers.get("via", "")
    from_cloudfront = "(CloudFront)" in via
    country = headers.get("cloudfront-viewer-country")
    cf_id = headers.get("x-amz-cf-id")
    viewer_ip = _viewer_ip(event)

    iam = (event.get("requestContext") or {}).get("authorizer", {}).get("iam") or {}
    oac_arn = iam.get("userArn")

    logger.info(
        "%s %s from_cf=%s country=%s viewer=%s cf_id=%s oac=%s",
        method,
        path,
        from_cloudfront,
        country,
        viewer_ip,
        cf_id,
        oac_arn,
    )

    if path and path.startswith("/admin"):
        return {
            "statusCode": 403,
            "headers": {"Content-Type": "text/plain"},
            "body": "Forbidden",
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": "ok",
                "path": path,
                "query": query,
                "body": body,
                "fromCloudFront": from_cloudfront,
                "viewerCountry": country,
                "viewerIp": viewer_ip,
            }
        ),
    }

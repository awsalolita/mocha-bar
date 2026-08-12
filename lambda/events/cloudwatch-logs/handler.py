"""CloudWatch Logs subscription filter handler.

The payload in `awslogs.data` is base64-encoded, then gzip-compressed JSON.
After decoding you get a `logEvents` list. `messageType` is CONTROL_MESSAGE
(a periodic connectivity check you can ignore) or DATA_MESSAGE.
"""

import base64
import gzip
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def decode(event):
    compressed = base64.b64decode(event["awslogs"]["data"])
    return json.loads(gzip.decompress(compressed))


def lambda_handler(event, context):
    data = decode(event)

    if data.get("messageType") == "CONTROL_MESSAGE":
        return {"skipped": "control message"}

    log_group = data.get("logGroup")
    events = data.get("logEvents", [])
    logger.info("cwlogs group=%s events=%d", log_group, len(events))

    for log_event in events:
        logger.info("[%s] %s", log_event["timestamp"], log_event["message"])

    return {"logGroup": log_group, "processed": len(events)}

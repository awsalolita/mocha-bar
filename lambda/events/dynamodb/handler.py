"""DynamoDB Streams event handler.

Records arrive in the DynamoDB "attribute value" wire format ({"S": ...},
{"N": ...}). `deserialize` flattens a single image into plain Python types.
eventName is one of INSERT | MODIFY | REMOVE.
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _value(attr):
    (dtype, raw), = attr.items()
    if dtype == "N":
        return int(raw) if raw.isdigit() else float(raw)
    if dtype == "BOOL":
        return raw
    if dtype == "NULL":
        return None
    if dtype == "L":
        return [_value(v) for v in raw]
    if dtype == "M":
        return {k: _value(v) for k, v in raw.items()}
    if dtype == "SS":
        return set(raw)
    return raw  # S, B, etc.


def deserialize(image):
    return {k: _value(v) for k, v in (image or {}).items()}


def lambda_handler(event, context):
    for record in event.get("Records", []):
        name = record["eventName"]
        ddb = record["dynamodb"]
        keys = deserialize(ddb.get("Keys"))
        new_image = deserialize(ddb.get("NewImage"))
        old_image = deserialize(ddb.get("OldImage"))

        logger.info("ddb %s keys=%s new=%s old=%s", name, keys, new_image, old_image)

    return {"ok": True}

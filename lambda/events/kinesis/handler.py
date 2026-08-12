"""Kinesis Data Streams event handler.

Each record's `data` field is base64-encoded. Records are delivered in
batches per shard; supports partial batch responses via batchItemFailures.
"""

import base64
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    batch_item_failures = []

    for record in event.get("Records", []):
        seq = record["kinesis"]["sequenceNumber"]
        try:
            raw = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
            try:
                payload = json.loads(raw)
            except (ValueError, TypeError):
                payload = raw

            partition_key = record["kinesis"]["partitionKey"]
            logger.info("kinesis seq=%s pk=%s data=%s", seq, partition_key, payload)
        except Exception:  # noqa: BLE001
            logger.exception("failed to process record %s", seq)
            batch_item_failures.append({"itemIdentifier": seq})

    return {"batchItemFailures": batch_item_failures}

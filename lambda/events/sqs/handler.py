"""SQS event handler.

An SQS trigger delivers a batch of messages. Returning
`batchItemFailures` lets you report only the messages that failed so the
rest are deleted from the queue (requires ReportBatchItemFailures enabled
on the event source mapping).
"""

import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record["messageId"]
        try:
            body = json.loads(record["body"])
        except (ValueError, TypeError):
            body = record["body"]

        attrs = record.get("messageAttributes", {})
        source = attrs.get("source", {}).get("stringValue")

        logger.info("sqs message %s from %s: %s", message_id, source, body)
        # ... business logic here; on failure append to batch_item_failures ...

    return {"batchItemFailures": batch_item_failures}

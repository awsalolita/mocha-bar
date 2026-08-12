"""S3 event handler.

Triggered when objects are created/removed in a bucket. An S3 event can
carry multiple records (one per object action), so always iterate.
"""

import logging
from urllib.parse import unquote_plus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    results = []

    for record in event.get("Records", []):
        s3 = record["s3"]
        bucket = s3["bucket"]["name"]
        # Object keys are URL-encoded in the event (spaces -> '+', etc.).
        key = unquote_plus(s3["object"]["key"])
        size = s3["object"].get("size")
        event_name = record["eventName"]

        logger.info("s3 %s -> s3://%s/%s (%s bytes)", event_name, bucket, key, size)

        results.append(
            {
                "bucket": bucket,
                "key": key,
                "size": size,
                "event": event_name,
                "region": record.get("awsRegion"),
            }
        )

    return {"processed": len(results), "records": results}

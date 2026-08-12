"""SNS event handler.

SNS invokes Lambda synchronously, one Lambda invocation per notification
(records usually has length 1). The actual payload lives in Sns.Message as
a string.
"""

import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    for record in event.get("Records", []):
        sns = record["Sns"]
        subject = sns.get("Subject")
        topic = sns["TopicArn"]
        try:
            message = json.loads(sns["Message"])
        except (ValueError, TypeError):
            message = sns["Message"]

        attrs = {k: v.get("Value") for k, v in sns.get("MessageAttributes", {}).items()}


        logger.info("sns topic=%s subject=%s attrs=%s msg=%s", topic, subject, attrs, message)

    return {"ok": True}

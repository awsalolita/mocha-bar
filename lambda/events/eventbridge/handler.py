"""EventBridge (CloudWatch Events) event handler.

Unlike batch sources, EventBridge delivers a single event object (no
`Records`). Route on `source` + `detail-type`; the payload is in `detail`.
This also covers scheduled rules (source == "aws.events").
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    source = event.get("source")
    detail_type = event.get("detail-type")
    detail = event.get("detail", {})

    logger.info("eventbridge source=%s type=%s detail=%s", source, detail_type, detail)

    if source == "mocha-bar.orders" and detail_type == "Order Placed":
        logger.info("handling new order %s", detail.get("orderId"))

    return {"source": source, "detailType": detail_type, "handled": True}

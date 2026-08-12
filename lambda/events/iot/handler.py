"""AWS IoT Core rule -> Lambda action handler.

An IoT Topic Rule invokes Lambda with a payload that is EXACTLY the JSON
produced by the rule's SQL SELECT. There is no `Records` wrapper. Enrich the
payload in SQL to get routing metadata, e.g.:

    SELECT *, topic() AS topic, topic(2) AS deviceId, timestamp() AS timestamp
    FROM 'devices/+/telemetry'

The invocation is asynchronous, so the return value is ignored by IoT.
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_ALARM_C = 95.0


def _device_from_topic(topic):
    # topic form: devices/{deviceId}/telemetry
    parts = (topic or "").split("/")
    return parts[1] if len(parts) >= 2 else None


def lambda_handler(event, context):
    topic = event.get("topic")
    device_id = event.get("deviceId") or _device_from_topic(topic)
    temperature = event.get("temperature")

    logger.info(
        "iot device=%s topic=%s temp=%s status=%s",
        device_id,
        topic,
        temperature,
        event.get("status"),
    )

    if isinstance(temperature, (int, float)) and temperature >= TEMP_ALARM_C:
        logger.warning("device %s over temp: %s C", device_id, temperature)
        # ... publish an alert / write to a datastore ...

    return {"deviceId": device_id, "processed": True}

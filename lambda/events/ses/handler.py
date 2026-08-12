"""SES inbound email (receipt rule) handler.

SES gives you metadata + verdicts, not the raw email body (store the body in
S3 with an S3 action if you need it). For a synchronous receipt-rule
invocation you may return a `disposition` to STOP_RULE / CONTINUE.
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _verdicts_pass(receipt):
    checks = ["spamVerdict", "virusVerdict", "spfVerdict", "dkimVerdict", "dmarcVerdict"]
    return all(receipt.get(c, {}).get("status") == "PASS" for c in checks)


def lambda_handler(event, context):
    for record in event.get("Records", []):
        ses = record["ses"]
        mail = ses["mail"]
        receipt = ses["receipt"]

        subject = mail["commonHeaders"].get("subject")
        sender = mail["source"]
        recipients = receipt.get("recipients", [])

        clean = _verdicts_pass(receipt)
        logger.info("ses from=%s to=%s subject=%s clean=%s", sender, recipients, subject, clean)

        if not clean:
            # Reject suspicious mail; SES will not run subsequent actions.
            return {"disposition": "STOP_RULE"}

    return {"disposition": "CONTINUE"}

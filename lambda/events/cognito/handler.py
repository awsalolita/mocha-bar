"""Cognito User Pool trigger handler (Pre Sign-up example).

Cognito triggers are synchronous request/response: you MUST return the whole
`event` back, mutating `event["response"]` as needed. `triggerSource` tells
you which lifecycle hook fired (PreSignUp_SignUp, PostConfirmation_*, etc.).
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRUSTED_DOMAINS = {"mocha-bar.example.com"}


def lambda_handler(event, context):
    trigger = event.get("triggerSource")
    attrs = event["request"].get("userAttributes", {})
    email = attrs.get("email", "")

    logger.info("cognito trigger=%s user=%s email=%s", trigger, event.get("userName"), email)

    if trigger == "PreSignUp_SignUp":
        domain = email.split("@")[-1].lower() if "@" in email else ""
        if domain in TRUSTED_DOMAINS:
            # Auto-confirm and verify trusted internal users.
            event["response"]["autoConfirmUser"] = True
            event["response"]["autoVerifyEmail"] = True

    # Always return the (possibly mutated) event to Cognito.
    return event

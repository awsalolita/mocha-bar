"""
SNS unit functions — both CLIENT and RESOURCE interfaces.

client   = boto3.client("sns")
resource = boto3.resource("sns")
"""
import json
import boto3


def get_client(region=None):
    return boto3.client("sns", region_name=region)


def get_resource(region=None):
    return boto3.resource("sns", region_name=region)


# ============================================================
# ---------------------- CLIENT ------------------------------
# ============================================================

def snsc_create_topic(client, name, fifo=False):
    attrs = {}
    if fifo:
        if not name.endswith(".fifo"):
            name += ".fifo"
        attrs["FifoTopic"] = "true"
    return client.create_topic(Name=name, Attributes=attrs)["TopicArn"]


def snsc_list_topics(client):
    return client.list_topics().get("Topics", [])


def snsc_delete_topic(client, topic_arn):
    return client.delete_topic(TopicArn=topic_arn)


def snsc_subscribe(client, topic_arn, protocol, endpoint):
    """protocol: 'email' | 'sms' | 'http'/'https' | 'sqs' | 'lambda'.
    endpoint: email address, phone number, URL, SQS ARN, or Lambda ARN."""
    return client.subscribe(
        TopicArn=topic_arn, Protocol=protocol,
        Endpoint=endpoint, ReturnSubscriptionArn=True)


def snsc_list_subscriptions(client, topic_arn):
    return client.list_subscriptions_by_topic(
        TopicArn=topic_arn).get("Subscriptions", [])


def snsc_unsubscribe(client, subscription_arn):
    return client.unsubscribe(SubscriptionArn=subscription_arn)


def snsc_publish(client, topic_arn, message, subject=None, attributes=None,
                 group_id=None, dedup_id=None):
    kwargs = {"TopicArn": topic_arn, "Message": message}
    if subject:
        kwargs["Subject"] = subject
    if attributes:
        kwargs["MessageAttributes"] = attributes
    if group_id:      # FIFO topic
        kwargs["MessageGroupId"] = group_id
    if dedup_id:      # FIFO topic
        kwargs["MessageDeduplicationId"] = dedup_id
    return client.publish(**kwargs)


def snsc_publish_json(client, topic_arn, payload):
    """Publish a dict as JSON string."""
    return client.publish(TopicArn=topic_arn, Message=json.dumps(payload))


def snsc_publish_sms(client, phone_number, message):
    """Direct SMS, no topic needed. phone_number in E.164 e.g. +15551234567."""
    return client.publish(PhoneNumber=phone_number, Message=message)


def snsc_set_subscription_filter(client, subscription_arn, filter_policy):
    return client.set_subscription_attributes(
        SubscriptionArn=subscription_arn,
        AttributeName="FilterPolicy",
        AttributeValue=json.dumps(filter_policy))


# ============================================================
# --------------------- RESOURCE -----------------------------
# ============================================================

def snsr_create_topic(resource, name):
    return resource.create_topic(Name=name)  # Topic object


def snsr_get_topic(resource, topic_arn):
    return resource.Topic(topic_arn)


def snsr_list_topics(resource):
    return list(resource.topics.all())


def snsr_subscribe(resource, topic, protocol, endpoint):
    """topic = Topic object. Returns Subscription object."""
    return topic.subscribe(
        Protocol=protocol, Endpoint=endpoint, ReturnSubscriptionArn=True)


def snsr_publish(resource, topic, message, subject=None):
    """topic = Topic object."""
    kwargs = {"Message": message}
    if subject:
        kwargs["Subject"] = subject
    return topic.publish(**kwargs)

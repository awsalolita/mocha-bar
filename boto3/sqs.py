"""
SQS unit functions — both CLIENT and RESOURCE interfaces.

client   = boto3.client("sqs")
resource = boto3.resource("sqs")

Note: the client works with QueueUrl; the resource works with Queue objects.
"""
import boto3


def get_client(region=None):
    return boto3.client("sqs", region_name=region)


def get_resource(region=None):
    return boto3.resource("sqs", region_name=region)


# ============================================================
# ---------------------- CLIENT ------------------------------
# ============================================================

def sqsc_create_queue(client, name, fifo=False, attributes=None):
    attrs = dict(attributes or {})
    if fifo:
        if not name.endswith(".fifo"):
            name += ".fifo"
        attrs["FifoQueue"] = "true"
    return client.create_queue(QueueName=name, Attributes=attrs)["QueueUrl"]


def sqsc_get_queue_url(client, name):
    return client.get_queue_url(QueueName=name)["QueueUrl"]


def sqsc_list_queues(client, prefix=None):
    kwargs = {"QueueNamePrefix": prefix} if prefix else {}
    return client.list_queues(**kwargs).get("QueueUrls", [])


def sqsc_delete_queue(client, queue_url):
    return client.delete_queue(QueueUrl=queue_url)


def sqsc_get_queue_attributes(client, queue_url, names=("All",)):
    return client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=list(names))["Attributes"]


def sqsc_send_message(client, queue_url, body, group_id=None, dedup_id=None):
    kwargs = {"QueueUrl": queue_url, "MessageBody": body}
    if group_id:  # FIFO
        kwargs["MessageGroupId"] = group_id
    if dedup_id:  # FIFO
        kwargs["MessageDeduplicationId"] = dedup_id
    return client.send_message(**kwargs)


def sqsc_send_message_batch(client, queue_url, bodies):
    entries = [{"Id": str(i), "MessageBody": b} for i, b in enumerate(bodies)]
    return client.send_message_batch(QueueUrl=queue_url, Entries=entries)


def sqsc_receive_messages(client, queue_url, max_messages=1, wait_seconds=0,
                          visibility_timeout=None):
    kwargs = {"QueueUrl": queue_url,
              "MaxNumberOfMessages": max_messages,
              "WaitTimeSeconds": wait_seconds}  # >0 = long polling
    if visibility_timeout is not None:
        kwargs["VisibilityTimeout"] = visibility_timeout
    return client.receive_message(**kwargs).get("Messages", [])


def sqsc_delete_message(client, queue_url, receipt_handle):
    return client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


def sqsc_purge_queue(client, queue_url):
    return client.purge_queue(QueueUrl=queue_url)


# ============================================================
# --------------------- RESOURCE -----------------------------
# ============================================================

def sqsr_create_queue(resource, name, fifo=False, attributes=None):
    attrs = dict(attributes or {})
    if fifo:
        if not name.endswith(".fifo"):
            name += ".fifo"
        attrs["FifoQueue"] = "true"
    return resource.create_queue(QueueName=name, Attributes=attrs)  # Queue object


def sqsr_get_queue(resource, name):
    return resource.get_queue_by_name(QueueName=name)


def sqsr_list_queues(resource):
    return list(resource.queues.all())


def sqsr_send_message(resource, queue, body, group_id=None, dedup_id=None):
    """queue = Queue object."""
    kwargs = {"MessageBody": body}
    if group_id:
        kwargs["MessageGroupId"] = group_id
    if dedup_id:
        kwargs["MessageDeduplicationId"] = dedup_id
    return queue.send_message(**kwargs)


def sqsr_receive_messages(resource, queue, max_messages=1, wait_seconds=0):
    """Returns Message objects; call msg.delete() to remove."""
    return queue.receive_messages(
        MaxNumberOfMessages=max_messages, WaitTimeSeconds=wait_seconds)


def sqsr_delete_message(message):
    """message = a Message object returned by receive."""
    return message.delete()

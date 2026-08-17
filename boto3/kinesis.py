"""
Kinesis unit functions — CLIENT only (Kinesis has no resource API).

Two separate services live here:
  * Kinesis Data Streams   -> boto3.client("kinesis")   (prefix: kds_)
  * Amazon Data Firehose   -> boto3.client("firehose")  (prefix: kfh_)

Data Streams  = you manage shards, read/write records, replay via iterators.
Firehose      = fully managed delivery to S3 / Redshift / OpenSearch, no shards.
"""
import json
import boto3


def get_client(region=None):
    """Kinesis Data Streams client."""
    return boto3.client("kinesis", region_name=region)


def get_firehose_client(region=None):
    """Amazon Data Firehose (Kinesis Firehose) client."""
    return boto3.client("firehose", region_name=region)


# ============================================================
# ---------------- KINESIS DATA STREAMS (kds) ----------------
# ============================================================

def kds_create_stream(client, name, shard_count=1, on_demand=False):
    """on_demand=True ignores shard_count and uses ON_DEMAND capacity."""
    if on_demand:
        return client.create_stream(
            StreamName=name, StreamModeDetails={"StreamMode": "ON_DEMAND"})
    return client.create_stream(StreamName=name, ShardCount=shard_count)


def kds_delete_stream(client, name):
    return client.delete_stream(StreamName=name)


def kds_wait_stream_exists(client, name):
    client.get_waiter("stream_exists").wait(StreamName=name)


def kds_wait_stream_not_exists(client, name):
    client.get_waiter("stream_not_exists").wait(StreamName=name)


def kds_describe_stream(client, name):
    return client.describe_stream(StreamName=name)["StreamDescription"]


def kds_describe_summary(client, name):
    return client.describe_stream_summary(
        StreamName=name)["StreamDescriptionSummary"]


def kds_list_streams(client):
    return client.list_streams().get("StreamNames", [])


def kds_list_shards(client, name):
    return client.list_shards(StreamName=name).get("Shards", [])


def kds_put_record(client, name, data, partition_key):
    """data: str/bytes/dict. partition_key decides which shard it lands on."""
    if isinstance(data, (dict, list)):
        data = json.dumps(data)
    if isinstance(data, str):
        data = data.encode("utf-8")
    return client.put_record(
        StreamName=name, Data=data, PartitionKey=partition_key)


def kds_put_records(client, name, records):
    """records: list of (data, partition_key) tuples — batched single call."""
    entries = []
    for data, pk in records:
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        if isinstance(data, str):
            data = data.encode("utf-8")
        entries.append({"Data": data, "PartitionKey": pk})
    return client.put_records(StreamName=name, Records=entries)


def kds_get_shard_iterator(client, name, shard_id,
                           iterator_type="TRIM_HORIZON", sequence_number=None):
    """iterator_type: TRIM_HORIZON | LATEST | AT_SEQUENCE_NUMBER |
    AFTER_SEQUENCE_NUMBER | AT_TIMESTAMP."""
    kwargs = {"StreamName": name, "ShardId": shard_id,
              "ShardIteratorType": iterator_type}
    if sequence_number:
        kwargs["StartingSequenceNumber"] = sequence_number
    return client.get_shard_iterator(**kwargs)["ShardIterator"]


def kds_get_records(client, shard_iterator, limit=100):
    """Returns (records, next_shard_iterator)."""
    resp = client.get_records(ShardIterator=shard_iterator, Limit=limit)
    return resp.get("Records", []), resp.get("NextShardIterator")


def kds_read_shard(client, name, shard_id,
                   iterator_type="TRIM_HORIZON", max_records=100):
    """Convenience: open an iterator on a shard and pull one batch of records.
    Each record's raw payload is in record['Data'] (bytes)."""
    shard_iterator = kds_get_shard_iterator(client, name, shard_id, iterator_type)
    records, _ = kds_get_records(client, shard_iterator, limit=max_records)
    return records


def kds_increase_retention(client, name, hours):
    return client.increase_stream_retention_period(
        StreamName=name, RetentionPeriodHours=hours)


def kds_update_shard_count(client, name, target_shard_count):
    return client.update_shard_count(
        StreamName=name, TargetShardCount=target_shard_count,
        ScalingType="UNIFORM_SCALING")


def kds_add_tags(client, name, tags):
    """tags: {"Key": "Value", ...}."""
    return client.add_tags_to_stream(StreamName=name, Tags=tags)


# ============================================================
# --------------- AMAZON DATA FIREHOSE (kfh) -----------------
# ============================================================

def kfh_create_stream_s3(client, name, bucket_arn, role_arn,
                         prefix=None, buffer_mb=5, buffer_seconds=300,
                         compression="UNCOMPRESSED"):
    """Create a Firehose delivery stream that lands data in S3.
    compression: UNCOMPRESSED | GZIP | ZIP | Snappy | HADOOP_SNAPPY."""
    s3_config = {
        "RoleARN": role_arn,
        "BucketARN": bucket_arn,
        "BufferingHints": {"SizeInMBs": buffer_mb,
                           "IntervalInSeconds": buffer_seconds},
        "CompressionFormat": compression,
    }
    if prefix:
        s3_config["Prefix"] = prefix
    return client.create_delivery_stream(
        DeliveryStreamName=name,
        DeliveryStreamType="DirectPut",
        ExtendedS3DestinationConfiguration=s3_config)


def kfh_create_stream_from_kinesis(client, name, source_stream_arn, role_arn,
                                   bucket_arn, s3_role_arn):
    """Firehose whose source is a Kinesis Data Stream, delivering to S3."""
    return client.create_delivery_stream(
        DeliveryStreamName=name,
        DeliveryStreamType="KinesisStreamAsSource",
        KinesisStreamSourceConfiguration={
            "KinesisStreamARN": source_stream_arn, "RoleARN": role_arn},
        ExtendedS3DestinationConfiguration={
            "RoleARN": s3_role_arn, "BucketARN": bucket_arn})


def kfh_delete_stream(client, name):
    return client.delete_delivery_stream(DeliveryStreamName=name)


def kfh_describe_stream(client, name):
    return client.describe_delivery_stream(
        DeliveryStreamName=name)["DeliveryStreamDescription"]


def kfh_list_streams(client):
    return client.list_delivery_streams().get("DeliveryStreamNames", [])


def kfh_put_record(client, name, data):
    """data: str/bytes/dict. Single record into the delivery stream.
    A newline is appended so S3 output stays newline-delimited."""
    if isinstance(data, (dict, list)):
        data = json.dumps(data)
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not data.endswith(b"\n"):
        data += b"\n"
    return client.put_record(DeliveryStreamName=name, Record={"Data": data})


def kfh_put_record_batch(client, name, items):
    """items: list of str/bytes/dict — sent as a single batched call."""
    records = []
    for data in items:
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not data.endswith(b"\n"):
            data += b"\n"
        records.append({"Data": data})
    return client.put_record_batch(DeliveryStreamName=name, Records=records)


def kfh_add_tags(client, name, tags):
    """tags: {"Key": "Value", ...}."""
    tag_list = [{"Key": k, "Value": v} for k, v in tags.items()]
    return client.tag_delivery_stream(DeliveryStreamName=name, Tags=tag_list)

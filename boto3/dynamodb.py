"""
DynamoDB unit functions — both CLIENT and RESOURCE interfaces.

client   = boto3.client("dynamodb")     -> raw API, values are typed {"S": "x"}
resource = boto3.resource("dynamodb")   -> Table object, plain Python types

TIP for the contest: use the RESOURCE (Table) API for item CRUD — no need to
hand-write {"S": ...}/{"N": ...} type descriptors. Use CLIENT for admin ops.
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr


def get_client(region=None):
    return boto3.client("dynamodb", region_name=region)


def get_resource(region=None):
    return boto3.resource("dynamodb", region_name=region)


# ============================================================
# ---------------------- CLIENT ------------------------------
# ============================================================

def ddbc_create_table(client, table, hash_key, hash_type="S",
                      range_key=None, range_type="S", on_demand=True):
    """hash_type/range_type: 'S' | 'N' | 'B'."""
    attr_defs = [{"AttributeName": hash_key, "AttributeType": hash_type}]
    key_schema = [{"AttributeName": hash_key, "KeyType": "HASH"}]
    if range_key:
        attr_defs.append({"AttributeName": range_key, "AttributeType": range_type})
        key_schema.append({"AttributeName": range_key, "KeyType": "RANGE"})
    kwargs = {"TableName": table, "AttributeDefinitions": attr_defs,
              "KeySchema": key_schema}
    if on_demand:
        kwargs["BillingMode"] = "PAY_PER_REQUEST"
    else:
        kwargs["BillingMode"] = "PROVISIONED"
        kwargs["ProvisionedThroughput"] = {
            "ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
    return client.create_table(**kwargs)


def ddbc_delete_table(client, table):
    return client.delete_table(TableName=table)


def ddbc_wait_table_exists(client, table):
    client.get_waiter("table_exists").wait(TableName=table)


def ddbc_describe_table(client, table):
    return client.describe_table(TableName=table)["Table"]


def ddbc_list_tables(client):
    return client.list_tables()["TableNames"]


def ddbc_put_item(client, table, item):
    """item uses typed values, e.g. {"id": {"S": "1"}, "n": {"N": "5"}}."""
    return client.put_item(TableName=table, Item=item)


def ddbc_get_item(client, table, key):
    """key uses typed values, e.g. {"id": {"S": "1"}}."""
    return client.get_item(TableName=table, Key=key).get("Item")


def ddbc_delete_item(client, table, key):
    return client.delete_item(TableName=table, Key=key)


def ddbc_update_item(client, table, key, update_expr, expr_values, expr_names=None):
    kwargs = {"TableName": table, "Key": key,
              "UpdateExpression": update_expr,
              "ExpressionAttributeValues": expr_values}
    if expr_names:
        kwargs["ExpressionAttributeNames"] = expr_names
    return client.update_item(**kwargs)


def ddbc_query(client, table, key_condition_expr, expr_values):
    return client.query(
        TableName=table,
        KeyConditionExpression=key_condition_expr,
        ExpressionAttributeValues=expr_values)


def ddbc_scan(client, table):
    return client.scan(TableName=table).get("Items", [])


# ============================================================
# --------------------- RESOURCE -----------------------------
# ============================================================

def ddbr_create_table(resource, table, hash_key, hash_type="S",
                      range_key=None, range_type="S"):
    attr_defs = [{"AttributeName": hash_key, "AttributeType": hash_type}]
    key_schema = [{"AttributeName": hash_key, "KeyType": "HASH"}]
    if range_key:
        attr_defs.append({"AttributeName": range_key, "AttributeType": range_type})
        key_schema.append({"AttributeName": range_key, "KeyType": "RANGE"})
    return resource.create_table(
        TableName=table,
        AttributeDefinitions=attr_defs,
        KeySchema=key_schema,
        BillingMode="PAY_PER_REQUEST")


def ddbr_get_table(resource, table):
    return resource.Table(table)


def ddbr_put_item(resource, table, item):
    """item uses plain Python types, e.g. {"id": "1", "n": 5}."""
    return resource.Table(table).put_item(Item=item)


def ddbr_get_item(resource, table, key):
    """key uses plain Python types, e.g. {"id": "1"}."""
    return resource.Table(table).get_item(Key=key).get("Item")


def ddbr_delete_item(resource, table, key):
    return resource.Table(table).delete_item(Key=key)


def ddbr_update_item(resource, table, key, update_expr, expr_values, expr_names=None):
    kwargs = {"Key": key, "UpdateExpression": update_expr,
              "ExpressionAttributeValues": expr_values}
    if expr_names:
        kwargs["ExpressionAttributeNames"] = expr_names
    return resource.Table(table).update_item(**kwargs)


def ddbr_query(resource, table, hash_key_name, hash_key_value):
    """Query by partition key using the Key condition helper."""
    return resource.Table(table).query(
        KeyConditionExpression=Key(hash_key_name).eq(hash_key_value)
    ).get("Items", [])


def ddbr_scan(resource, table, filter_attr=None, filter_value=None):
    table_obj = resource.Table(table)
    if filter_attr is not None:
        return table_obj.scan(
            FilterExpression=Attr(filter_attr).eq(filter_value)
        ).get("Items", [])
    return table_obj.scan().get("Items", [])


def ddbr_batch_write(resource, table, items):
    """Efficient bulk insert via batch_writer (auto-batches + retries)."""
    table_obj = resource.Table(table)
    with table_obj.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    return len(items)


def ddbr_scan_all(resource, table):
    """Scan every page (handles LastEvaluatedKey pagination)."""
    table_obj = resource.Table(table)
    items, kwargs = [], {}
    while True:
        resp = table_obj.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return items


# ============================================================
# ----------------- DAX ACCELERATOR HOOK ---------------------
# ============================================================

def get_dax_resource(endpoint_url, region=None):
    """
    Returns an amazondax Table Resource pointing to a DAX cluster discovery endpoint.
    Drop-in replacement for get_resource() — all ddbr_* functions work identically!
    See boto3/dax.py and docs/DAX.md for cluster provisioning and details.
    """
    import amazondax
    kwargs = {"endpoint_url": endpoint_url}
    if region:
        kwargs["region_name"] = region
    return amazondax.AmazonDaxClient.resource(**kwargs)

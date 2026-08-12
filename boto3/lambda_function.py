"""
Lambda unit functions — CLIENT only (no resource API).

client = boto3.client("lambda")

Covers: create/update/delete, invoke (sync/async), env vars, permissions,
aliases/versions, event source mappings (SQS/DynamoDB/Kinesis triggers).
"""
import io
import json
import zipfile
import boto3


def get_client(region=None):
    return boto3.client("lambda", region_name=region)


def zip_single_file(filename="lambda_function.py", code_str=None):
    """Helper: build an in-memory .zip for ZipFile deployment.
    If code_str is None, reads the file from disk."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if code_str is not None:
            zf.writestr(filename, code_str)
        else:
            zf.write(filename)
    buf.seek(0)
    return buf.read()


# ---- Function lifecycle ----
def lmbc_create_function(client, name, role_arn, handler, zip_bytes,
                         runtime="python3.12", timeout=30, memory=128, env=None):
    kwargs = {
        "FunctionName": name,
        "Runtime": runtime,
        "Role": role_arn,
        "Handler": handler,               # e.g. "lambda_function.lambda_handler"
        "Code": {"ZipFile": zip_bytes},
        "Timeout": timeout,
        "MemorySize": memory,
    }
    if env:
        kwargs["Environment"] = {"Variables": env}
    return client.create_function(**kwargs)


def lmbc_create_function_from_s3(client, name, role_arn, handler,
                                 bucket, key, runtime="python3.12"):
    return client.create_function(
        FunctionName=name, Runtime=runtime, Role=role_arn, Handler=handler,
        Code={"S3Bucket": bucket, "S3Key": key})


def lmbc_update_code(client, name, zip_bytes):
    return client.update_function_code(FunctionName=name, ZipFile=zip_bytes)


def lmbc_update_config(client, name, timeout=None, memory=None, env=None, handler=None):
    kwargs = {"FunctionName": name}
    if timeout is not None:
        kwargs["Timeout"] = timeout
    if memory is not None:
        kwargs["MemorySize"] = memory
    if env is not None:
        kwargs["Environment"] = {"Variables": env}
    if handler is not None:
        kwargs["Handler"] = handler
    return client.update_function_configuration(**kwargs)


def lmbc_delete_function(client, name):
    return client.delete_function(FunctionName=name)


def lmbc_get_function(client, name):
    return client.get_function(FunctionName=name)


def lmbc_list_functions(client):
    return client.list_functions().get("Functions", [])


def lmbc_wait_active(client, name):
    client.get_waiter("function_active_v2").wait(FunctionName=name)


# ---- Invocation ----
def lmbc_invoke(client, name, payload=None):
    """Synchronous (RequestResponse). Returns parsed JSON payload."""
    resp = client.invoke(
        FunctionName=name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload or {}).encode())
    body = resp["Payload"].read().decode()
    return {"StatusCode": resp["StatusCode"],
            "FunctionError": resp.get("FunctionError"),
            "Payload": json.loads(body) if body else None}


def lmbc_invoke_async(client, name, payload=None):
    """Fire-and-forget (Event). Returns 202."""
    return client.invoke(
        FunctionName=name,
        InvocationType="Event",
        Payload=json.dumps(payload or {}).encode())


# ---- Permissions (e.g. let S3/SNS/APIGW invoke the function) ----
def lmbc_add_permission(client, name, statement_id, principal, source_arn=None,
                        action="lambda:InvokeFunction"):
    kwargs = {"FunctionName": name, "StatementId": statement_id,
              "Action": action, "Principal": principal}  # e.g. "s3.amazonaws.com"
    if source_arn:
        kwargs["SourceArn"] = source_arn
    return client.add_permission(**kwargs)


# ---- Versions & aliases ----
def lmbc_publish_version(client, name):
    return client.publish_version(FunctionName=name)


def lmbc_create_alias(client, name, alias, version):
    return client.create_alias(
        FunctionName=name, Name=alias, FunctionVersion=version)


# ---- Environment variables (replace whole map) ----
def lmbc_set_env(client, name, env):
    return client.update_function_configuration(
        FunctionName=name, Environment={"Variables": env})


# ---- Event source mappings (SQS / DynamoDB Streams / Kinesis triggers) ----
def lmbc_create_event_source(client, name, source_arn, batch_size=10, enabled=True):
    return client.create_event_source_mapping(
        FunctionName=name, EventSourceArn=source_arn,
        BatchSize=batch_size, Enabled=enabled)


def lmbc_list_event_sources(client, name):
    return client.list_event_source_mappings(
        FunctionName=name).get("EventSourceMappings", [])

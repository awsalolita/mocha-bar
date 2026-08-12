"""
Secrets Manager unit functions — CLIENT only.

client = boto3.client("secretsmanager")
"""
import json
import boto3


def get_client(region=None):
    return boto3.client("secretsmanager", region_name=region)


def sm_create_secret(client, name, secret, description=""):
    """secret: str -> SecretString; dict -> JSON string; bytes -> SecretBinary."""
    kwargs = {"Name": name, "Description": description}
    if isinstance(secret, (dict, list)):
        kwargs["SecretString"] = json.dumps(secret)
    elif isinstance(secret, bytes):
        kwargs["SecretBinary"] = secret
    else:
        kwargs["SecretString"] = secret
    return client.create_secret(**kwargs)


def sm_get_secret(client, secret_id):
    """Returns the SecretString (or bytes if binary)."""
    resp = client.get_secret_value(SecretId=secret_id)
    return resp.get("SecretString", resp.get("SecretBinary"))


def sm_get_secret_json(client, secret_id):
    """Convenience: parse SecretString as JSON dict."""
    return json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])


def sm_put_secret(client, secret_id, secret):
    """Store a new version of an existing secret."""
    if isinstance(secret, (dict, list)):
        secret = json.dumps(secret)
    return client.put_secret_value(SecretId=secret_id, SecretString=secret)


def sm_update_secret(client, secret_id, secret):
    if isinstance(secret, (dict, list)):
        secret = json.dumps(secret)
    return client.update_secret(SecretId=secret_id, SecretString=secret)


def sm_list_secrets(client):
    out, paginator = [], client.get_paginator("list_secrets")
    for page in paginator.paginate():
        out.extend(page.get("SecretList", []))
    return out


def sm_delete_secret(client, secret_id, force=False):
    """force=True skips the recovery window (immediate delete)."""
    if force:
        return client.delete_secret(
            SecretId=secret_id, ForceDeleteWithoutRecovery=True)
    return client.delete_secret(SecretId=secret_id, RecoveryWindowInDays=7)


def sm_rotate_secret(client, secret_id, lambda_arn, days=30):
    return client.rotate_secret(
        SecretId=secret_id,
        RotationLambdaARN=lambda_arn,
        RotationRules={"AutomaticallyAfterDays": days})

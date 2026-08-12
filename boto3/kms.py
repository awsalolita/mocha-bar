"""
KMS unit functions — CLIENT only.

client = boto3.client("kms")

Covers: key create/alias, encrypt/decrypt, data keys (envelope encryption).
"""
import boto3


def get_client(region=None):
    return boto3.client("kms", region_name=region)


def kms_create_key(client, description="", usage="ENCRYPT_DECRYPT"):
    """Returns metadata incl. KeyId."""
    return client.create_key(
        Description=description, KeyUsage=usage)["KeyMetadata"]


def kms_create_alias(client, alias_name, key_id):
    """alias_name must start with 'alias/'."""
    if not alias_name.startswith("alias/"):
        alias_name = "alias/" + alias_name
    return client.create_alias(AliasName=alias_name, TargetKeyId=key_id)


def kms_list_keys(client):
    return client.list_keys().get("Keys", [])


def kms_describe_key(client, key_id):
    return client.describe_key(KeyId=key_id)["KeyMetadata"]


def kms_encrypt(client, key_id, plaintext):
    """plaintext: bytes or str. Returns ciphertext bytes (blob)."""
    if isinstance(plaintext, str):
        plaintext = plaintext.encode()
    return client.encrypt(KeyId=key_id, Plaintext=plaintext)["CiphertextBlob"]


def kms_decrypt(client, ciphertext_blob):
    """KMS finds the key from the blob; returns plaintext bytes."""
    return client.decrypt(CiphertextBlob=ciphertext_blob)["Plaintext"]


def kms_generate_data_key(client, key_id, key_spec="AES_256"):
    """Envelope encryption: returns Plaintext key (use then discard) +
    CiphertextBlob (store this to decrypt the data key later)."""
    resp = client.generate_data_key(KeyId=key_id, KeySpec=key_spec)
    return resp["Plaintext"], resp["CiphertextBlob"]


def kms_enable_rotation(client, key_id):
    return client.enable_key_rotation(KeyId=key_id)


def kms_schedule_deletion(client, key_id, days=7):
    return client.schedule_key_deletion(KeyId=key_id, PendingWindowInDays=days)

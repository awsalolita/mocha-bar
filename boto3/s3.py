"""
S3 unit functions — both CLIENT and RESOURCE interfaces.

client   = boto3.client("s3")   -> low-level, 1:1 with the S3 API
resource = boto3.resource("s3") -> high-level Bucket/Object objects
"""
import boto3
from botocore.exceptions import ClientError


def get_client(region=None):
    return boto3.client("s3", region_name=region)


def get_resource(region=None):
    return boto3.resource("s3", region_name=region)


# ============================================================
# ---------------------- CLIENT ------------------------------
# ============================================================

# ---- Buckets ----
def s3c_create_bucket(client, bucket, region=None):
    """Create a bucket. NOTE: us-east-1 must NOT send LocationConstraint."""
    if region is None or region == "us-east-1":
        return client.create_bucket(Bucket=bucket)
    return client.create_bucket(
        Bucket=bucket,
        CreateBucketConfiguration={"LocationConstraint": region},
    )


def s3c_list_buckets(client):
    return client.list_buckets()["Buckets"]


def s3c_delete_bucket(client, bucket):
    return client.delete_bucket(Bucket=bucket)


def s3c_head_bucket(client, bucket):
    """Check a bucket exists / you have access (raises ClientError otherwise)."""
    return client.head_bucket(Bucket=bucket)


# ---- Objects: upload ----
def s3c_upload_file(client, bucket, key, filename, extra_args=None):
    """Upload from a local path (managed multipart). ExtraArgs e.g. {'ACL':'private'}."""
    return client.upload_file(filename, bucket, key, ExtraArgs=extra_args)


def s3c_upload_fileobj(client, bucket, key, fileobj, extra_args=None):
    """Upload from an open binary file object / stream."""
    return client.upload_fileobj(fileobj, bucket, key, ExtraArgs=extra_args)


def s3c_put_object(client, bucket, key, body):
    """Put raw bytes/str body directly (single request, no multipart)."""
    return client.put_object(Bucket=bucket, Key=key, Body=body)


# ---- Objects: download ----
def s3c_download_file(client, bucket, key, filename):
    return client.download_file(bucket, key, filename)


def s3c_download_fileobj(client, bucket, key, fileobj):
    return client.download_fileobj(bucket, key, fileobj)


def s3c_get_object(client, bucket, key):
    """Returns dict; body bytes via resp['Body'].read()."""
    return client.get_object(Bucket=bucket, Key=key)


# ---- Objects: list / delete / copy ----
def s3c_list_objects(client, bucket, prefix=""):
    """Paginated listing of all keys under prefix."""
    keys = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def s3c_delete_object(client, bucket, key):
    return client.delete_object(Bucket=bucket, Key=key)


def s3c_delete_objects(client, bucket, keys):
    """Bulk delete (max 1000 per call)."""
    return client.delete_objects(
        Bucket=bucket,
        Delete={"Objects": [{"Key": k} for k in keys]},
    )


def s3c_copy_object(client, src_bucket, src_key, dst_bucket, dst_key):
    return client.copy_object(
        Bucket=dst_bucket,
        Key=dst_key,
        CopySource={"Bucket": src_bucket, "Key": src_key},
    )


def s3c_head_object(client, bucket, key):
    """Metadata/size/existence without downloading body."""
    return client.head_object(Bucket=bucket, Key=key)


# ---- Presigned URLs ----
def s3c_presign_get(client, bucket, key, expires=3600):
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires
    )


def s3c_presign_put(client, bucket, key, expires=3600):
    return client.generate_presigned_url(
        "put_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires
    )


def s3c_presign_post(client, bucket, key, expires=3600):
    """Returns {'url':..., 'fields':{...}} for browser form uploads."""
    return client.generate_presigned_post(bucket, key, ExpiresIn=expires)


# ---- Bucket config: versioning / encryption / policy / website / lifecycle ----
def s3c_enable_versioning(client, bucket):
    return client.put_bucket_versioning(
        Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
    )


def s3c_put_encryption(client, bucket, kms_key_id=None):
    """Default SSE. If kms_key_id given -> SSE-KMS, else SSE-S3 (AES256)."""
    if kms_key_id:
        rule = {"ApplyServerSideEncryptionByDefault": {
            "SSEAlgorithm": "aws:kms", "KMSMasterKeyID": kms_key_id}}
    else:
        rule = {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
    return client.put_bucket_encryption(
        Bucket=bucket, ServerSideEncryptionConfiguration={"Rules": [rule]}
    )


def s3c_put_bucket_policy(client, bucket, policy_json):
    """policy_json is a JSON string."""
    return client.put_bucket_policy(Bucket=bucket, Policy=policy_json)


def s3c_get_bucket_policy(client, bucket):
    return client.get_bucket_policy(Bucket=bucket)["Policy"]


def s3c_put_public_access_block(client, bucket, block=True):
    return client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": block, "IgnorePublicAcls": block,
            "BlockPublicPolicy": block, "RestrictPublicBuckets": block},
    )


def s3c_put_website(client, bucket, index="index.html", error="error.html"):
    return client.put_bucket_website(
        Bucket=bucket,
        WebsiteConfiguration={
            "IndexDocument": {"Suffix": index},
            "ErrorDocument": {"Key": error}},
    )


def s3c_put_lifecycle_expire(client, bucket, prefix="", days=30):
    return client.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={"Rules": [{
            "ID": f"expire-{days}d",
            "Filter": {"Prefix": prefix},
            "Status": "Enabled",
            "Expiration": {"Days": days}}]},
    )


def s3c_bucket_exists(client, bucket):
    """Convenience boolean helper using head_bucket."""
    try:
        client.head_bucket(Bucket=bucket)
        return True
    except ClientError:
        return False


# ============================================================
# --------------------- RESOURCE -----------------------------
# ============================================================

# ---- Buckets ----
def s3r_create_bucket(resource, bucket, region=None):
    if region is None or region == "us-east-1":
        return resource.create_bucket(Bucket=bucket)
    return resource.create_bucket(
        Bucket=bucket,
        CreateBucketConfiguration={"LocationConstraint": region},
    )


def s3r_list_buckets(resource):
    return list(resource.buckets.all())


def s3r_delete_bucket(resource, bucket):
    return resource.Bucket(bucket).delete()


# ---- Objects: upload ----
def s3r_upload_file(resource, bucket, key, filename, extra_args=None):
    return resource.Bucket(bucket).upload_file(filename, key, ExtraArgs=extra_args)


def s3r_upload_fileobj(resource, bucket, key, fileobj, extra_args=None):
    return resource.Bucket(bucket).upload_fileobj(fileobj, key, ExtraArgs=extra_args)


def s3r_put_object(resource, bucket, key, body):
    return resource.Object(bucket, key).put(Body=body)


# ---- Objects: download ----
def s3r_download_file(resource, bucket, key, filename):
    return resource.Bucket(bucket).download_file(key, filename)


def s3r_get_object(resource, bucket, key):
    """Returns dict; body via resp['Body'].read()."""
    return resource.Object(bucket, key).get()


# ---- Objects: list / delete / copy ----
def s3r_list_objects(resource, bucket, prefix=""):
    return list(resource.Bucket(bucket).objects.filter(Prefix=prefix))


def s3r_delete_object(resource, bucket, key):
    return resource.Object(bucket, key).delete()


def s3r_delete_all_objects(resource, bucket, prefix=""):
    """Empty a bucket (needed before delete on a non-empty bucket)."""
    return resource.Bucket(bucket).objects.filter(Prefix=prefix).delete()


def s3r_copy_object(resource, src_bucket, src_key, dst_bucket, dst_key):
    return resource.Object(dst_bucket, dst_key).copy(
        {"Bucket": src_bucket, "Key": src_key})


# ---- Config via resource sub-resources ----
def s3r_enable_versioning(resource, bucket):
    return resource.BucketVersioning(bucket).enable()


def s3r_put_bucket_policy(resource, bucket, policy_json):
    return resource.BucketPolicy(bucket).put(Policy=policy_json)

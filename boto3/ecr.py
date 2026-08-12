"""
ECR (Elastic Container Registry) unit functions — CLIENT only.

client = boto3.client("ecr")

Covers: repositories, auth token (for docker login), images, lifecycle policy.
"""
import base64
import boto3


def get_client(region=None):
    return boto3.client("ecr", region_name=region)


def ecr_create_repository(client, name, scan_on_push=True, immutable=False):
    return client.create_repository(
        repositoryName=name,
        imageScanningConfiguration={"scanOnPush": scan_on_push},
        imageTagMutability="IMMUTABLE" if immutable else "MUTABLE",
    )["repository"]


def ecr_delete_repository(client, name, force=True):
    """force=True deletes even if it still contains images."""
    return client.delete_repository(repositoryName=name, force=force)


def ecr_describe_repositories(client):
    return client.describe_repositories()["repositories"]


def ecr_get_login(client):
    """Returns (username, password, registry_url) for `docker login`.
    Usage: docker login -u <user> -p <pass> <registry_url>."""
    resp = client.get_authorization_token()
    data = resp["authorizationData"][0]
    user, password = base64.b64decode(
        data["authorizationToken"]).decode().split(":", 1)
    return user, password, data["proxyEndpoint"]


def ecr_list_images(client, name):
    return client.list_images(repositoryName=name).get("imageIds", [])


def ecr_describe_images(client, name):
    return client.describe_images(repositoryName=name).get("imageDetails", [])


def ecr_delete_image(client, name, tag=None, digest=None):
    image_id = {}
    if tag:
        image_id["imageTag"] = tag
    if digest:
        image_id["imageDigest"] = digest
    return client.batch_delete_image(
        repositoryName=name, imageIds=[image_id])


def ecr_put_lifecycle_policy(client, name, policy_json):
    """policy_json: JSON string (e.g. keep last N images)."""
    return client.put_lifecycle_policy(
        repositoryName=name, lifecyclePolicyText=policy_json)

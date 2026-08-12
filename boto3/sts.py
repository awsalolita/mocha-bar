"""
STS unit functions — CLIENT only.

client = boto3.client("sts")

Covers: caller identity, assume-role, building a session from temp credentials.
"""
import boto3


def get_client(region=None):
    return boto3.client("sts", region_name=region)


def sts_get_caller_identity(client):
    """Who am I? Returns Account, UserId, Arn."""
    return client.get_caller_identity()


def sts_account_id(client):
    return client.get_caller_identity()["Account"]


def sts_assume_role(client, role_arn, session_name="session", duration=3600,
                    external_id=None):
    """Returns the Credentials dict (AccessKeyId/SecretAccessKey/SessionToken)."""
    kwargs = {"RoleArn": role_arn, "RoleSessionName": session_name,
              "DurationSeconds": duration}
    if external_id:
        kwargs["ExternalId"] = external_id
    return client.assume_role(**kwargs)["Credentials"]


def sts_session_from_role(role_arn, session_name="session", region=None):
    """Assume a role and return a ready-to-use boto3.Session using the temp creds.
    Then: s3 = session.client('s3')."""
    creds = boto3.client("sts").assume_role(
        RoleArn=role_arn, RoleSessionName=session_name)["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region)


def sts_get_session_token(client, duration=3600):
    """Temp creds for the current identity (e.g. for MFA-gated calls)."""
    return client.get_session_token(DurationSeconds=duration)["Credentials"]

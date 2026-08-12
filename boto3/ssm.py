"""
SSM (Systems Manager) unit functions — CLIENT only.

client = boto3.client("ssm")

Covers: Parameter Store (String / StringList / SecureString) + Run Command.
"""
import boto3


def get_client(region=None):
    return boto3.client("ssm", region_name=region)


# ---- Parameter Store ----
def ssm_put_parameter(client, name, value, secure=False, overwrite=True,
                      description="", tier="Standard"):
    ptype = "SecureString" if secure else "String"
    return client.put_parameter(
        Name=name, Value=value, Type=ptype,
        Overwrite=overwrite, Description=description, Tier=tier)


def ssm_put_stringlist(client, name, values, overwrite=True):
    """values: list -> stored as comma-separated StringList."""
    return client.put_parameter(
        Name=name, Value=",".join(values),
        Type="StringList", Overwrite=overwrite)


def ssm_get_parameter(client, name, decrypt=True):
    """Returns just the value string."""
    return client.get_parameter(
        Name=name, WithDecryption=decrypt)["Parameter"]["Value"]


def ssm_get_parameters(client, names, decrypt=True):
    """Batch get (max 10). Returns {name: value}."""
    resp = client.get_parameters(Names=names, WithDecryption=decrypt)
    return {p["Name"]: p["Value"] for p in resp["Parameters"]}


def ssm_get_by_path(client, path, decrypt=True, recursive=True):
    """Fetch all params under a path prefix, e.g. '/app/prod/'."""
    out, paginator = {}, client.get_paginator("get_parameters_by_path")
    for page in paginator.paginate(Path=path, Recursive=recursive,
                                   WithDecryption=decrypt):
        for p in page["Parameters"]:
            out[p["Name"]] = p["Value"]
    return out


def ssm_delete_parameter(client, name):
    return client.delete_parameter(Name=name)


# ---- Run Command (execute on EC2 via SSM agent) ----
def ssm_run_shell(client, instance_ids, commands):
    """Run shell commands on Linux instances (AWS-RunShellScript)."""
    return client.send_command(
        InstanceIds=instance_ids,
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands})


def ssm_run_powershell(client, instance_ids, commands):
    return client.send_command(
        InstanceIds=instance_ids,
        DocumentName="AWS-RunPowerShellScript",
        Parameters={"commands": commands})


def ssm_get_command_output(client, command_id, instance_id):
    return client.get_command_invocation(
        CommandId=command_id, InstanceId=instance_id)

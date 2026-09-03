"""
AppConfig unit functions — CLIENT only.

client = boto3.client("appconfig")
data_client = boto3.client("appconfigdata")
"""
import boto3


def get_client(region=None):
    """Returns the AppConfig control plane client."""
    return boto3.client("appconfig", region_name=region)


def get_data_client(region=None):
    """Returns the AppConfig data plane client (for retrieving configs)."""
    return boto3.client("appconfigdata", region_name=region)


# ---- Control Plane (appconfig) ----

def appconfig_create_application(client, name, description=""):
    return client.create_application(Name=name, Description=description)


def appconfig_create_environment(client, app_id, name, description=""):
    return client.create_environment(
        ApplicationId=app_id, Name=name, Description=description)


def appconfig_create_configuration_profile(client, app_id, name, location_uri="hosted", description=""):
    """
    location_uri: 'hosted' for AppConfig hosted config, 
    or an SSM/S3 URI (e.g. ssm-parameter://..., s3://...)
    """
    return client.create_configuration_profile(
        ApplicationId=app_id,
        Name=name,
        LocationUri=location_uri,
        Description=description
    )


def appconfig_create_hosted_configuration_version(client, app_id, profile_id, content, content_type="application/json"):
    """
    content: str or bytes containing the configuration data
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return client.create_hosted_configuration_version(
        ApplicationId=app_id,
        ConfigurationProfileId=profile_id,
        Content=content,
        ContentType=content_type
    )


def appconfig_start_deployment(client, app_id, env_id, profile_id, version, strategy_id="AppConfig.AllAtOnce"):
    """
    Starts a deployment of a configuration version to an environment.
    strategy_id: default is 'AppConfig.AllAtOnce' (AWS managed strategy)
    """
    return client.start_deployment(
        ApplicationId=app_id,
        EnvironmentId=env_id,
        ConfigurationProfileId=profile_id,
        ConfigurationVersion=str(version),
        DeploymentStrategyId=strategy_id
    )


def appconfig_get_deployment(client, app_id, env_id, deployment_number):
    return client.get_deployment(
        ApplicationId=app_id,
        EnvironmentId=env_id,
        DeploymentNumber=deployment_number
    )


def appconfig_list_applications(client):
    out, paginator = [], client.get_paginator("list_applications")
    for page in paginator.paginate():
        out.extend(page.get("Items", []))
    return out


def appconfig_delete_application(client, app_id):
    return client.delete_application(ApplicationId=app_id)


# ---- Data Plane (appconfigdata) ----

def appconfigdata_start_session(data_client, app_id, env_id, profile_id):
    """
    Starts a configuration session and returns the InitialConfigurationToken.
    Note: Identifiers can be IDs or Names.
    """
    resp = data_client.start_configuration_session(
        ApplicationIdentifier=app_id,
        EnvironmentIdentifier=env_id,
        ConfigurationProfileIdentifier=profile_id
    )
    return resp["InitialConfigurationToken"]


def appconfigdata_get_latest_configuration(data_client, token):
    """
    Returns (ConfigurationContent_bytes, NextPollConfigurationToken).
    If no new configuration is available, content will be empty bytes.
    """
    resp = data_client.get_latest_configuration(ConfigurationToken=token)
    content = resp.get("Configuration", b"")
    if hasattr(content, "read"):
        content = content.read()
    return content, resp["NextPollConfigurationToken"]

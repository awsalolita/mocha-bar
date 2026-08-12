"""
IAM unit functions — both CLIENT and RESOURCE interfaces.

client   = boto3.client("iam")
resource = boto3.resource("iam")

Covers: users, groups, roles, policies (managed + inline), access keys,
instance profiles. IAM is global (region is ignored, but accepted).
"""
import json
import boto3


def get_client(region=None):
    return boto3.client("iam", region_name=region)


def get_resource(region=None):
    return boto3.resource("iam", region_name=region)


# ============================================================
# ---------------------- CLIENT ------------------------------
# ============================================================

# ---- Users ----
def iamc_create_user(client, user_name):
    return client.create_user(UserName=user_name)


def iamc_delete_user(client, user_name):
    return client.delete_user(UserName=user_name)


def iamc_list_users(client):
    return client.list_users()["Users"]


def iamc_create_access_key(client, user_name):
    """Returns AccessKeyId + SecretAccessKey (secret shown only once)."""
    return client.create_access_key(UserName=user_name)["AccessKey"]


def iamc_delete_access_key(client, user_name, access_key_id):
    return client.delete_access_key(UserName=user_name, AccessKeyId=access_key_id)


def iamc_create_login_profile(client, user_name, password, reset_required=True):
    return client.create_login_profile(
        UserName=user_name, Password=password,
        PasswordResetRequired=reset_required)


# ---- Groups ----
def iamc_create_group(client, group_name):
    return client.create_group(GroupName=group_name)


def iamc_add_user_to_group(client, group_name, user_name):
    return client.add_user_to_group(GroupName=group_name, UserName=user_name)


# ---- Managed policies ----
def iamc_create_policy(client, policy_name, policy_document):
    """policy_document: dict OR json string."""
    if isinstance(policy_document, dict):
        policy_document = json.dumps(policy_document)
    return client.create_policy(
        PolicyName=policy_name, PolicyDocument=policy_document)


def iamc_delete_policy(client, policy_arn):
    return client.delete_policy(PolicyArn=policy_arn)


def iamc_attach_user_policy(client, user_name, policy_arn):
    return client.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)


def iamc_attach_group_policy(client, group_name, policy_arn):
    return client.attach_group_policy(GroupName=group_name, PolicyArn=policy_arn)


def iamc_attach_role_policy(client, role_name, policy_arn):
    return client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)


def iamc_detach_role_policy(client, role_name, policy_arn):
    return client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)


# ---- Inline policies ----
def iamc_put_user_inline_policy(client, user_name, policy_name, policy_document):
    if isinstance(policy_document, dict):
        policy_document = json.dumps(policy_document)
    return client.put_user_policy(
        UserName=user_name, PolicyName=policy_name, PolicyDocument=policy_document)


def iamc_put_role_inline_policy(client, role_name, policy_name, policy_document):
    if isinstance(policy_document, dict):
        policy_document = json.dumps(policy_document)
    return client.put_role_policy(
        RoleName=role_name, PolicyName=policy_name, PolicyDocument=policy_document)


# ---- Roles ----
def iamc_create_role(client, role_name, assume_role_policy, description=""):
    """assume_role_policy = trust policy (dict or json str)."""
    if isinstance(assume_role_policy, dict):
        assume_role_policy = json.dumps(assume_role_policy)
    return client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=assume_role_policy,
        Description=description)


def iamc_delete_role(client, role_name):
    return client.delete_role(RoleName=role_name)


def iamc_ec2_trust_policy():
    """Common trust policy allowing EC2 to assume the role."""
    return {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"}]}


# ---- Instance profiles (attach a role to EC2) ----
def iamc_create_instance_profile(client, name):
    return client.create_instance_profile(InstanceProfileName=name)


def iamc_add_role_to_instance_profile(client, profile_name, role_name):
    return client.add_role_to_instance_profile(
        InstanceProfileName=profile_name, RoleName=role_name)


# ============================================================
# --------------------- RESOURCE -----------------------------
# ============================================================

# ---- Users ----
def iamr_create_user(resource, user_name):
    return resource.create_user(UserName=user_name)


def iamr_get_user(resource, user_name):
    user = resource.User(user_name)
    user.load()
    return user


def iamr_list_users(resource):
    return list(resource.users.all())


def iamr_create_access_key(resource, user_name):
    return resource.User(user_name).create_access_key_pair()


def iamr_attach_user_policy(resource, user_name, policy_arn):
    return resource.User(user_name).attach_policy(PolicyArn=policy_arn)


# ---- Groups ----
def iamr_create_group(resource, group_name):
    return resource.create_group(GroupName=group_name)


def iamr_add_user_to_group(resource, group_name, user_name):
    return resource.Group(group_name).add_user(UserName=user_name)


# ---- Roles ----
def iamr_create_role(resource, role_name, assume_role_policy, description=""):
    if isinstance(assume_role_policy, dict):
        assume_role_policy = json.dumps(assume_role_policy)
    return resource.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=assume_role_policy,
        Description=description)


def iamr_attach_role_policy(resource, role_name, policy_arn):
    return resource.Role(role_name).attach_policy(PolicyArn=policy_arn)


# ---- Managed policies ----
def iamr_create_policy(resource, policy_name, policy_document):
    if isinstance(policy_document, dict):
        policy_document = json.dumps(policy_document)
    return resource.create_policy(
        PolicyName=policy_name, PolicyDocument=policy_document)

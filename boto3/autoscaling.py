"""
Auto Scaling (EC2) unit functions — CLIENT only.

asg_client = boto3.client("autoscaling")
ec2_client = boto3.client("ec2")   # launch templates live in EC2

Covers: launch templates, ASG create/update, scaling policies, instance mgmt.
"""
import boto3


def get_client(region=None):
    return boto3.client("autoscaling", region_name=region)


def get_ec2_client(region=None):
    return boto3.client("ec2", region_name=region)


# ---- Launch template (EC2 API) ----
def create_launch_template(ec2_client, name, ami, instance_type="t3.micro",
                           key_name=None, sg_ids=None, user_data_b64=None):
    data = {"ImageId": ami, "InstanceType": instance_type}
    if key_name:
        data["KeyName"] = key_name
    if sg_ids:
        data["SecurityGroupIds"] = sg_ids
    if user_data_b64:
        data["UserData"] = user_data_b64  # must be base64-encoded
    return ec2_client.create_launch_template(
        LaunchTemplateName=name, LaunchTemplateData=data)


# ---- Auto Scaling Group ----
def asg_create(client, name, launch_template_name, min_size, max_size,
               desired, subnet_ids, target_group_arns=None,
               health_check_type="EC2"):
    kwargs = {
        "AutoScalingGroupName": name,
        "LaunchTemplate": {"LaunchTemplateName": launch_template_name,
                           "Version": "$Latest"},
        "MinSize": min_size, "MaxSize": max_size, "DesiredCapacity": desired,
        "VPCZoneIdentifier": ",".join(subnet_ids),
        "HealthCheckType": health_check_type,   # EC2 | ELB
    }
    if target_group_arns:
        kwargs["TargetGroupARNs"] = target_group_arns
    return client.create_auto_scaling_group(**kwargs)


def asg_update(client, name, min_size=None, max_size=None, desired=None):
    kwargs = {"AutoScalingGroupName": name}
    if min_size is not None:
        kwargs["MinSize"] = min_size
    if max_size is not None:
        kwargs["MaxSize"] = max_size
    if desired is not None:
        kwargs["DesiredCapacity"] = desired
    return client.update_auto_scaling_group(**kwargs)


def asg_set_desired(client, name, desired, honor_cooldown=False):
    return client.set_desired_capacity(
        AutoScalingGroupName=name, DesiredCapacity=desired,
        HonorCooldown=honor_cooldown)


def asg_describe(client, names=None):
    kwargs = {"AutoScalingGroupNames": names} if names else {}
    return client.describe_auto_scaling_groups(**kwargs)["AutoScalingGroups"]


def asg_delete(client, name, force=True):
    return client.delete_auto_scaling_group(
        AutoScalingGroupName=name, ForceDelete=force)


# ---- Scaling policies ----
def asg_target_tracking_policy(client, name, policy_name, target_value,
                               metric="ASGAverageCPUUtilization"):
    """Target-tracking: keep metric at target_value (e.g. 50.0 % CPU)."""
    return client.put_scaling_policy(
        AutoScalingGroupName=name,
        PolicyName=policy_name,
        PolicyType="TargetTrackingScaling",
        TargetTrackingConfiguration={
            "PredefinedMetricSpecification": {"PredefinedMetricType": metric},
            "TargetValue": target_value})


def asg_step_policy(client, name, policy_name, adjustment):
    """Simple step scaling: add/remove `adjustment` instances."""
    return client.put_scaling_policy(
        AutoScalingGroupName=name,
        PolicyName=policy_name,
        AdjustmentType="ChangeInCapacity",
        ScalingAdjustment=adjustment)


def asg_attach_target_groups(client, name, target_group_arns):
    return client.attach_load_balancer_target_groups(
        AutoScalingGroupName=name, TargetGroupARNs=target_group_arns)

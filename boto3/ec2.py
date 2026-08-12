"""
EC2 / VPC unit functions — both CLIENT and RESOURCE interfaces.

client   = boto3.client("ec2")
resource = boto3.resource("ec2")

Covers: instances, key pairs, security groups, VPC/subnet/IGW/route tables,
EBS volumes, Elastic IPs, AMIs, tags.
"""
import boto3


def get_client(region=None):
    return boto3.client("ec2", region_name=region)


def get_resource(region=None):
    return boto3.resource("ec2", region_name=region)


# ============================================================
# ---------------------- CLIENT ------------------------------
# ============================================================

# ---- Instances ----
def ec2c_run_instances(client, ami, instance_type="t3.micro", key_name=None,
                       sg_ids=None, subnet_id=None, count=1, user_data=None, tags=None):
    kwargs = {"ImageId": ami, "InstanceType": instance_type,
              "MinCount": count, "MaxCount": count}
    if key_name:
        kwargs["KeyName"] = key_name
    if sg_ids:
        kwargs["SecurityGroupIds"] = sg_ids
    if subnet_id:
        kwargs["SubnetId"] = subnet_id
    if user_data:
        kwargs["UserData"] = user_data
    if tags:
        kwargs["TagSpecifications"] = [{
            "ResourceType": "instance",
            "Tags": [{"Key": k, "Value": v} for k, v in tags.items()]}]
    return client.run_instances(**kwargs)


def ec2c_describe_instances(client, instance_ids=None, filters=None):
    kwargs = {}
    if instance_ids:
        kwargs["InstanceIds"] = instance_ids
    if filters:
        kwargs["Filters"] = filters
    return client.describe_instances(**kwargs)


def ec2c_start_instances(client, instance_ids):
    return client.start_instances(InstanceIds=instance_ids)


def ec2c_stop_instances(client, instance_ids):
    return client.stop_instances(InstanceIds=instance_ids)


def ec2c_reboot_instances(client, instance_ids):
    return client.reboot_instances(InstanceIds=instance_ids)


def ec2c_terminate_instances(client, instance_ids):
    return client.terminate_instances(InstanceIds=instance_ids)


def ec2c_wait_running(client, instance_ids):
    client.get_waiter("instance_running").wait(InstanceIds=instance_ids)


def ec2c_wait_terminated(client, instance_ids):
    client.get_waiter("instance_terminated").wait(InstanceIds=instance_ids)


def ec2c_create_tags(client, resource_ids, tags):
    return client.create_tags(
        Resources=resource_ids,
        Tags=[{"Key": k, "Value": v} for k, v in tags.items()])


# ---- Key pairs ----
def ec2c_create_key_pair(client, name):
    """Returns dict incl. 'KeyMaterial' (the private key PEM)."""
    return client.create_key_pair(KeyName=name)


def ec2c_delete_key_pair(client, name):
    return client.delete_key_pair(KeyName=name)


def ec2c_import_key_pair(client, name, public_key_bytes):
    return client.import_key_pair(KeyName=name, PublicKeyMaterial=public_key_bytes)


# ---- Security groups ----
def ec2c_create_security_group(client, name, description, vpc_id):
    return client.create_security_group(
        GroupName=name, Description=description, VpcId=vpc_id)


def ec2c_authorize_ingress(client, group_id, ip_permissions):
    """ip_permissions: list of IpPermission dicts."""
    return client.authorize_security_group_ingress(
        GroupId=group_id, IpPermissions=ip_permissions)


def ec2c_authorize_ingress_simple(client, group_id, protocol, port, cidr="0.0.0.0/0"):
    return client.authorize_security_group_ingress(
        GroupId=group_id,
        IpPermissions=[{
            "IpProtocol": protocol, "FromPort": port, "ToPort": port,
            "IpRanges": [{"CidrIp": cidr}]}])


def ec2c_revoke_ingress(client, group_id, ip_permissions):
    return client.revoke_security_group_ingress(
        GroupId=group_id, IpPermissions=ip_permissions)


def ec2c_delete_security_group(client, group_id):
    return client.delete_security_group(GroupId=group_id)


# ---- VPC / networking ----
def ec2c_create_vpc(client, cidr="10.0.0.0/16"):
    return client.create_vpc(CidrBlock=cidr)


def ec2c_delete_vpc(client, vpc_id):
    return client.delete_vpc(VpcId=vpc_id)


def ec2c_create_subnet(client, vpc_id, cidr, az=None):
    kwargs = {"VpcId": vpc_id, "CidrBlock": cidr}
    if az:
        kwargs["AvailabilityZone"] = az
    return client.create_subnet(**kwargs)


def ec2c_create_igw(client):
    return client.create_internet_gateway()


def ec2c_attach_igw(client, igw_id, vpc_id):
    return client.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)


def ec2c_create_route_table(client, vpc_id):
    return client.create_route_table(VpcId=vpc_id)


def ec2c_create_route(client, route_table_id, dest_cidr, gateway_id):
    return client.create_route(
        RouteTableId=route_table_id,
        DestinationCidrBlock=dest_cidr,
        GatewayId=gateway_id)


def ec2c_associate_route_table(client, route_table_id, subnet_id):
    return client.associate_route_table(
        RouteTableId=route_table_id, SubnetId=subnet_id)


def ec2c_map_public_ip_on_launch(client, subnet_id, value=True):
    return client.modify_subnet_attribute(
        SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": value})


# ---- Elastic IP ----
def ec2c_allocate_eip(client):
    return client.allocate_address(Domain="vpc")


def ec2c_associate_eip(client, allocation_id, instance_id):
    return client.associate_address(
        AllocationId=allocation_id, InstanceId=instance_id)


def ec2c_release_eip(client, allocation_id):
    return client.release_address(AllocationId=allocation_id)


# ---- EBS volumes ----
def ec2c_create_volume(client, az, size_gib, volume_type="gp3"):
    return client.create_volume(
        AvailabilityZone=az, Size=size_gib, VolumeType=volume_type)


def ec2c_attach_volume(client, volume_id, instance_id, device="/dev/sdf"):
    return client.attach_volume(
        VolumeId=volume_id, InstanceId=instance_id, Device=device)


def ec2c_detach_volume(client, volume_id):
    return client.detach_volume(VolumeId=volume_id)


def ec2c_create_snapshot(client, volume_id, description=""):
    return client.create_snapshot(VolumeId=volume_id, Description=description)


# ---- AMIs ----
def ec2c_create_image(client, instance_id, name, no_reboot=True):
    return client.create_image(
        InstanceId=instance_id, Name=name, NoReboot=no_reboot)


def ec2c_describe_images(client, owners=("self",)):
    return client.describe_images(Owners=list(owners))


# ============================================================
# --------------------- RESOURCE -----------------------------
# ============================================================

# ---- Instances ----
def ec2r_create_instances(resource, ami, instance_type="t3.micro", key_name=None,
                          sg_ids=None, subnet_id=None, count=1):
    kwargs = {"ImageId": ami, "InstanceType": instance_type,
              "MinCount": count, "MaxCount": count}
    if key_name:
        kwargs["KeyName"] = key_name
    if sg_ids:
        kwargs["SecurityGroupIds"] = sg_ids
    if subnet_id:
        kwargs["SubnetId"] = subnet_id
    return resource.create_instances(**kwargs)  # returns list of Instance objects


def ec2r_get_instance(resource, instance_id):
    return resource.Instance(instance_id)


def ec2r_start_instance(resource, instance_id):
    return resource.Instance(instance_id).start()


def ec2r_stop_instance(resource, instance_id):
    return resource.Instance(instance_id).stop()


def ec2r_terminate_instance(resource, instance_id):
    return resource.Instance(instance_id).terminate()


def ec2r_wait_running(resource, instance_id):
    inst = resource.Instance(instance_id)
    inst.wait_until_running()
    return inst


def ec2r_list_instances(resource, filters=None):
    if filters:
        return list(resource.instances.filter(Filters=filters))
    return list(resource.instances.all())


def ec2r_create_tags(resource, instance_id, tags):
    return resource.Instance(instance_id).create_tags(
        Tags=[{"Key": k, "Value": v} for k, v in tags.items()])


# ---- Security groups ----
def ec2r_create_security_group(resource, name, description, vpc_id):
    return resource.create_security_group(
        GroupName=name, Description=description, VpcId=vpc_id)


def ec2r_authorize_ingress(resource, group_id, protocol, port, cidr="0.0.0.0/0"):
    sg = resource.SecurityGroup(group_id)
    return sg.authorize_ingress(
        IpPermissions=[{
            "IpProtocol": protocol, "FromPort": port, "ToPort": port,
            "IpRanges": [{"CidrIp": cidr}]}])


# ---- VPC / subnet ----
def ec2r_create_vpc(resource, cidr="10.0.0.0/16"):
    return resource.create_vpc(CidrBlock=cidr)


def ec2r_create_subnet(resource, vpc_id, cidr, az=None):
    vpc = resource.Vpc(vpc_id)
    kwargs = {"CidrBlock": cidr}
    if az:
        kwargs["AvailabilityZone"] = az
    return vpc.create_subnet(**kwargs)


# ---- Volumes ----
def ec2r_create_volume(resource, az, size_gib, volume_type="gp3"):
    return resource.create_volume(
        AvailabilityZone=az, Size=size_gib, VolumeType=volume_type)

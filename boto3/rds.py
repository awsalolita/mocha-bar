"""
RDS unit functions — CLIENT only.

client = boto3.client("rds")

Covers: DB instances, snapshots, waiters, subnet groups.
"""
import boto3


def get_client(region=None):
    return boto3.client("rds", region_name=region)


def rds_create_instance(client, db_id, engine="mysql", instance_class="db.t3.micro",
                        username="admin", password=None, allocated_gb=20,
                        db_name=None, sg_ids=None, subnet_group=None,
                        multi_az=False, publicly_accessible=False):
    kwargs = {
        "DBInstanceIdentifier": db_id,
        "Engine": engine,                 # mysql | postgres | mariadb | ...
        "DBInstanceClass": instance_class,
        "MasterUsername": username,
        "MasterUserPassword": password,
        "AllocatedStorage": allocated_gb,
        "MultiAZ": multi_az,
        "PubliclyAccessible": publicly_accessible,
    }
    if db_name:
        kwargs["DBName"] = db_name
    if sg_ids:
        kwargs["VpcSecurityGroupIds"] = sg_ids
    if subnet_group:
        kwargs["DBSubnetGroupName"] = subnet_group
    return client.create_db_instance(**kwargs)


def rds_delete_instance(client, db_id, skip_final_snapshot=True):
    return client.delete_db_instance(
        DBInstanceIdentifier=db_id,
        SkipFinalSnapshot=skip_final_snapshot)


def rds_describe_instances(client, db_id=None):
    kwargs = {"DBInstanceIdentifier": db_id} if db_id else {}
    return client.describe_db_instances(**kwargs)["DBInstances"]


def rds_get_endpoint(client, db_id):
    """Returns (address, port) once available."""
    inst = client.describe_db_instances(
        DBInstanceIdentifier=db_id)["DBInstances"][0]
    ep = inst.get("Endpoint", {})
    return ep.get("Address"), ep.get("Port")


def rds_wait_available(client, db_id):
    client.get_waiter("db_instance_available").wait(DBInstanceIdentifier=db_id)


def rds_wait_deleted(client, db_id):
    client.get_waiter("db_instance_deleted").wait(DBInstanceIdentifier=db_id)


def rds_stop_instance(client, db_id):
    return client.stop_db_instance(DBInstanceIdentifier=db_id)


def rds_start_instance(client, db_id):
    return client.start_db_instance(DBInstanceIdentifier=db_id)


def rds_reboot_instance(client, db_id):
    return client.reboot_db_instance(DBInstanceIdentifier=db_id)


# ---- Snapshots ----
def rds_create_snapshot(client, db_id, snapshot_id):
    return client.create_db_snapshot(
        DBInstanceIdentifier=db_id, DBSnapshotIdentifier=snapshot_id)


def rds_restore_from_snapshot(client, new_db_id, snapshot_id,
                              instance_class="db.t3.micro"):
    return client.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=new_db_id,
        DBSnapshotIdentifier=snapshot_id,
        DBInstanceClass=instance_class)


# ---- Subnet group ----
def rds_create_subnet_group(client, name, subnet_ids, description="db subnet group"):
    return client.create_db_subnet_group(
        DBSubnetGroupName=name,
        DBSubnetGroupDescription=description,
        SubnetIds=subnet_ids)

"""
ECS (Elastic Container Service) unit functions — CLIENT only.

client = boto3.client("ecs")

Covers: clusters, task definitions (Fargate/EC2), services, run task, scaling.
"""
import boto3


def get_client(region=None):
    return boto3.client("ecs", region_name=region)


# ---- Clusters ----
def ecs_create_cluster(client, name, fargate=True):
    kwargs = {"clusterName": name}
    if fargate:
        kwargs["capacityProviders"] = ["FARGATE", "FARGATE_SPOT"]
    return client.create_cluster(**kwargs)["cluster"]


def ecs_delete_cluster(client, name):
    return client.delete_cluster(cluster=name)


def ecs_list_clusters(client):
    return client.list_clusters()["clusterArns"]


# ---- Task definitions ----
def ecs_register_task_def(client, family, image, container_name="app",
                          cpu="256", memory="512", port=80,
                          execution_role_arn=None, task_role_arn=None,
                          env=None, log_group=None, region=None):
    """Registers a Fargate-compatible task definition (awsvpc network mode)."""
    container = {
        "name": container_name,
        "image": image,
        "essential": True,
        "portMappings": [{"containerPort": port, "protocol": "tcp"}],
    }
    if env:
        container["environment"] = [{"name": k, "value": v}
                                    for k, v in env.items()]
    if log_group:
        container["logConfiguration"] = {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": log_group,
                "awslogs-region": region,
                "awslogs-stream-prefix": container_name}}
    kwargs = {
        "family": family,
        "requiresCompatibilities": ["FARGATE"],
        "networkMode": "awsvpc",
        "cpu": cpu, "memory": memory,
        "containerDefinitions": [container],
    }
    if execution_role_arn:
        kwargs["executionRoleArn"] = execution_role_arn
    if task_role_arn:
        kwargs["taskRoleArn"] = task_role_arn
    return client.register_task_definition(**kwargs)["taskDefinition"]


def ecs_deregister_task_def(client, task_def):
    return client.deregister_task_definition(taskDefinition=task_def)


# ---- Services ----
def ecs_create_service(client, cluster, name, task_def, desired=1,
                       subnet_ids=None, sg_ids=None, assign_public_ip=True,
                       target_group_arn=None, container_name="app", port=80):
    kwargs = {
        "cluster": cluster,
        "serviceName": name,
        "taskDefinition": task_def,
        "desiredCount": desired,
        "launchType": "FARGATE",
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "subnets": subnet_ids or [],
                "securityGroups": sg_ids or [],
                "assignPublicIp": "ENABLED" if assign_public_ip else "DISABLED"}},
    }
    if target_group_arn:
        kwargs["loadBalancers"] = [{
            "targetGroupArn": target_group_arn,
            "containerName": container_name,
            "containerPort": port}]
    return client.create_service(**kwargs)["service"]


def ecs_update_service(client, cluster, name, desired=None, task_def=None,
                       force_new=False):
    kwargs = {"cluster": cluster, "service": name}
    if desired is not None:
        kwargs["desiredCount"] = desired
    if task_def:
        kwargs["taskDefinition"] = task_def
    if force_new:
        kwargs["forceNewDeployment"] = True
    return client.update_service(**kwargs)["service"]


def ecs_delete_service(client, cluster, name, force=True):
    return client.delete_service(cluster=cluster, service=name, force=force)


def ecs_describe_services(client, cluster, names):
    return client.describe_services(cluster=cluster, services=names)["services"]


def ecs_wait_services_stable(client, cluster, names):
    client.get_waiter("services_stable").wait(cluster=cluster, services=names)


# ---- Run a one-off task ----
def ecs_run_task(client, cluster, task_def, subnet_ids, sg_ids=None,
                 assign_public_ip=True, count=1):
    return client.run_task(
        cluster=cluster,
        taskDefinition=task_def,
        count=count,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnet_ids,
                "securityGroups": sg_ids or [],
                "assignPublicIp": "ENABLED" if assign_public_ip else "DISABLED"}})


def ecs_list_tasks(client, cluster):
    return client.list_tasks(cluster=cluster)["taskArns"]


def ecs_stop_task(client, cluster, task_arn):
    return client.stop_task(cluster=cluster, task=task_arn)

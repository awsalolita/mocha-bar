"""
Elastic Load Balancing v2 (ALB / NLB) unit functions — CLIENT only.

client = boto3.client("elbv2")

Flow: create LB -> create target group -> register targets -> create listener.
"""
import boto3


def get_client(region=None):
    return boto3.client("elbv2", region_name=region)


# ---- Load balancer ----
def elb_create_load_balancer(client, name, subnet_ids, sg_ids=None,
                             scheme="internet-facing", lb_type="application"):
    """lb_type: 'application' (ALB) | 'network' (NLB).
       scheme: 'internet-facing' | 'internal'."""
    kwargs = {"Name": name, "Subnets": subnet_ids,
              "Scheme": scheme, "Type": lb_type}
    if sg_ids and lb_type == "application":
        kwargs["SecurityGroups"] = sg_ids
    return client.create_load_balancer(**kwargs)["LoadBalancers"][0]


def elb_delete_load_balancer(client, lb_arn):
    return client.delete_load_balancer(LoadBalancerArn=lb_arn)


def elb_describe_load_balancers(client, names=None):
    kwargs = {"Names": names} if names else {}
    return client.describe_load_balancers(**kwargs)["LoadBalancers"]


def elb_wait_available(client, lb_arn):
    client.get_waiter("load_balancer_available").wait(LoadBalancerArns=[lb_arn])


# ---- Target group ----
def elb_create_target_group(client, name, vpc_id, port=80, protocol="HTTP",
                            target_type="instance", health_path="/"):
    """target_type: 'instance' | 'ip' | 'lambda'."""
    return client.create_target_group(
        Name=name, Protocol=protocol, Port=port, VpcId=vpc_id,
        TargetType=target_type,
        HealthCheckProtocol=protocol,
        HealthCheckPath=health_path)["TargetGroups"][0]


def elb_register_targets(client, tg_arn, target_ids, port=None):
    """target_ids: instance IDs or IP addresses."""
    targets = [{"Id": t} for t in target_ids]
    if port:
        for t in targets:
            t["Port"] = port
    return client.register_targets(TargetGroupArn=tg_arn, Targets=targets)


def elb_deregister_targets(client, tg_arn, target_ids):
    return client.deregister_targets(
        TargetGroupArn=tg_arn, Targets=[{"Id": t} for t in target_ids])


def elb_target_health(client, tg_arn):
    return client.describe_target_health(
        TargetGroupArn=tg_arn)["TargetHealthDescriptions"]


# ---- Listener ----
def elb_create_listener(client, lb_arn, tg_arn, port=80, protocol="HTTP"):
    return client.create_listener(
        LoadBalancerArn=lb_arn, Protocol=protocol, Port=port,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": tg_arn}]
    )["Listeners"][0]


def elb_create_https_listener(client, lb_arn, tg_arn, cert_arn, port=443):
    return client.create_listener(
        LoadBalancerArn=lb_arn, Protocol="HTTPS", Port=port,
        Certificates=[{"CertificateArn": cert_arn}],
        DefaultActions=[{"Type": "forward", "TargetGroupArn": tg_arn}]
    )["Listeners"][0]


def elb_add_rule(client, listener_arn, tg_arn, path_pattern, priority=1):
    """Path-based routing rule on a listener."""
    return client.create_rule(
        ListenerArn=listener_arn, Priority=priority,
        Conditions=[{"Field": "path-pattern",
                     "PathPatternConfig": {"Values": [path_pattern]}}],
        Actions=[{"Type": "forward", "TargetGroupArn": tg_arn}])

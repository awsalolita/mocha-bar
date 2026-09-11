"""
DAX (DynamoDB Accelerator) unit functions — Control Plane & Data Plane.

Architecture & Overview:
- DAX is a fully managed, highly available, in-memory cache for Amazon DynamoDB.
- Delivers up to a 10x performance improvement — from milliseconds to microseconds.
- DAX is VPC-only: clusters are deployed inside a VPC, across multiple subnets/AZs.
- Port: 8111 (unencrypted) or 9111 (TLS / in-transit encryption).

TWO INTERFACES:
1. CONTROL PLANE (boto3):
   client = boto3.client("dax")
   Used to manage DAX clusters, subnet groups, parameter groups, and node scaling.

2. DATA PLANE (amazondax):
   pip install amazon-dax-client
   Drop-in replacement for boto3 DynamoDB client & resource:
     import amazondax
     dax_resource = amazondax.AmazonDaxClient.resource(endpoint_url="dax://my-cluster.xxxxxx.dax-clusters.region.amazonaws.com")
     table = dax_resource.Table("MyTable")
     item = table.get_item(Key={"id": "123"})["Item"]

KEY CONTEST & PRODUCTION TIPS:
- IAM Service Role: DAX requires a service role with trust relationship `dax.amazonaws.com`
  and permissions to access the underlying DynamoDB tables (e.g., AWSAppRunnerServicePolicyForECRAccess or AmazonDynamoDBFullAccess).
- Caches:
  * Item Cache: Caches results of GetItem and BatchGetItem. Invalidated on PutItem/UpdateItem/DeleteItem.
  * Query Cache: Caches results of Query and Scan with identical parameters.
- Consistency: DAX only caches eventually consistent reads. Strongly consistent reads
  (`ConsistentRead=True`) BYPASS DAX and are passed directly through to DynamoDB!
- Write-Through: Writes (Put/Update/Delete) go to DynamoDB first, then update/invalidate the DAX cache.
"""
import boto3
from typing import Optional, List, Dict, Any

try:
    import amazondax
    AMAZONDAX_AVAILABLE = True
except ImportError:
    amazondax = None
    AMAZONDAX_AVAILABLE = False


# ============================================================
# -------------------- CLIENT FACTORIES ----------------------
# ============================================================

def get_client(region: Optional[str] = None):
    """
    Control-plane Boto3 client for DAX cluster management.
    """
    return boto3.client("dax", region_name=region)


def get_dax_resource(endpoint_url: str, region: Optional[str] = None):
    """
    Data-plane High-Level Table Resource (amazondax.AmazonDaxClient.resource).
    Drop-in replacement for boto3.resource('dynamodb').

    endpoint_url format:
      - 'dax://my-cluster.xxxxxx.dax-clusters.us-east-1.amazonaws.com'
      - or 'my-cluster.xxxxxx.dax-clusters.us-east-1.amazonaws.com:8111'
    """
    if not AMAZONDAX_AVAILABLE:
        raise ImportError(
            "amazon-dax-client is not installed. Install via: pip install amazon-dax-client"
        )
    kwargs = {}
    if region:
        kwargs["region_name"] = region
    return amazondax.AmazonDaxClient.resource(endpoint_url=endpoint_url, **kwargs)


def get_dax_client(endpoints: List[str], region: Optional[str] = None):
    """
    Data-plane Low-Level Client (amazondax.AmazonDaxClient).
    Drop-in replacement for boto3.client('dynamodb').

    endpoints format:
      ['my-cluster.xxxxxx.dax-clusters.us-east-1.amazonaws.com:8111']
    """
    if not AMAZONDAX_AVAILABLE:
        raise ImportError(
            "amazon-dax-client is not installed. Install via: pip install amazon-dax-client"
        )
    kwargs = {}
    if region:
        kwargs["region_name"] = region
    return amazondax.AmazonDaxClient(endpoints=endpoints, **kwargs)


# ============================================================
# ----------------- CONTROL PLANE: CLUSTERS ------------------
# ============================================================

def dax_create_cluster(client,
                       cluster_name: str,
                       node_type: str,
                       iam_role_arn: str,
                       subnet_group_name: str,
                       security_group_ids: List[str],
                       replication_factor: int = 1,
                       description: str = "DAX cluster",
                       parameter_group_name: Optional[str] = None,
                       sse_enabled: bool = False,
                       encryption_type: Optional[str] = None,
                       tags: Optional[List[Dict[str, str]]] = None):
    """
    Create a new DAX cluster.

    node_type: e.g. 'dax.t3.small', 'dax.t2.small', 'dax.r5.large'
    replication_factor: 1 (single primary node) up to 10 (1 primary + 9 read replicas)
    encryption_type: 'NONE' | 'TLS' (in-transit encryption)
    sse_enabled: at-rest encryption
    """
    kwargs: Dict[str, Any] = {
        "ClusterName": cluster_name,
        "NodeType": node_type,
        "Description": description,
        "ReplicationFactor": replication_factor,
        "IamRoleArn": iam_role_arn,
        "SubnetGroupName": subnet_group_name,
        "SecurityGroupIds": security_group_ids,
    }
    if parameter_group_name:
        kwargs["ParameterGroupName"] = parameter_group_name
    if sse_enabled:
        kwargs["SSESpecification"] = {"Enabled": True}
    if encryption_type:
        kwargs["ClusterEndpointEncryptionType"] = encryption_type
    if tags:
        kwargs["Tags"] = tags

    return client.create_cluster(**kwargs)["Cluster"]


def dax_describe_clusters(client, cluster_names: Optional[List[str]] = None):
    """
    Describe all clusters or specific cluster names.
    """
    kwargs = {"ClusterNames": cluster_names} if cluster_names else {}
    return client.describe_clusters(**kwargs).get("Clusters", [])


def dax_get_cluster(client, cluster_name: str):
    """
    Get description dictionary for a single DAX cluster.
    """
    clusters = dax_describe_clusters(client, [cluster_name])
    if not clusters:
        raise ValueError(f"DAX cluster '{cluster_name}' not found.")
    return clusters[0]


def dax_get_cluster_endpoint(client, cluster_name: str):
    """
    Returns discovery URL ('dax://<address>:<port>') and raw (address, port) dict.
    Returns (None, None) if the cluster is still creating.
    """
    cluster = dax_get_cluster(client, cluster_name)
    endpoint = cluster.get("ClusterDiscoveryEndpoint")
    if not endpoint:
        return None, None
    address = endpoint.get("Address")
    port = endpoint.get("Port", 8111)
    dax_url = f"dax://{address}:{port}" if address else None
    return dax_url, {"Address": address, "Port": port}


def dax_delete_cluster(client, cluster_name: str):
    """
    Delete a DAX cluster.
    """
    return client.delete_cluster(ClusterName=cluster_name)["Cluster"]


def dax_increase_replication_factor(client, cluster_name: str, new_factor: int,
                                    availability_zones: Optional[List[str]] = None):
    """
    Scale out by increasing node count.
    """
    kwargs = {"ClusterName": cluster_name, "NewReplicationFactor": new_factor}
    if availability_zones:
        kwargs["AvailabilityZones"] = availability_zones
    return client.increase_replication_factor(**kwargs)["Cluster"]


def dax_decrease_replication_factor(client, cluster_name: str, new_factor: int,
                                    node_ids_to_remove: Optional[List[str]] = None):
    """
    Scale in by decreasing node count.
    """
    kwargs = {"ClusterName": cluster_name, "NewReplicationFactor": new_factor}
    if node_ids_to_remove:
        kwargs["NodeIdsToRemove"] = node_ids_to_remove
    return client.decrease_replication_factor(**kwargs)["Cluster"]


def dax_reboot_node(client, cluster_name: str, node_id: str):
    """
    Reboot a specific DAX node.
    """
    return client.reboot_node(ClusterName=cluster_name, NodeId=node_id)["Cluster"]


# ============================================================
# --------------- CONTROL PLANE: SUBNET GROUPS ---------------
# ============================================================

def dax_create_subnet_group(client, name: str, subnet_ids: List[str],
                            description: str = "DAX subnet group"):
    """
    Create a subnet group for DAX across VPC subnets.
    """
    return client.create_subnet_group(
        SubnetGroupName=name,
        Description=description,
        SubnetIds=subnet_ids
    )["SubnetGroup"]


def dax_describe_subnet_groups(client, names: Optional[List[str]] = None):
    """
    List or describe subnet groups.
    """
    kwargs = {"SubnetGroupNames": names} if names else {}
    return client.describe_subnet_groups(**kwargs).get("SubnetGroups", [])


def dax_delete_subnet_group(client, name: str):
    """
    Delete a subnet group.
    """
    return client.delete_subnet_group(SubnetGroupName=name)


# ============================================================
# -------------- CONTROL PLANE: PARAMETER GROUPS -------------
# ============================================================

def dax_create_parameter_group(client, name: str, description: str = "Custom DAX parameter group"):
    """
    Create a new parameter group to customize TTL.
    """
    return client.create_parameter_group(
        ParameterGroupName=name,
        Description=description
    )["ParameterGroup"]


def dax_modify_parameter_group(client, name: str,
                               record_ttl_ms: Optional[int] = None,
                               query_ttl_ms: Optional[int] = None):
    """
    Modify cache TTL values in milliseconds:
      record_ttl_ms: Item Cache TTL (e.g. 300000 for 5 min, 0 to disable)
      query_ttl_ms:  Query Cache TTL (e.g. 300000 for 5 min, 0 to disable)
    """
    param_values = []
    if record_ttl_ms is not None:
        param_values.append({
            "ParameterName": "record-ttl-millis",
            "ParameterValue": str(record_ttl_ms)
        })
    if query_ttl_ms is not None:
        param_values.append({
            "ParameterName": "query-ttl-millis",
            "ParameterValue": str(query_ttl_ms)
        })
    if not param_values:
        raise ValueError("Must provide at least record_ttl_ms or query_ttl_ms.")

    return client.modify_parameter_group(
        ParameterGroupName=name,
        ParameterNameValues=param_values
    )["ParameterGroup"]


def dax_describe_parameter_groups(client, names: Optional[List[str]] = None):
    """
    Describe parameter groups.
    """
    kwargs = {"ParameterGroupNames": names} if names else {}
    return client.describe_parameter_groups(**kwargs).get("ParameterGroups", [])


def dax_delete_parameter_group(client, name: str):
    """
    Delete a parameter group.
    """
    return client.delete_parameter_group(ParameterGroupName=name)


# ============================================================
# ------------------ CONTROL PLANE: TAGS ---------------------
# ============================================================

def dax_tag_resource(client, resource_arn: str, tags: List[Dict[str, str]]):
    """
    Tag a DAX resource (Cluster ARN).
    tags: [{"Key": "Environment", "Value": "Production"}]
    """
    return client.tag_resource(ResourceName=resource_arn, Tags=tags)


def dax_list_tags(client, resource_arn: str):
    """
    List tags on a DAX resource.
    """
    return client.list_tags(ResourceName=resource_arn).get("Tags", [])


# ============================================================
# -------------------- DATA PLANE (CRUD) ---------------------
# ============================================================

def dax_put_item(dax_resource, table_name: str, item: Dict[str, Any]):
    """
    Put item via DAX (Write-Through: writes to DynamoDB & updates Item Cache).
    Item uses plain Python types with resource Table.
    """
    table = dax_resource.Table(table_name)
    return table.put_item(Item=item)


def dax_get_item(dax_resource, table_name: str, key: Dict[str, Any]):
    """
    Get item via DAX Item Cache (microsecond latency on cache hit).
    Note: DAX only serves cache on EVENTUALLY CONSISTENT reads.
    If you need Strongly Consistent read, it bypasses DAX.
    """
    table = dax_resource.Table(table_name)
    return table.get_item(Key=key).get("Item")


def dax_delete_item(dax_resource, table_name: str, key: Dict[str, Any]):
    """
    Delete item via DAX (removes from DynamoDB & clears from Item Cache).
    """
    table = dax_resource.Table(table_name)
    return table.delete_item(Key=key)


def dax_query(dax_resource, table_name: str, key_condition_expr, expr_values: Optional[Dict[str, Any]] = None):
    """
    Query via DAX Query Cache.
    Results are cached based on exact parameters.
    """
    table = dax_resource.Table(table_name)
    kwargs = {"KeyConditionExpression": key_condition_expr}
    if expr_values:
        kwargs["ExpressionAttributeValues"] = expr_values
    return table.query(**kwargs).get("Items", [])


# ============================================================
# ------------------- IAM HELPER FOR DAX ---------------------
# ============================================================

def get_dax_trust_policy() -> str:
    """
    Trust relationship policy required for the DAX IAM service role.
    """
    return """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "dax.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}"""


def get_dax_dynamodb_policy(table_arn: str = "*") -> str:
    """
    Policy granting DAX permission to execute DynamoDB operations.
    """
    return f"""{{
  "Version": "2012-10-17",
  "Statement": [
    {{
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:ConditionCheckItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": "{table_arn}"
    }}
  ]
}}"""


# ============================================================
# ------------------------ EXAMPLE ---------------------------
# ============================================================

if __name__ == "__main__":
    print("=== DAX Boto3 & AmazonDax Quick Example ===")
    
    # 1. Control plane
    # client = get_client("us-east-1")
    # clusters = dax_describe_clusters(client)
    # print(f"Found {len(clusters)} DAX clusters.")

    # 2. Data plane (inside VPC)
    # endpoint = "dax://my-dax-cluster.xxxxxx.dax-clusters.us-east-1.amazonaws.com"
    # if AMAZONDAX_AVAILABLE:
    #     dax_res = get_dax_resource(endpoint, region="us-east-1")
    #     item = dax_get_item(dax_res, "Users", {"user_id": "u100"})
    #     print("Cached Item:", item)

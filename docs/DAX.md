# DynamoDB Accelerator (DAX) Guide

Amazon DynamoDB Accelerator (DAX) is a fully managed, highly available, in-memory cache for Amazon DynamoDB that delivers up to a 10x performance improvement — reducing response times from single-digit milliseconds to **microseconds**, even at millions of requests per second.

---

## 1. Key Concepts & Architecture

### A. How DAX Works
* **Write-Through Caching**: When your application writes data (`PutItem`, `UpdateItem`, `DeleteItem`), the write is written directly to DynamoDB first, and upon success, DAX updates or invalidates its internal cache.
* **Two Distinct Caches**:
  1. **Item Cache**: Caches results of `GetItem` and `BatchGetItem`. Keyed by partition key and sort key. Default TTL: 5 minutes.
  2. **Query Cache**: Caches results of `Query` and `Scan`. Keyed by query parameters, conditions, and projections. Default TTL: 5 minutes.
* **Read Consistency**:
  * **Eventually Consistent Reads**: Handled by DAX cache (microsecond latency).
  * **Strongly Consistent Reads (`ConsistentRead=True`)**: **BYPASSES DAX** and passes through directly to DynamoDB (costs normal DynamoDB RCUs, millisecond latency).
* **Bypassed Operations**:
  * `TransactGetItems` and `TransactWriteItems` always bypass DAX.

### B. Networking & Security
* **VPC Only**: DAX clusters exist inside a VPC. Applications (EC2, ECS, EKS, Lambda inside VPC) connect directly via private IP.
* **Ports**:
  * `8111`: Default unencrypted endpoint.
  * `9111`: Encrypted endpoint (TLS).
* **Endpoints**:
  * **Cluster Discovery Endpoint**: `dax://<cluster-name>.<random>.<region>.dax-clusters.amazonaws.com:8111`. Client libraries use this discovery endpoint to automatically route reads across all cluster nodes.

---

## 2. Prerequisites Setup

### A. IAM Service Role for DAX
DAX needs an IAM role to access your DynamoDB tables on your behalf.

1. **Trust Policy** (`dax-trust.json`):
```json
{
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
}
```

2. **Permissions Policy** (`dax-policy.json`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
      "Resource": "*"
    }
  ]
}
```

3. **Create Role via CLI**:
```bash
aws iam create-role --role-name DAXServiceRole --assume-role-policy-document file://dax-trust.json
aws iam put-role-policy --role-name DAXServiceRole --policy-name DAXPermissions --policy-document file://dax-policy.json
```

---

## 3. Python & Boto3 Integration

Python interacts with DAX in two layers:
1. **Control Plane** (Creating & managing clusters): Use `boto3.client('dax')` (see [boto3/dax.py](file:///c:/Users/Client/Desktop/mocha-bar/boto3/dax.py)).
2. **Data Plane** (Caching DynamoDB reads & writes): Use `amazon-dax-client` (`amazondax`).

### Installation
```bash
pip install amazon-dax-client boto3
```

### A. High-Level Resource Interface (Recommended)
`amazondax.AmazonDaxClient.resource` is a drop-in replacement for `boto3.resource('dynamodb')`:

```python
import amazondax

DAX_ENDPOINT = "dax://my-dax-cluster.xxxxxx.dax-clusters.us-east-1.amazonaws.com:8111"

# Connect via DAX Resource
dax = amazondax.AmazonDaxClient.resource(endpoint_url=DAX_ENDPOINT)
table = dax.Table("Products")

# 1. GetItem (reads from Item Cache)
response = table.get_item(Key={"product_id": "p-1001"})
item = response.get("Item")
print("Item from DAX:", item)

# 2. PutItem (write-through to DynamoDB + updates cache)
table.put_item(
    Item={
        "product_id": "p-1001",
        "name": "Mocha Espresso",
        "price": 5.99
    }
)

# 3. Query (reads from Query Cache)
from boto3.dynamodb.conditions import Key
result = table.query(
    KeyConditionExpression=Key("product_id").eq("p-1001")
)
print("Query items:", result.get("Items", []))
```

### B. Low-Level Client Interface
`amazondax.AmazonDaxClient` works like `boto3.client('dynamodb')`:

```python
import amazondax

dax_client = amazondax.AmazonDaxClient(
    endpoints=["my-dax-cluster.xxxxxx.dax-clusters.us-east-1.amazonaws.com:8111"]
)

response = dax_client.get_item(
    TableName="Products",
    Key={"product_id": {"S": "p-1001"}}
)
```

### C. Graceful Fallback Pattern (DAX or DynamoDB)
Use this pattern in your application to automatically fall back to direct DynamoDB if DAX endpoint is not configured or in local development:

```python
import os
import boto3

def get_dynamo_resource():
    dax_endpoint = os.getenv("DAX_ENDPOINT")
    if dax_endpoint:
        try:
            import amazondax
            print(f"[DAX] Connecting to DAX endpoint: {dax_endpoint}")
            return amazondax.AmazonDaxClient.resource(endpoint_url=dax_endpoint)
        except Exception as e:
            print(f"[WARN] Failed to init DAX ({e}), falling back to direct DynamoDB")
    
    print("[DynamoDB] Connecting directly to DynamoDB")
    return boto3.resource("dynamodb")
```

---

## 4. Control Plane via Boto3 (`boto3.client("dax")`)

Using the helper functions from [boto3/dax.py](file:///c:/Users/Client/Desktop/mocha-bar/boto3/dax.py):

```python
from boto3.dax import (
    get_client,
    dax_create_subnet_group,
    dax_create_parameter_group,
    dax_modify_parameter_group,
    dax_create_cluster,
    dax_get_cluster_endpoint
)

client = get_client("us-east-1")

# 1. Create Subnet Group
dax_create_subnet_group(
    client=client,
    name="my-dax-subnets",
    subnet_ids=["subnet-0123456789abcdef0", "subnet-0fedcba9876543210"],
    description="Subnets for DAX cluster"
)

# 2. Create Custom Parameter Group with Custom TTL
dax_create_parameter_group(client, name="short-ttl-group")
dax_modify_parameter_group(
    client,
    name="short-ttl-group",
    record_ttl_ms=60000,   # Item cache TTL: 60 seconds
    query_ttl_ms=30000     # Query cache TTL: 30 seconds
)

# 3. Create Cluster
role_arn = "arn:aws:iam::123456789012:role/DAXServiceRole"
cluster = dax_create_cluster(
    client=client,
    cluster_name="mocha-dax-cluster",
    node_type="dax.t3.small",
    replication_factor=1,
    iam_role_arn=role_arn,
    subnet_group_name="my-dax-subnets",
    security_group_ids=["sg-0123456789abcdef0"],
    parameter_group_name="short-ttl-group"
)

# 4. Get Discovery Endpoint once cluster status is 'available'
dax_url, raw = dax_get_cluster_endpoint(client, "mocha-dax-cluster")
print("Discovery URL:", dax_url)  # dax://mocha-dax-cluster.xxxx.dax-clusters.us-east-1.amazonaws.com:8111
```

---

## 5. AWS CLI Reference Cheatsheet

### Create Subnet Group
```bash
aws dax create-subnet-group \
  --subnet-group-name dax-subnets \
  --subnet-ids subnet-01234567 subnet-89abcdef
```

### Create Parameter Group & Customize TTL
```bash
# Create parameter group
aws dax create-parameter-group \
  --parameter-group-name dax-custom-params

# Set record TTL to 10 min (600000 ms) and query TTL to 2 min (120000 ms)
aws dax modify-parameter-group \
  --parameter-group-name dax-custom-params \
  --parameter-name-values "ParameterName=record-ttl-millis,ParameterValue=600000" "ParameterName=query-ttl-millis,ParameterValue=120000"
```

### Launch Cluster
```bash
aws dax create-cluster \
  --cluster-name my-dax-cluster \
  --node-type dax.t3.small \
  --replication-factor 2 \
  --iam-role-arn "arn:aws:iam::<ACCOUNT_ID>:role/DAXServiceRole" \
  --subnet-group-name dax-subnets \
  --security-group-ids sg-xxxxxxxx \
  --parameter-group-name dax-custom-params
```

### Describe & Get Discovery Endpoint
```bash
aws dax describe-clusters \
  --cluster-names my-dax-cluster \
  --query "Clusters[0].ClusterDiscoveryEndpoint"
```

### Scale Nodes
```bash
# Increase replication factor (add read replica)
aws dax increase-replication-factor \
  --cluster-name my-dax-cluster \
  --new-replication-factor 3

# Decrease replication factor
aws dax decrease-replication-factor \
  --cluster-name my-dax-cluster \
  --new-replication-factor 1
```

### Delete Cluster
```bash
aws dax delete-cluster --cluster-name my-dax-cluster
```

---

## 6. Contest / Production Checklist

| Scenario | Recommendation |
| :--- | :--- |
| **High read spikes on specific partition keys** | DAX eliminates hot partitions by caching items in memory. |
| **Need strongly consistent reads** | Remember `ConsistentRead=True` completely bypasses DAX to DynamoDB. Do not use strong consistency unless strictly required. |
| **Lambda connecting to DAX** | Lambda must run inside the **same VPC and subnets** as DAX, and security groups must allow outbound/inbound on port `8111`. |
| **CloudWatch Metrics to watch** | `ItemCacheHits`, `ItemCacheMisses`, `QueryCacheHits`, `QueryCacheMisses`, `CPUUtilization`. |
| **Cost optimization in GameDay** | Use `dax.t3.small` (burstable, low cost) with `replication-factor 1` unless multi-AZ redundancy or read scale-out is tested. |

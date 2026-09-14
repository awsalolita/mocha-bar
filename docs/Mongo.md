# Amazon DocumentDB (with MongoDB Compatibility) Guide

Comprehensive guide for connecting to **Amazon DocumentDB** using SSL/TLS (`global-bundle.pem`), with command-line tools (`mongosh`, `mongoimport`, `mongoexport`) and complete **Python (`pymongo`)** CRUD examples.

---

## 1. Prerequisites & SSL Certificate

Amazon DocumentDB clusters enforce TLS/SSL by default. You need the Amazon RDS/DocumentDB Global Certificate Authority (CA) bundle to establish a secure connection.

### Download CA Certificate Bundle
Run one of the following commands in your project directory:

```bash
# Using wget
wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

# Or using curl
curl -sS "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem" > global-bundle.pem
```

> [!TIP]
> Keep `global-bundle.pem` in your application root or specify its absolute path in your connection configuration.

### Install PyMongo
```bash
pip install pymongo
```

---

## 2. Connecting with PyMongo

### Important Connection Parameters for DocumentDB
* `tls=True` (or `ssl=True`): Enforces encrypted connection.
* `tlsCAFile="global-bundle.pem"` (or `ssl_ca_certs="global-bundle.pem"`): Path to the downloaded CA certificate bundle.
* `replicaSet="rs0"`: DocumentDB cluster replica set name (always `rs0` by default).
* `readPreference="secondaryPreferred"`: Routes read traffic to replica instances to balance read workloads.
* `retryWrites=False`: **Crucial** — Amazon DocumentDB does not support retryable writes. In PyMongo 4+, `retryWrites` defaults to `True`, which will cause operations to fail if not explicitly set to `False`.

---

### Option A: Standard Connection Script

```python
import os
from pymongo import MongoClient

# Configuration
DOCDB_USER = os.getenv("DOCDB_USER", "<your-username>")
DOCDB_PASS = os.getenv("DOCDB_PASS", "<your-password>")
DOCDB_HOST = os.getenv("DOCDB_HOST", "<cluster-endpoint>.docdb.amazonaws.com")
DOCDB_PORT = int(os.getenv("DOCDB_PORT", 27017))
CA_FILE = os.getenv("DOCDB_CA_FILE", "global-bundle.pem")

# 1. Connection using Keyword Arguments
client = MongoClient(
    host=DOCDB_HOST,
    port=DOCDB_PORT,
    username=DOCDB_USER,
    password=DOCDB_PASS,
    tls=True,
    tlsCAFile=CA_FILE,
    replicaSet="rs0",
    readPreference="secondaryPreferred",
    retryWrites=False
)

# Access database and collection
db = client["sample_database"]
collection = db["users"]

# Test connection
print("Databases available:", client.list_database_names())
```

---

### Option B: Connection URI String

```python
from pymongo import MongoClient

connection_uri = (
    "mongodb://<username>:<password>@<cluster-endpoint>:27017/"
    "?tls=true"
    "&tlsCAFile=global-bundle.pem"
    "&replicaSet=rs0"
    "&readPreference=secondaryPreferred"
    "&retryWrites=false"
)

client = MongoClient(connection_uri)
db = client["sample_database"]
```

---

## 3. PyMongo CRUD Operations

Below is a complete reference of CRUD operations using `pymongo`.

### A. Create (Insert)

```python
from pymongo import MongoClient
from bson.objectid import ObjectId

# Initialize client
client = MongoClient(
    host="<cluster-endpoint>:27017",
    username="<your-username>",
    password="<your-password>",
    tls=True,
    tlsCAFile="global-bundle.pem",
    replicaSet="rs0",
    readPreference="secondaryPreferred",
    retryWrites=False
)
db = client["company_db"]
users = db["users"]

# 1. Insert a single document
single_user = {
    "name": "Alice Johnson",
    "role": "admin",
    "age": 30,
    "email": "alice@example.com",
    "skills": ["AWS", "Python", "MongoDB"],
    "status": "active"
}
result_one = users.insert_one(single_user)
print(f"Inserted single ID: {result_one.inserted_id}")

# 2. Insert multiple documents
multiple_users = [
    {
        "name": "Bob Smith",
        "role": "developer",
        "age": 25,
        "email": "bob@example.com",
        "skills": ["JavaScript", "React", "Node.js"],
        "status": "active"
    },
    {
        "name": "Charlie Brown",
        "role": "developer",
        "age": 32,
        "email": "charlie@example.com",
        "skills": ["Python", "FastAPI", "Docker"],
        "status": "inactive"
    },
    {
        "name": "Diana Prince",
        "role": "manager",
        "age": 35,
        "email": "diana@example.com",
        "skills": ["Agile", "Scrum", "Management"],
        "status": "active"
    }
]
result_many = users.insert_many(multiple_users)
print(f"Inserted {len(result_many.inserted_ids)} documents.")
```

---

### B. Read (Query)

```python
import pymongo

# 1. Find a single document
user = users.find_one({"email": "alice@example.com"})
print("Find one:", user)

# 2. Find by ObjectId
user_by_id = users.find_one({"_id": ObjectId("66e3b08e2f3d6c1b4e8a1234")})

# 3. Find with filter conditions (Comparison operators: $gt, $gte, $lt, $lte, $in, $ne)
query = {
    "age": {"$gte": 25, "$lte": 32},
    "role": {"$in": ["developer", "admin"]}
}
for u in users.find(query):
    print(f"Match: {u['name']} - {u['role']} ({u['age']} yo)")

# 4. Projection: Include or exclude specific fields (1 = include, 0 = exclude)
projection = {"name": 1, "email": 1, "_id": 0}
for u in users.find({"status": "active"}, projection):
    print(u)

# 5. Sorting and Limiting (Pagination)
# Sort by age descending (-1 or pymongo.DESCENDING)
results = (
    users.find({"status": "active"})
    .sort("age", pymongo.DESCENDING)
    .skip(0)   # Offset
    .limit(5)  # Limit / Page size
)
for doc in results:
    print(doc["name"], doc["age"])

# 6. Count documents
count = users.count_documents({"status": "active"})
print(f"Active users count: {count}")

# 7. Regex search (case-insensitive)
search_query = {"name": {"$regex": "^ali", "$options": "i"}}
matches = users.find(search_query)
for match in matches:
    print("Regex match:", match["name"])
```

---

### C. Update

```python
from datetime import datetime

# 1. Update single document (using $set, $inc, $currentDate)
filter_criteria = {"email": "bob@example.com"}
update_action = {
    "$set": {"role": "senior developer", "title": "Tech Lead"},
    "$inc": {"age": 1},  # Increment age by 1
    "$currentDate": {"updatedAt": True}
}
update_res = users.update_one(filter_criteria, update_action)
print(f"Matched: {update_res.matched_count}, Modified: {update_res.modified_count}")

# 2. Update multiple documents
multi_filter = {"role": "developer"}
multi_update = {
    "$set": {"department": "Engineering"}
}
res_many = users.update_many(multi_filter, multi_update)
print(f"Bulk updated {res_many.modified_count} users")

# 3. Array operations ($push, $addToSet, $pull)
# $addToSet adds an element only if it does not already exist
users.update_one(
    {"email": "alice@example.com"},
    {"$addToSet": {"skills": "Kubernetes"}}
)

# 4. Upsert (Insert if not found, otherwise update)
upsert_filter = {"email": "eva@example.com"}
upsert_data = {
    "$set": {
        "name": "Eva Green",
        "role": "designer",
        "age": 27,
        "status": "active"
    }
}
upsert_res = users.update_one(upsert_filter, upsert_data, upsert=True)
if upsert_res.upserted_id:
    print(f"Inserted new user via upsert: {upsert_res.upserted_id}")
else:
    print("Updated existing user.")
```

---

### D. Delete

```python
# 1. Delete a single document
delete_one_res = users.delete_one({"email": "charlie@example.com"})
print(f"Deleted single count: {delete_one_res.deleted_count}")

# 2. Delete multiple documents matching a query
delete_many_res = users.delete_many({"status": "inactive"})
print(f"Deleted multiple count: {delete_many_res.deleted_count}")

# 3. Clean all documents in a collection (Use with caution!)
# users.delete_many({})
```

---

### E. Aggregation Pipeline

DocumentDB supports MongoDB aggregation pipelines:

```python
pipeline = [
    # Stage 1: Filter active users
    {"$match": {"status": "active"}},
    # Stage 2: Group by role and compute statistics
    {
        "$group": {
            "_id": "$role",
            "total_users": {"$sum": 1},
            "avg_age": {"$avg": "$age"},
            "min_age": {"$min": "$age"},
            "max_age": {"$max": "$age"}
        }
    },
    # Stage 3: Sort by total_users descending
    {"$sort": {"total_users": -1}}
]

stats = list(users.aggregate(pipeline))
for s in stats:
    print(f"Role: {s['_id']} | Count: {s['total_users']} | Avg Age: {s['avg_age']:.1f}")
```

---

### F. Indexes

Creating indexes is essential for query performance in Amazon DocumentDB:

```python
import pymongo

# 1. Single Field Index
users.create_index([("email", pymongo.ASCENDING)], unique=True)

# 2. Compound Index
users.create_index([
    ("role", pymongo.ASCENDING),
    ("age", pymongo.DESCENDING)
])

# 3. List all indexes
for idx in users.list_indexes():
    print(idx["name"], idx["key"])
```

---

## 4. CLI Tools (`mongosh`, `mongoimport`, `mongoexport`)

### Connect with `mongosh`
```bash
mongosh --host <cluster-endpoint>:27017 \
  --tls \
  --tlsCAFile global-bundle.pem \
  --username <your-username> \
  --password <your-password>
```

### Import JSON Data

#### A. JSON Array Format (e.g. `[ { ... }, { ... } ]`)
When your file contains an array of JSON documents, you **must** pass `--jsonArray`:
```bash
mongoimport --host <cluster-endpoint>:27017 \
  --ssl \
  --sslCAFile global-bundle.pem \
  --username <your-username> \
  --password <your-password> \
  --db <database-name> \
  --collection <collection-name> \
  --file data.json \
  --jsonArray
```

#### B. Line-Delimited JSON / NDJSON (one JSON object per line)
If each line in the file is an independent JSON document, omit `--jsonArray`:
```bash
mongoimport --host <cluster-endpoint>:27017 \
  --ssl \
  --sslCAFile global-bundle.pem \
  --username <your-username> \
  --password <your-password> \
  --db <database-name> \
  --collection <collection-name> \
  --file data.json
```

> [!TIP]
> Add `--drop` to the command if you want to drop the collection before importing fresh documents.

### Import CSV Data
```bash
mongoimport --host <cluster-endpoint>:27017 \
  --ssl \
  --sslCAFile global-bundle.pem \
  --username <your-username> \
  --password <your-password> \
  --db <database-name> \
  --collection <collection-name> \
  --type csv \
  --headerline \
  --file data.csv
```

### Export Data
```bash
mongoexport --host <cluster-endpoint>:27017 \
  --ssl \
  --sslCAFile global-bundle.pem \
  --username <your-username> \
  --password <your-password> \
  --db <database-name> \
  --collection <collection-name> \
  --out exported_data.json
```

---

## 5. `mongosh` Shell CRUD Reference

```javascript
// Switch database
use sample_database

// --- CREATE ---
db.users.insertOne({
  name: "Alice",
  role: "admin",
  age: 30,
  skills: ["AWS", "Python"]
})

db.users.insertMany([
  { name: "Bob", role: "developer", age: 25 },
  { name: "Charlie", role: "developer", age: 28 }
])

// --- READ ---
// Find all
db.users.find().pretty()

// Filter by field
db.users.find({ role: "developer" })

// Comparison ($gt, $lt, $in)
db.users.find({ age: { $gte: 25 } })

// Projection (include only name and role)
db.users.find({}, { name: 1, role: 1, _id: 0 })

// Sort and Limit
db.users.find().sort({ age: -1 }).limit(10)

// --- UPDATE ---
// Update one
db.users.updateOne(
  { name: "Bob" },
  { $set: { role: "lead developer" }, $inc: { age: 1 } }
)

// Update many
db.users.updateMany(
  { role: "developer" },
  { $set: { department: "Engineering" } }
)

// --- DELETE ---
// Delete one
db.users.deleteOne({ name: "Charlie" })

// Delete many
db.users.deleteMany({ role: "inactive" })

// --- INDEXES ---
db.users.createIndex({ email: 1 }, { unique: true })
db.users.getIndexes()
```

---

## 6. DocumentDB Troubleshooting & Key Notes

| Issue / Consideration | Cause | Solution |
| :--- | :--- | :--- |
| **VPC Connectivity** | DocumentDB clusters are isolated inside an Amazon VPC by default. | Connect from an EC2 instance, ECS/EKS task, or Lambda function within the same VPC (or set up a Bastion Host with SSH tunneling). |
| **`retryWrites=true` Error** | `ConfigurationError: retryWrites=true is not supported` | Explicitly pass `retryWrites=False` in PyMongo client options or URI (`&retryWrites=false`). |
| **SSL Verification Failed** | Missing or incorrect CA bundle path. | Ensure `global-bundle.pem` is downloaded from AWS and the file path passed to `tlsCAFile` is valid. |
| **Read Scaling** | Writes go to primary instance, but reads can scale across replicas. | Set `readPreference="secondaryPreferred"` to distribute read load across read replicas. |
| **Authentication Mechanism** | DocumentDB uses SCRAM-SHA-1. | Default PyMongo handles this automatically when authenticating against the `admin` or target database. |

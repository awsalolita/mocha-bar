## Connect to the mongo
```bash
mongosh --host <cluster-endpoint>:27017 \
  --ssl \
  --sslCAFile global-bundle.pem \
  --username <your-username> \
  --password <your-password>

```

## Import json data
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

## Import csv file
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

## CRUD
```bash
db.users.insertOne({ 
  name: "Alice", 
  role: "admin", 
  age: 30 
})

db.users.insertMany([
  { name: "Bob", role: "user", age: 25 },
  { name: "Charlie", role: "user", age: 28 }
])

db.users.find()

db.users.find({ role: "user" })



```

# Creating the Cluster
* be careful of the fucking vpc settings , it can fuck you up so good
# Redshift iam roles 
* policies like access to s3 and kinesis
* make it `DEFAULT`
# Create External database from glue data catalog
* [examples](./SQL/Redshift.sql)
```sql
create external schema spectrum
from data catalog
database '<catalogDB>'
iam_role 'arn:aws:iam::123456789012:role/MySpectrumRole'
create external database if not exists;
```
* create table with dist key
```sql
CREATE TABLE flights (
  year           smallint,
  month          smallint,
  day            smallint,
  carrier        varchar(80) DISTKEY)
```
```sql
SELECT * FROM flights ORDER BY random() LIMIT 10;
select * from spectrum.stock_data;
select * from spectrum.stock_data where <column>='<value>' limit 10;
select * from spectrum_schema.stock_data where <column> like '%pending%' limit 10;
select * from spectrum_schema.stock_data where order_class='stocks' order by price desc limit 5;
```
* show external tables
```sql
SELECT * FROM SVV_EXTERNAL_TABLES;
```
# sql commands
* join command for two tables
```sql
SELECT
  aircraft,
  SUM(departures) AS trips
FROM flights
JOIN aircraft using (aircraft_code)
GROUP BY aircraft
ORDER BY trips DESC
LIMIT 10;
```
* `EXPLAIN` command
* analyze
```sql
ANALYZE COMPRESSION <table>;
```
# Creating materialized views
* Create view
```sql
CREATE MATERIALIZED VIEW myview2
SORTKEY (investor_id)
as
select		investor_id, round(sum(price),2) as total_negotiated
from		stock_lake.stock_data
where		status = 'complete'
and			order_type = 'buy'
group by 	investor_id
```
```sql
CREATE MATERIALIZED VIEW players_purchases_amount
as
select		p.name as Name , g.id as Id, sum(g.purchases) as total
from		games_rs_db.players_schema.games_data g , games_rs_db.players_schema.players_data p
where		p.game_details = Id
group by 	Id , Name
```
* show all views 
```sql
select * from STV_MV_INFO;
```

# Complex query
* select from two tables
```sql
select * from games_rs_db.players_schema.games_data , games_rs_db.players_schema.players_data \
where games_rs_db.players_schema.games_data.id = games_rs_db.players_schema.players_data.game_details 
and id ='12345' limit 5
```
# S3 to Redshift
* the table schema is needed before
* json
```sql
copy  feedback.product_feedback
from 's3://' 
iam_role 'arn:aws:iam::083190880943:role/S3AccessRoleRedshift'
json 'auto'
GZIP
DELIMITER ','
REMOVEQUOTES
REGION 'us-west-2';
```
* csv
```sql
copy sailors from 's3://redshift-demos/data/gamejam/sailors/' 
iam_role 'arn:aws:iam::869076321287:role/Redshiftgamesrole' # OR default
csv
IGNOREHEADER 1;
```
# MYSQL to redshift
```sql
CREATE EXTERNAL SCHEMA lending_schema
FROM MYSQL
DATABASE 'lending'
URI 'INSERT-READER-INSTANCE-ENDPOINT'
IAM_ROLE 'INSERT-IAM-ROLE-ARN'
SECRET_ARN 'INSERT-SECRET-ARN';
```

# Cache
* disable cache
```
SET enable_result_cache_for_session TO OFF;
```

# Grant Role to user
```sql
create user cashking with password 'abcD1234'
create role captain 
grant role captain to cashking
select * from svv_roles
```

# Grant specific permissions and creating row level security (RLS)
```sql
GRANT SELECT ON sailors TO ROLE captain;
GRANT SELECT(s_name,s_segment,s_dietrestrictions) ON sailors TO ROLE crew;
GRANT SELECT(s_name,s_address,s_acctbal) ON sailors TO ROLE finance;

CREATE RLS POLICY board
with (s_onboard BOOLEAN)
using (s_onboard = TRUE)

CREATE RLS POLICY allpolicy
using (TRUE)

SELECT * FROM svv_rls_policy;
```



# Space management
* disk capacity
```sql
SELECT
  owner AS node,
  diskno,
  used,
  capacity,
  used/capacity::numeric * 100 as percent_used
FROM stv_partitions
WHERE host = node
ORDER BY 1, 2;
```
* space taken by table
```sql
SELECT
  name,
  count(*)
FROM stv_blocklist
JOIN (SELECT DISTINCT name, id as tbl from stv_tbl_perm) USING (tbl)
GROUP BY name;
```
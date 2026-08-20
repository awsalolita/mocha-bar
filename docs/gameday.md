# AWS GameDay / Contest Best-Practices Checklist

Use this as a pass/fail audit during the contest. For every resource you create or find: **encrypt (prefer CMK) → protect from deletion → enable backup/recovery → enable logging/monitoring → least privilege → private networking**.

Legend:
- `[ ]` = check / fix
- **CMK** = customer-managed KMS key (prefer over AWS-managed / default where scoring rewards it)
- **Deletion protection** = prevent accidental destroy
- **PITR** = point-in-time recovery

---

## 0. Contest order of operations (do first)

- [ ] Enable **AWS CloudTrail** (multi-Region trail, log file validation, SSE-KMS/CMK, deliver to S3 + optional CloudWatch Logs)
- [ ] Enable **AWS Config** (recorder + delivery channel; record all resources / global resources)
- [ ] Enable **Amazon GuardDuty** (all detectors; EKS/ECS/RDS/S3/Lambda/Malware protection where available)
- [ ] Enable **AWS Security Hub** (CIS / Foundational Security Best Practices / AWS Resource Configuration standards)
- [ ] Enable **Amazon Inspector** (EC2, ECR, Lambda scanning)
- [ ] Enable **AWS IAM Access Analyzer**
- [ ] Enable **Amazon Macie** (if S3 data sensitivity is in scope)
- [ ] Enable **AWS Trusted Advisor** / Well-Architected checks if available in account
- [ ] Turn on **EBS encryption by default** (account attribute, per Region)
- [ ] Set **S3 Block Public Access** account-level ON
- [ ] Set **AMI Block Public Access** account-level ON (where available)
- [ ] Create / verify **CMKs** with rotation enabled; key policies least privilege
- [ ] Enable **AWS Backup** (org/account backup plan + vault lock if scoring requires immutability)
- [ ] Enable **VPC Flow Logs** for every VPC (to CloudWatch Logs or S3, encrypted)
- [ ] Enable **AWS WAF** on ALB / CloudFront / API Gateway as applicable
- [ ] Enable **AWS Shield** (Standard always on; Advanced if contest allows)
- [ ] Confirm **MFA** for root; no root access keys; root unused for daily ops
- [ ] Confirm **CloudWatch Alarms** on billing / anomalies if required

---



## 1. Identity & access



### IAM

- [ ] No long-lived access keys on users when SSO/roles are available
- [ ] MFA on human users / console users
- [ ] Password policy strong (length, reuse, expiration if required)
- [ ] Least privilege policies; prefer managed policies + conditions (`aws:SourceVpce`, `aws:SourceIp`, `aws:SecureTransport`)
- [ ] No `*` on sensitive actions (`iam:*`, `kms:Decrypt`, `s3:*`, `sts:AssumeRole`) without conditions
- [ ] Service-linked roles only where needed
- [ ] Permission boundaries for builders / contest automation roles
- [ ] Access Analyzer findings reviewed / remediated
- [ ] IAM credential report reviewed (unused users/keys)



### AWS Organizations / Account

- [ ] SCPs deny dangerous actions if org is in scope (disable leaving org, deny unencrypted writes, deny public S3, etc.)
- [ ] Separate accounts (prod/sec/log) if architecture allows
- [ ] CloudTrail / Config / GuardDuty delegated admin if multi-account



### AWS SSO / IAM Identity Center

- [ ] Permission sets least privilege
- [ ] MFA enforced
- [ ] Session duration limited



### Cognito (if used)

- [ ] MFA / advanced security mode
- [ ] Strong password policy
- [ ] App client secrets not in code
- [ ] Encrypted user pool attributes as required

---



## 2. Encryption & keys



### KMS

- [ ] Prefer **customer-managed keys (CMK)** for data stores scoring encryption
- [ ] Automatic key rotation enabled on CMKs
- [ ] Key policy least privilege; separate admin vs usage principals
- [ ] Multi-Region keys only if cross-Region DR is required
- [ ] CloudTrail logs KMS API calls
- [ ] Alias naming consistent; unused keys scheduled for deletion carefully (contest may penalize pending deletion)



### Secrets Manager

- [ ] Secrets encrypted with CMK
- [ ] Rotation enabled for DB / API credentials
- [ ] No plaintext secrets in env vars, userdata, or repos
- [ ] Resource policies restrict principals / VPC endpoints
- [ ] Recovery window set (not immediate delete) when deleting secrets



### Systems Manager Parameter Store

- [ ] Sensitive params as `SecureString` with CMK
- [ ] Hierarchy + IAM path restrictions
- [ ] Prefer Secrets Manager for rotating credentials



### Certificate Manager (ACM)

- [ ] TLS certs on ALB / CloudFront / API Gateway
- [ ] DNS validation preferred
- [ ] No expired / unused certs
- [ ] HTTPS listeners only (redirect HTTP → HTTPS)

---



## 3. Logging, detection & compliance



### CloudTrail

- [ ] Multi-Region trail
- [ ] Management events + data events for S3 / Lambda if required
- [ ] Log file validation enabled
- [ ] SSE-KMS (CMK) on trail bucket
- [ ] Bucket: Block Public Access, versioning, Object Lock if required
- [ ] CloudWatch Logs integration + metric filters / alarms (root login, unauthorized API, IAM changes)
- [ ] Insights enabled if useful for contest scoring



### AWS Config

- [ ] Configuration recorder ON in all used Regions
- [ ] Global resource types recorded
- [ ] Managed rules: encryption, public access, MFA, restricted SSH/RDP, etc.
- [ ] Conformance packs (CIS / Operational Best Practices) if available
- [ ] SNS / EventBridge remediation hooks if scoring expects auto-fix



### Security Hub

- [ ] Standards enabled (FSBP, CIS, PCI if relevant)
- [ ] Findings triaged; Critical/High remediated
- [ ] Aggregator Region configured for multi-Region



### GuardDuty

- [ ] Enabled all Regions
- [ ] Malware Protection for EBS / S3 as available
- [ ] Runtime Monitoring for EKS/ECS/EC2 if in scope
- [ ] Findings exported / alarmed via EventBridge → SNS



### Inspector

- [ ] EC2 scanning enabled
- [ ] ECR continuous scanning enabled
- [ ] Lambda scanning enabled
- [ ] Critical CVEs remediated / images rebuilt



### Macie

- [ ] Sensitive data discovery jobs on key buckets
- [ ] Findings reviewed



### CloudWatch

- [ ] Log groups retention set (never “Never expire” unless required; contest often wants retention)
- [ ] Log groups encrypted with CMK (where supported)
- [ ] Metric alarms on CPU, errors, 5xx, free storage, throttle, DLQ depth
- [ ] Dashboards for critical services
- [ ] Composite alarms for noisy metrics if needed



### X-Ray / Application Signals

- [ ] Tracing on APIs, Lambda, ECS/EKS apps if observability scored



### AWS Backup Audit Manager / AWS Audit Manager

- [ ] Enable if compliance evidence is scored

---



## 4. Networking



### VPC

- [ ] No unnecessary public subnets / open routes
- [ ] Separate public / private / data subnets
- [ ] NAT Gateway(s) or endpoints for private egress (prefer VPC endpoints for AWS APIs)
- [ ] **VPC Flow Logs** enabled (ACCEPT+REJECT or ALL)
- [ ] Network ACLs default-deny only if intentional; don’t break traffic blindly
- [ ] DNS hostnames + resolution enabled as needed
- [ ] DHCP options correct



### Subnets / Routing

- [ ] Databases / caches in **private** subnets only
- [ ] No `0.0.0.0/0` route on private route tables except via NAT
- [ ] Transit Gateway / peering least routes if used



### Security Groups

- [ ] Least privilege ports/CIDRs
- [ ] No `0.0.0.0/0` on SSH (22) / RDP (3389) / DB ports
- [ ] Prefer SG → SG references over CIDR where possible
- [ ] Unused SGs cleaned up
- [ ] Description on every rule



### Network Firewall / WAF / Shield

- [ ] AWS WAF WebACL on ALB / CloudFront / API GW (AWS Managed Rules + rate limit)
- [ ] AWS Network Firewall if east-west / egress filtering required
- [ ] Shield Advanced + Route53 health checks if DDoS scoring exists



### VPC Endpoints

- [ ] Interface/Gateway endpoints for S3, DynamoDB, ECR, Secrets Manager, Logs, STS, KMS, SSM
- [ ] Endpoint policies least privilege
- [ ] Private DNS enabled on interface endpoints



### Route 53

- [ ] DNSSEC if required
- [ ] Query logging enabled
- [ ] Health checks + failover for HA
- [ ] Alias records to AWS targets (ALB/CloudFront)
- [ ] Domain registrar lock / transfer lock if applicable



### CloudFront

- [ ] HTTPS only / redirect HTTP→HTTPS
- [ ] TLS 1.2+ minimum
- [ ] Origin Access Control (OAC) for S3 (not public buckets)
- [ ] WAF associated
- [ ] Access logging to S3 (encrypted)
- [ ] Geo / field-level encryption if needed
- [ ] Cache policies least privilege (don’t forward secrets)
- [ ] Origin custom headers / signed URLs for private content



### API Gateway

- [ ] AuthN/Z (IAM, Cognito, Lambda authorizer) — no open APIs
- [ ] TLS / custom domain with ACM
- [ ] Access logging + execution logging (ERROR/INFO as needed)
- [ ] X-Ray tracing
- [ ] Throttling / usage plans / WAF
- [ ] Private API + VPC endpoint if internal-only
- [ ] Encryption at rest for cache stage if caching used

---



## 5. Load balancing & edge



### Application Load Balancer (ALB)

- [ ] **Deletion protection** enabled
- [ ] **Access logs** enabled → S3 (bucket policy + encryption / CMK)
- [ ] **Connection logs** enabled if available / required
- [ ] HTTP→HTTPS redirect listener
- [ ] TLS policy modern (ELBSecurityPolicy-TLS13-* or latest recommended)
- [ ] ACM certificate (not expired)
- [ ] WAF associated
- [ ] Drop invalid headers attribute ON
- [ ] Desync mitigation mode (defensive / strict)
- [ ] Idle timeout appropriate
- [ ] Stickiness only if required
- [ ] Security groups: only 80/443 from needed CIDRs (or CloudFront prefix list)
- [ ] Target groups: health checks correct; deregistration delay set
- [ ] Cross-zone load balancing as required
- [ ] HTTP/2 / gRPC only if intentional



### Network Load Balancer (NLB)

- [ ] Deletion protection enabled
- [ ] Access / connection logs if supported for contest version
- [ ] TLS listeners with ACM where terminating TLS
- [ ] Cross-zone as required
- [ ] Security groups on NLB (newer feature) restricted
- [ ] Proxy protocol / client IP preservation intentional



### Gateway Load Balancer

- [ ] Deletion protection
- [ ] Appliance health checks
- [ ] Flow stickiness as required



### Elastic IP / Global Accelerator

- [ ] Unused EIPs released (cost + hygiene)
- [ ] Global Accelerator flow logs if used

---



## 6. Compute



### EC2

- [ ] EBS volumes **encrypted** (CMK preferred); encryption by default ON
- [ ] IMDSv2 **required** (`HttpTokens=required`); hop limit 1–2 as appropriate
- [ ] No public IP unless required; prefer private + SSM
- [ ] SSM Session Manager instead of SSH bastion when possible
- [ ] Instance roles (no embedded keys)
- [ ] Detailed monitoring if scored
- [ ] Termination protection on critical instances
- [ ] Hibernation / stop protection only if needed
- [ ] Security groups least privilege
- [ ] Patch via Patch Manager / Inspector findings remediations
- [ ] User data has no secrets
- [ ] Nitro / modern instance types where required
- [ ] Dedicated tenancy / placements only if mandated



### Auto Scaling Group (ASG)

- [ ] Health checks (ELB) configured
- [ ] Multiple AZs
- [ ] Scaling policies / target tracking
- [ ] Launch template (not legacy launch config) with encrypted EBS + IMDSv2
- [ ] Instance refresh / warm pools if needed
- [ ] Notifications on launch/terminate failures



### Lambda

- [ ] Least privilege execution role
- [ ] Environment variables encrypted with CMK (sensitive)
- [ ] In VPC only if needing private resources; then use endpoints
- [ ] Dead-letter queue (SQS/SNS) or failure destination
- [ ] Reserved / provisioned concurrency only as needed
- [ ] Tracing (X-Ray) on
- [ ] CloudWatch Logs retention + CMK encryption
- [ ] Function URL auth type AWS_IAM (not NONE) if used
- [ ] Code signing if required
- [ ] No wildcard resource permissions



### Elastic Beanstalk (if used)

- [ ] Managed platform updates
- [ ] Enhanced health reporting
- [ ] HTTPS listener
- [ ] Immutable / rolling deployments
- [ ] Logs streamed to CloudWatch

---



## 7. Containers



### ECR

- [ ] Image scanning on push (or Inspector continuous)
- [ ] Encryption with CMK
- [ ] Repo policies least privilege; no public repos unless required
- [ ] Tag immutability ON
- [ ] Lifecycle policies (expire untagged / old images)
- [ ] Prefer private endpoints for pulls



### ECS

- [ ] Task definitions: no privileged unless required
- [ ] Readonly root filesystem where possible
- [ ] Secrets from Secrets Manager / SSM (not plaintext env)
- [ ] Task role + execution role separated / least privilege
- [ ] awsvpc networking; private subnets
- [ ] CloudWatch Logs / FireLens configured; retention set
- [ ] ECS Exec only when needed + logging
- [ ] Capacity providers / multi-AZ
- [ ] Service circuit breaker + rollback
- [ ] Container Insights / Container Insights with enhanced observability
- [ ] Fargate platform latest; ephemeral storage encrypted (default)



### EKS

- [ ] Private API endpoint (public disabled or restricted CIDRs)
- [ ] Secrets encryption with CMK (envelope encryption)
- [ ] Cluster logging: api, audit, authenticator, controllerManager, scheduler → CloudWatch
- [ ] Control plane / node CMK encryption where applicable
- [ ] IRSA (IAM Roles for Service Accounts) — no node instance role over-permission
- [ ] Pod Security Standards / Kyverno / PSPs successor enforced
- [ ] NetworkPolicies (Calico/Cilium) default-deny where possible
- [ ] Nodes in private subnets; IMDSv2; encrypted EBS
- [ ] aws-auth / EKS access entries least privilege
- [ ] Addon versions current (vpc-cni, kube-proxy, coredns, ebs-csi, etc.)
- [ ] GuardDuty EKS Protection / Runtime Monitoring
- [ ] Image provenance: pull only from approved ECR
- [ ] Backup cluster state / etcd via appropriate tools if required
- [ ] Deletion protection / retain on managed node groups as contest requires



### App Runner / Lightsail (if appear)

- [ ] HTTPS only
- [ ] Private connectivity / VPC connector when talking to data plane
- [ ] Health checks + auto deploy controlled

---



## 8. Storage



### S3

- [ ] Block Public Access (account + bucket) ON
- [ ] Default encryption **SSE-KMS with CMK** (prefer over SSE-S3 when scoring CMK)
- [ ] Bucket key enabled (cost/perf for KMS)
- [ ] Versioning enabled
- [ ] MFA Delete if required (and practical)
- [ ] Object Lock / Legal Hold if immutability scored
- [ ] Access logging or **Server Access Logging** / **CloudTrail data events** / **S3 Storage Lens**
- [ ] Lifecycle rules (transition + expire noncurrent)
- [ ] Replication (CRR/SRR) encrypted with CMK if DR required
- [ ] Bucket policy: deny `aws:SecureTransport=false`; deny public; least privilege principals
- [ ] No ACLs (Bucket owner enforced)
- [ ] Event notifications secured
- [ ] Intelligent-Tiering / storage class appropriate
- [ ] Access Points / Multi-Region Access Points policies reviewed
- [ ] Inventory / Storage Lens for visibility



### EBS

- [ ] Volumes encrypted (CMK)
- [ ] Snapshots encrypted
- [ ] DeleteOnTermination set intentionally
- [ ] Unused volumes / snapshots cleaned or retained per backup policy
- [ ] Fast Snapshot Restore only if needed
- [ ] Recycle Bin for EBS snapshots / AMIs enabled if available



### EFS

- [ ] Encryption at rest (CMK)
- [ ] Encryption in transit (`tls` mount option / stunnel)
- [ ] Backup policy enabled (AWS Backup)
- [ ] Lifecycle management (IA transition)
- [ ] Mount targets in private subnets; SG least privilege (NFS 2049 from clients only)
- [ ] Access points with POSIX user enforcement
- [ ] Replication if DR required



### FSx (Windows / Lustre / NetApp / OpenZFS)

- [ ] Encryption at rest (CMK)
- [ ] Encryption in transit where supported
- [ ] Automatic backups + retention
- [ ] Copy tags to backups
- [ ] Private subnets / SG restricted
- [ ] Deletion protection / final backup on delete if available



### Storage Gateway / Backup Gateway

- [ ] Encrypted cache / upload buffers
- [ ] Upload to encrypted S3
- [ ] Monitoring alarms

---



## 9. Databases



### Common DB checklist (apply to all engines)

- [ ] Encryption at rest (**CMK**)
- [ ] Encryption in transit (TLS required / `rds.force_ssl` / parameter groups)
- [ ] Private subnets; **not publicly accessible**
- [ ] SG: only app SG on DB port
- [ ] Deletion protection ON
- [ ] Automated backups ON + retention ≥ contest minimum (often 7+)
- [ ] Prefer **AWS Backup** integration + vault
- [ ] Copy tags to snapshots
- [ ] Enhanced monitoring / Performance Insights ON
- [ ] CloudWatch Logs exports (engine logs) ON
- [ ] Minor version auto-upgrade intentional
- [ ] Multi-AZ / Multi-AZ cluster for HA
- [ ] Credentials in Secrets Manager with rotation
- [ ] Parameter / option groups hardened
- [ ] IAM DB auth if supported & useful



### RDS (MySQL / Postgres / MariaDB / SQL Server / Oracle)

- [ ] Storage encrypted with CMK
- [ ] Deletion protection enabled
- [ ] Automated backups + PITR window
- [ ] Final snapshot on delete if deletion protection off temporarily
- [ ] Multi-AZ
- [ ] PubliclyAccessible = false
- [ ] Proxy (RDS Proxy) if connection storms / failover scoring
- [ ] Event subscriptions to SNS



### Aurora (MySQL / PostgreSQL)

- [ ] Storage encryption CMK
- [ ] Backtrack (MySQL) if useful
- [ ] Continuous backup / PITR
- [ ] Clone / global database only if DR needs
- [ ] Serverless v2 capacity bounds set
- [ ] Deletion protection
- [ ] Activity streams if advanced DB auditing scored



### DynamoDB

- [ ] Encryption at rest with **CMK** (owned by customer)
- [ ] **Point-in-time recovery (PITR)** enabled
- [ ] Deletion protection enabled
- [ ] On-demand vs provisioned intentional; autoscaling if provisioned
- [ ] TTL only if data lifecycle requires
- [ ] DynamoDB Streams + encrypted destinations if used
- [ ] Global Tables encrypted in all Regions
- [ ] Contributor Insights / CloudWatch alarms on throttle & system errors
- [ ] VPC endpoint (Gateway) + endpoint policy
- [ ] Resource-based policies least privilege
- [ ] Backup via AWS Backup / on-demand backups as required
- [ ] DAX cluster encrypted if used



### ElastiCache (Redis / Memcached) / MemoryDB

- [ ] Encryption at rest (CMK where supported)
- [ ] Encryption in transit (TLS)
- [ ] AUTH / RBAC / Secrets Manager for Redis
- [ ] Automated backups (Redis/MemoryDB) + retention
- [ ] Multi-AZ / Auto-failover
- [ ] Private subnets; no public access
- [ ] SG restricted
- [ ] Deletion / final snapshot intentional



### Redshift

- [ ] Encryption CMK
- [ ] Publicly accessible = false
- [ ] Automated snapshots + retention
- [ ] Audit logging to S3 (encrypted)
- [ ] Enhanced VPC routing
- [ ] SSL required
- [ ] Concurrency scaling / RA3 intentional
- [ ] Snapshot copy encrypted
- [ ] Deletion / terminate protections via IaC care



### DocumentDB / Neptune / Timestream / Keyspaces / QLDB

- [ ] Encryption at rest CMK
- [ ] TLS in transit
- [ ] Audit / slow logs to CloudWatch
- [ ] Automated backups / PITR where available
- [ ] Deletion protection
- [ ] Private networking only

---



## 10. Analytics & streaming



### Kinesis Data Streams / Firehose / Data Analytics

- [ ] Server-side encryption (KMS/CMK)
- [ ] Enhanced fan-out intentional
- [ ] CloudWatch monitoring + alarms
- [ ] Firehose destinations encrypted (S3 CMK)
- [ ] Transformation Lambda least privilege
- [ ] Source/dest VPC for Firehose when private



### MSK (Kafka) / MSK Serverless / MQ

- [ ] Encryption at rest CMK
- [ ] Encryption in transit TLS
- [ ] SASL/IAM auth preferred over plaintext
- [ ] Private subnets
- [ ] Broker logs to CloudWatch/S3
- [ ] Auto-scaling / storage monitoring
- [ ] MQ: audit logging, encryption, private access



### EMR / Athena / Glue / Lake Formation

- [ ] S3 data lake buckets encrypted CMK + Block Public Access
- [ ] Glue catalog encryption + connection passwords encrypted
- [ ] EMR security config (at-rest + in-transit)
- [ ] Athena workgroup encryption + query result location secured
- [ ] Lake Formation: LF-TBAC / grants least privilege; no broad IAM S3
- [ ] Job bookmarks / logging enabled



### OpenSearch Service

- [ ] Encryption at rest CMK
- [ ] Node-to-node encryption
- [ ] HTTPS enforced
- [ ] Fine-grained access control
- [ ] Cognito / SAML / IAM master user secured
- [ ] Audit logs / index / search / error logs to CloudWatch
- [ ] VPC only (no public)
- [ ] Automated snapshots
- [ ] UltraWarm / cold storage intentional

---



## 11. Messaging & integration



### SQS

- [ ] SSE with CMK (SSE-KMS)
- [ ] Dead-letter queue configured + redrive policy
- [ ] Access policy least privilege; deny non-TLS
- [ ] Long polling enabled
- [ ] Visibility timeout matches consumer
- [ ] FIFO only if ordering/dedup required



### SNS

- [ ] SSE with CMK
- [ ] Topic policy least privilege; deny non-TLS
- [ ] Subscription confirmation / filter policies
- [ ] Delivery status logging to CloudWatch/Firehose/S3
- [ ] HTTPS endpoints only for HTTP(S) subscriptions



### EventBridge

- [ ] Event buses resource policies least privilege
- [ ] Archive + replay if durability scored
- [ ] DLQ on targets
- [ ] Encrypted connections to targets
- [ ] Schema registry if used



### Step Functions

- [ ] Logging level ALL/ERROR to CloudWatch (CMK)
- [ ] X-Ray tracing
- [ ] Least privilege role
- [ ] Sensitive data not in plaintext state I/O (use redact / Secrets)



### AppSync

- [ ] Auth modes secured
- [ ] Logging + X-Ray
- [ ] Caching encrypted
- [ ] WAF association

---



## 12. CI/CD & source



### CodeCommit / CodeBuild / CodePipeline / CodeDeploy

- [ ] Encryption CMK on artifacts bucket
- [ ] Artifact S3: Block Public Access, versioning, logging
- [ ] Build logs to CloudWatch; no secrets in plaintext logs
- [ ] IAM roles least privilege per stage
- [ ] Manual approval on production if required
- [ ] CodeBuild privileged mode OFF unless Docker-in-Docker required
- [ ] VPC config for private resource access



### CodeArtifact / ECR (again)

- [ ] External connections reviewed
- [ ] Domain encryption

---



## 13. Backup & DR (cross-service)



### AWS Backup

- [ ] Backup plan covering: EBS, EFS, FSx, RDS/Aurora, DynamoDB, EC2, S3, Storage Gateway, DocumentDB, Neptune, Fargate volumes as supported
- [ ] Backup vault encrypted with CMK
- [ ] **Vault Lock** (WORM) if ransomware / immutability scored
- [ ] Cross-account / cross-Region copy for DR
- [ ] Lifecycle to cold storage
- [ ] Restore testing jobs scheduled
- [ ] SNS notifications on backup job failures
- [ ] Access policies deny delete backup unless break-glass role



### Snapshots hygiene

- [ ] Automated; tagged; encrypted
- [ ] Shared snapshots not public
- [ ] Recycle Bin rules for EBS / AMIs / EC2

---



## 14. Edge security & DNS mail (if in scope)



### WAF

- [ ] AWS Managed Rule groups (Core, Known Bad Inputs, SQLi, Linux/Windows)
- [ ] Rate-based rules
- [ ] Logging to S3 / Firehose / CloudWatch (encrypted)
- [ ] Associated to all public ALB/CloudFront/API GW



### Shield

- [ ] Shield Advanced subscriptions + health-based detection if allowed
- [ ] DRT access / proactive engagement if applicable
- [ ] Route 53 + CloudFront + ALB covered



### SES / Pinpoint

- [ ] DKIM / SPF / DMARC
- [ ] Configuration set logging
- [ ] Dedicated IPs only if needed
- [ ] Account-level suppression list
- [ ] No open relays; verified identities only

---



## 15. Machine learning (if appear)



### SageMaker

- [ ] Volume / data encryption CMK
- [ ] Network isolation / VPC only
- [ ] No direct internet from training if avoidable
- [ ] IAM least privilege execution roles
- [ ] Studio / notebook root access disabled
- [ ] Model artifacts in encrypted S3
- [ ] CloudWatch / audit logging



### Bedrock / Comprehend / Rekognition / Translate

- [ ] Data encryption / opt-out of service improvement if required
- [ ] Private VPC endpoints / PrivateLink
- [ ] IAM least privilege + SCPs
- [ ] Logging via CloudTrail

---



## 16. Hybrid & management



### Systems Manager

- [ ] Fleet Manager / Session Manager preferred over SSH
- [ ] Session logging to S3/CloudWatch (encrypted) + CMK
- [ ] Patch Manager baselines associated
- [ ] State Manager / Inventory enabled
- [ ] Default Host Management Configuration / instance profile with `AmazonSSMManagedInstanceCore`



### Systems Manager Incident Manager / OpsCenter / Chatbot

- [ ] Engaging path for P1 findings if scored



### AWS Resource Explorer / Tag Editor

- [ ] Mandatory tags: `Environment`, `Owner`, `CostCenter`, `DataClass`
- [ ] Untaggable / untagged resources fixed (many contests score tagging)



### Cost / Billing hygiene (often scored)

- [ ] Budgets + anomaly detection
- [ ] Unused EIPs, old snapshots, unattached EBS, idle LBs removed or justified
- [ ] S3 incomplete multipart uploads aborted via lifecycle

---



## 17. Per-service “quick card” (print this)


| Service                | Encrypt (CMK)            | Deletion protection                | Backup / PITR                         | Logging                              | Network                             |
| ---------------------- | ------------------------ | ---------------------------------- | ------------------------------------- | ------------------------------------ | ----------------------------------- |
| S3                     | SSE-KMS CMK + Bucket Key | N/A (use Object Lock / versioning) | Versioning + AWS Backup / replication | Access logs / CloudTrail data events | Private / OAC / Block Public Access |
| EBS                    | CMK                      | Termination protection on instance | Snapshots / AWS Backup / Recycle Bin  | CloudTrail                           | Private subnet instance             |
| EFS                    | CMK + TLS mount          | —                                  | AWS Backup policy                     | CloudWatch / backup jobs             | Private mount targets               |
| RDS / Aurora           | CMK + TLS                | ON                                 | Automated backups + PITR              | Logs export + PI                     | Private, not public                 |
| DynamoDB               | CMK                      | ON                                 | PITR + AWS Backup                     | CloudWatch + Contributor Insights    | Gateway endpoint                    |
| ElastiCache / MemoryDB | Rest + transit           | Snapshot on delete                 | Automated backups                     | CloudWatch                           | Private                             |
| ALB                    | TLS (ACM)                | ON                                 | N/A                                   | Access + connection logs             | SG + WAF                            |
| NLB                    | TLS if terminating       | ON                                 | N/A                                   | Logs if available                    | SG restricted                       |
| CloudFront             | TLS1.2+                  | —                                  | N/A                                   | Access logs                          | OAC + WAF                           |
| API Gateway            | TLS + cache encrypt      | —                                  | N/A                                   | Access + execution logs              | Private API / WAF                   |
| Lambda                 | Env CMK + logs CMK       | —                                  | N/A (use DLQ)                         | CW Logs + X-Ray                      | VPC + endpoints if needed           |
| ECS/Fargate            | Secrets + logs           | —                                  | N/A                                   | CW / FireLens / Insights             | Private awsvpc                      |
| EKS                    | Secrets CMK + node EBS   | Careful destroy                    | etcd/app backups                      | Control plane logs                   | Private API + IRSA                  |
| SQS/SNS                | SSE-KMS CMK              | —                                  | DLQ / delivery retries                | Delivery status                      | Deny non-TLS                        |
| OpenSearch             | CMK + node-to-node       | —                                  | Snapshots                             | Audit + app logs                     | VPC only                            |
| MSK                    | CMK + TLS                | —                                  | —                                     | Broker logs                          | Private                             |
| Redshift               | CMK + SSL                | Careful                            | Automated snapshots                   | Audit to S3                          | Enhanced VPC routing                |
| CloudTrail             | CMK on bucket            | Object Lock bucket                 | Bucket versioning                     | Trail + CW metrics                   | Org trail                           |
| KMS                    | Rotation ON              | Pending deletion caution           | —                                     | CloudTrail                           | Key policies                        |
| Backup vault           | CMK                      | Vault Lock                         | Cross-Region copy                     | Job notifications                    | Vault policy                        |


---



## 18. Contest remediation script mindset

When a finding appears (Security Hub / Config / Trusted Advisor / Inspector):

1. **Identify resource** (ARN / Region)
2. **Apply the matching row** in this checklist (encrypt → protect → backup → log → lock network)
3. **Re-run** Security Hub / Config evaluation
4. **Evidence**: screenshot or CLI output showing the setting ON (for scoring judges)



### Handy verification commands (examples)

```bash
# DynamoDB: PITR + deletion protection + SSE
aws dynamodb describe-continuous-backups --table-name TABLE
aws dynamodb describe-table --table-name TABLE --query "Table.{DeletionProtection:DeletionProtectionEnabled,SSE:SSEDescription}"

# RDS deletion protection + storage encrypted
aws rds describe-db-instances --query "DBInstances[].{Id:DBInstanceIdentifier,DelProt:DeletionProtection,Enc:StorageEncrypted,Public:PubliclyAccessible}"

# ALB deletion protection + access logs
aws elbv2 describe-load-balancer-attributes --load-balancer-arn ARN

# S3 public access + encryption
aws s3api get-public-access-block --bucket BUCKET
aws s3api get-bucket-encryption --bucket BUCKET

# EBS encryption by default
aws ec2 get-ebs-encryption-by-default
aws ec2 get-ebs-default-kms-key-id

# CloudTrail
aws cloudtrail describe-trails
aws cloudtrail get-trail-status --name TRAIL

# GuardDuty / Security Hub / Config (per Region)
aws guardduty list-detectors
aws securityhub describe-hub
aws configservice describe-configuration-recorders
```

---



## 19. Final sweep (before submit / freeze)

- [ ] All Regions you touched have CloudTrail/Config/GuardDuty coverage (or org-delegated)
- [ ] No public S3, public RDS/Redshift/OpenSearch, open SG on 22/3389/DB ports
- [ ] Every stateful store: CMK + backup/PITR + deletion protection where supported
- [ ] Every public entry point: TLS + WAF + access logs
- [ ] Every compute role: least privilege; no secrets in code
- [ ] Log retention + CMK on sensitive log groups
- [ ] Backup vault jobs green in last 24h
- [ ] Security Hub Critical/High = 0 (or waived with justification)
- [ ] Tags complete on all billable resources
- [ ] Root account locked down; no root keys

---

*Aligned with AWS Well-Architected (Security, Reliability) common GameDay / security contest scoring themes. Prefer CMK + explicit enablement of protection features even when AWS defaults partially cover them — contests often check the explicit setting.*
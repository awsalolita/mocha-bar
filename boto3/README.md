# boto3 Reference — WorldSkills Cloud Computing (AWS)

Fast, accurate, copy-paste **unit functions** for the most important AWS services.
Each function does **one** API interaction so you can grab exactly what you need under time pressure.

## Conventions

- Every service file exposes two helpers:
  - `get_client(region=None)` → low-level `boto3.client("<svc>")`
  - `get_resource(region=None)` → high-level `boto3.resource("<svc>")` **(only for services that have a resource API)**
- Functions are grouped:
  - `# ---------- CLIENT ----------` uses the low-level client (all services support this).
  - `# ---------- RESOURCE ----------` uses the high-level resource API.
- Functions return the raw boto3 response (or the resource object) so you can inspect/print it.
- Names are prefixed so client vs resource is obvious, e.g. `s3c_upload_file` (client) vs `s3r_upload_file` (resource).

## Which services have a `resource` API?

boto3 only ships a resource (high-level) API for a limited set of services:

| Service | client | resource |
|---|---|---|
| S3 | ✅ | ✅ |
| EC2 | ✅ | ✅ |
| IAM | ✅ | ✅ |
| DynamoDB | ✅ | ✅ |
| SQS | ✅ | ✅ |
| SNS | ✅ | ✅ |
| CloudWatch | ✅ | ✅ |
| CloudFormation | ✅ | ✅ |
| Glacier / OpsWorks | ✅ | ✅ |
| Lambda, STS, SSM, Secrets Manager, KMS, RDS, ELBv2, Auto Scaling, Route 53, ECR, ECS, CloudWatch **Logs** | ✅ | ❌ (client only) |

> Rule of thumb for the contest: **S3, EC2, IAM, DynamoDB, SQS, SNS** have both.
> Everything else you drive through the **client**.

## Auth / region

All helpers rely on the standard boto3 credential chain (env vars, `~/.aws/credentials`,
instance/role profile). Pass `region` explicitly when the default profile region isn't set:

```python
from s3 import get_client, get_resource
c = get_client("eu-west-1")
r = get_resource("eu-west-1")
```

## Files

| File | Service |
|---|---|
| `s3.py` | S3 (buckets, objects, presigned URLs, policies) |
| `ec2.py` | EC2 + VPC + Security Groups + EBS + Key Pairs |
| `iam.py` | IAM users, roles, policies, instance profiles |
| `dynamodb.py` | DynamoDB tables + items + query/scan |
| `sqs.py` | SQS queues + messages |
| `sns.py` | SNS topics + subscriptions + publish |
| `lambda_function.py` | Lambda functions + invoke |
| `cloudwatch.py` | CloudWatch metrics/alarms + Logs |
| `ssm.py` | SSM Parameter Store + Run Command |
| `secretsmanager.py` | Secrets Manager |
| `kms.py` | KMS keys + encrypt/decrypt |
| `sts.py` | STS assume-role + identity |
| `rds.py` | RDS instances + snapshots |
| `autoscaling.py` | Auto Scaling groups + launch templates |
| `elbv2.py` | ALB/NLB, target groups, listeners |
| `route53.py` | Route 53 zones + records |
| `ecr.py` | ECR repositories + images |
| `ecs.py` | ECS clusters, task defs, services |

### AI / ML services (all client-only)

| File | Service |
|---|---|
| `bedrock.py` | Bedrock foundation models — invoke/converse (Claude, Titan/Nova, Llama), embeddings, images |
| `rekognition.py` | Rekognition — labels/text/faces, moderation, face collections |
| `textract.py` | Textract — OCR + forms/tables, sync + async S3 jobs |
| `comprehend.py` | Comprehend — language, sentiment, entities, key phrases, PII |
| `transcribe.py` | Transcribe — async speech-to-text jobs + custom vocabulary |
| `polly.py` | Polly — text-to-speech (sync + async S3 tasks) |
| `translate.py` | Translate — real-time + batch document translation |

> These live in the **`bedrock`, `rekognition`, `textract`, `comprehend`, `transcribe`, `polly`, `translate`** service namespaces.
> Bedrock is special: the **control plane** (`boto3.client("bedrock")`) manages models/guardrails, while the
> **runtime** (`boto3.client("bedrock-runtime")`) is what you actually call to run inference.

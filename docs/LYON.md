# Lyon Marking Checklist

## S3
- [ ] Is S3 lifecycle configuration set?
- [ ] Is S3 versioning enabled?
- [ ] Is S3 encryption enabled?
- [ ] Is S3 endpoint configured?

## DynamoDB
- [ ] Is DynamoDB used?
- [ ] Is DynamoDB table encrypted?
- [ ] Is DynamoDB table backed up?
- [ ] Is DynamoDB deletion protection enabled?
- [ ] Does DynamoDB have tags?
- [ ] Is DynamoDB endpoint configured?
- [ ] Is DynamoDB TTL enabled?
- [ ] Is DynamoDB capacity mode set (on-demand/provisioned)?

## RDS
- [ ] Is RDS deletion protection enabled?
- [ ] Is RDS config logging enabled?
- [ ] Is RDS backup retention > 7 days?

## ECS
- [ ] Does ECS use Fargate?
- [ ] Is ECS Service used?
- [ ] Is application running on ECS?
- [ ] Is ECS Container Insight enabled?
- [ ] Does ECS have AutoScaling policy (tasks >= 2)?
- [ ] Is ECS Task Definition logging enabled?

## ECR
- [ ] Is ECR lifecycle configuration set?
- [ ] Is ECR image tag immutable?
- [ ] Is ECR endpoint configured?
- [ ] Does ECR have a resource policy?

## Lambda
- [ ] Does Lambda function have a tag?

## AWS Batch
- [ ] Is AWS Batch used?
- [ ] Has AWS Batch executed successfully?

## API Gateway
- [ ] Does API Gateway have a tag?
- [ ] Is API Gateway X-Ray tracing enabled?

## CloudFront
- [ ] Is CloudFront in use?

## ALB
- [ ] Is ALB in use?
- [ ] Is ALB access log enabled?

## VPC
- [ ] Does VPC Peering exist?
- [ ] Does VPC have a tag?
- [ ] Is VPC Flow Log enabled?

## Security Group
- [ ] Is SSH inbound blocked in Security Group?
- [ ] Is 0.0.0.0/0 inbound blocked in Security Group?

## Kinesis
- [ ] Is Kinesis Analysis in use?
- [ ] Does Kinesis Analysis have a tag?
- [ ] Is Kinesis Data Stream in use?
- [ ] Is Kinesis Data Stream provisioned shard = 1?
- [ ] Is Kinesis Data Streams encryption enabled?

## EventBridge
- [ ] Is EventBridge configured with Scheduler?

## CodePipeline
- [ ] Is CodePipeline created and used?
- [ ] Does CodePipeline have an approval stage?

## CodeBuild
- [ ] Is CodeBuild created and used?

## CodeDeploy
- [ ] Is CodeDeploy created and used?

## WAF
- [ ] Is WAF configured?

## GuardDuty
- [ ] Is GuardDuty enabled?
- [ ] Does GuardDuty have a tag?
- [ ] Is GuardDuty Finding Export enabled?

## CloudWatch
- [ ] Is CloudWatch Alarm enabled?

## Parameter Store
- [ ] Is Parameter Store Intelligent-Tiering enabled?

## Cost
- [ ] Is cost ratio within recommended range (0.2-1.0)?

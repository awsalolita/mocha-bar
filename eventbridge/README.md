# EventBridge event patterns

Reusable **event patterns** for Amazon EventBridge rules — the JSON that goes in
a rule's `EventPattern` to decide which events trigger a target (Lambda, SQS,
SNS, Step Functions, etc.).

> An *event pattern* is a filter, not the event itself. Every field is an array
> of allowed values; an event matches only if **all** listed fields match and
> each field's value is in its array. Fields not listed are ignored. For a
> sample of what a delivered event looks like, see
> [`lambda/events/eventbridge/event.json`](../lambda/events/eventbridge/event.json).

## Patterns

| File                                             | Service        | Triggers on                                             |
| ------------------------------------------------ | -------------- | ------------------------------------------------------- |
| `patterns/ec2-instance-state-change.json`        | EC2            | Instance entering stopping/stopped/terminated           |
| `patterns/ec2-spot-interruption.json`            | EC2 Spot       | 2-minute Spot interruption warning                      |
| `patterns/autoscaling-instance-lifecycle.json`   | Auto Scaling   | ASG instance launch/terminate (success or failure)      |
| `patterns/codebuild-build-state-change.json`     | CodeBuild      | Build succeeded/failed/stopped for a project            |
| `patterns/codepipeline-execution-state-change.json` | CodePipeline | Pipeline execution state transitions                    |
| `patterns/codecommit-repository-state-change.json` | CodeCommit   | Push/commit to `main` or `release` branch               |
| `patterns/ecs-task-state-change.json`            | ECS           | Task stopped (with a stop reason)                        |
| `patterns/ecr-image-push.json`                   | ECR           | Successful image push                                    |
| `patterns/batch-job-state-change.json`           | AWS Batch      | Job succeeded/failed                                     |
| `patterns/s3-object-created.json`                | S3            | Object created under a prefix (bucket EventBridge on)   |
| `patterns/rds-db-instance-event.json`            | RDS            | Failure/failover/maintenance/availability events        |
| `patterns/glue-job-state-change.json`            | Glue           | ETL job succeeded/failed/timeout/stopped                |
| `patterns/stepfunctions-execution-status-change.json` | Step Functions | Execution failed/timed out/aborted                 |
| `patterns/ssm-parameter-store-change.json`       | SSM            | Parameter create/update/delete under a path             |
| `patterns/tag-change-on-resource.json`           | Tagging        | Tag added/removed/changed on a resource                 |
| `patterns/cloudtrail-api-call.json`              | CloudTrail     | S3 bucket policy/ACL/public-access API calls            |
| `patterns/cloudtrail-root-account-usage.json`    | CloudTrail     | Any API call made by the root user                      |
| `patterns/cloudtrail-console-signin-failure.json`| CloudTrail     | Failed console sign-in                                   |
| `patterns/cloudtrail-iam-changes.json`           | CloudTrail     | IAM user/key/policy mutations                           |
| `patterns/guardduty-finding.json`                | GuardDuty      | Findings with severity >= 4 (Medium and above)          |
| `patterns/securityhub-findings-imported.json`    | Security Hub   | New HIGH/CRITICAL findings                              |
| `patterns/config-compliance-change.json`         | AWS Config     | Resource becoming NON_COMPLIANT                          |
| `patterns/health-event.json`                     | AWS Health     | Service issues / scheduled changes for EC2/RDS/EKS       |

## Notes on specific patterns

- **CloudTrail-based patterns** (`cloudtrail-*`) require a CloudTrail trail to be
  logging in the account/region. They match on the
  `AWS API Call via CloudTrail` / `AWS Console Sign In via CloudTrail`
  detail-types. Only write/management events are delivered by default; enable
  data events on the trail for object-level S3/Lambda calls.
- **`s3-object-created.json`** uses native S3 → EventBridge notifications. Turn
  it on per bucket (`aws s3api put-bucket-notification-configuration
  --notification-configuration '{"EventBridgeConfiguration":{}}'`) — it does not
  need CloudTrail.
- **Placeholders** like `mocha-bar-build`, `mocha-bar-uploads`, and
  `/mocha-bar/` are examples. Remove or replace the narrowing fields
  (`project-name`, `bucket.name`, `name` prefix, branch names) to broaden a
  pattern.

## Content filtering (matching operators)

Beyond exact string matches, EventBridge supports richer matching, used here in
`guardduty-finding.json`, `ssm-parameter-store-change.json`, and
`s3-object-created.json`:

```json
{
  "detail": {
    "severity":  [{ "numeric": [">=", 7] }],
    "name":      [{ "prefix": "/prod/" }],
    "key":       [{ "suffix": ".json" }],
    "state":     [{ "anything-but": ["PENDING"] }],
    "reason":    [{ "exists": true }]
  }
}
```

## Create a rule from a pattern

```bash
# 1. Create the rule with the event pattern
aws events put-rule \
  --name mocha-bar-codebuild-failed \
  --event-pattern file://eventbridge/patterns/codebuild-build-state-change.json

# 2. Attach a target (e.g. an SNS topic)
aws events put-targets \
  --rule mocha-bar-codebuild-failed \
  --targets 'Id=1,Arn=arn:aws:sns:us-east-1:123456789012:mocha-bar-alerts'
```

Test a pattern against a sample event without creating a rule:

```bash
aws events test-event-pattern \
  --event-pattern file://eventbridge/patterns/ec2-instance-state-change.json \
  --event file://lambda/events/eventbridge/event.json
```

## Scheduled rules (not event patterns)

Time-based triggers (e.g. "every 5 minutes", "0 9 * * ? *") do **not** use an
event pattern. Use a schedule expression instead:

```bash
aws events put-rule \
  --name mocha-bar-nightly \
  --schedule-expression "cron(0 3 * * ? *)"
```

EventBridge Scheduler (`aws scheduler create-schedule`) is the newer, dedicated
service for this and supports one-time schedules and time zones.

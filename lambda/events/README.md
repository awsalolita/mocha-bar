# Lambda event handlers

Reference AWS Lambda handlers, one per common event source. Each service has
its own folder with:

For handlers that *call* Textract, Rekognition, Comprehend, and the other AI
APIs, see [`../ai/`](../ai/).

- `event.json` — a realistic sample event as AWS delivers it to Lambda.
- `handler.py` — a Python handler (`lambda_handler(event, context)`) that
  parses that event and pulls out the useful fields.

## Services

| Folder                | Source                              | Invocation   | Key parsing detail                                   |
| --------------------- | ----------------------------------- | ------------ | ---------------------------------------------------- |
| `s3/`                 | S3 object events                    | Async        | Batched `Records`; object keys are URL-encoded       |
| `apigateway/`         | API Gateway REST (proxy, v1)        | Sync         | Flat request; return `{statusCode, headers, body}`   |
| `apigateway-http/`    | API Gateway HTTP API (v2)           | Sync         | HTTP details under `requestContext.http`             |
| `sqs/`                | SQS queue                           | Poll (batch) | Return `batchItemFailures` for partial failures      |
| `sns/`                | SNS topic                           | Async        | Payload string in `Sns.Message`                      |
| `dynamodb/`           | DynamoDB Streams                    | Poll (batch) | Attribute-value wire format; INSERT/MODIFY/REMOVE    |
| `kinesis/`            | Kinesis Data Streams                | Poll (batch) | Record `data` is base64                              |
| `eventbridge/`        | EventBridge / scheduled rules       | Async        | Single event (no `Records`); payload in `detail`     |
| `cloudwatch-logs/`    | CloudWatch Logs subscription filter | Async        | `awslogs.data` is base64 + gzip JSON                 |
| `cognito/`            | Cognito User Pool trigger           | Sync         | Must return the whole (mutated) `event`              |
| `ses/`                | SES inbound email receipt rule      | Sync/Async   | Metadata + verdicts only; return `disposition`       |
| `iot/`                | IoT Core topic rule action          | Async        | Payload is the rule's SQL SELECT output (no wrapper) |
| `cloudfront/`         | CloudFront → Function URL origin    | Sync         | Same as Function URL / HTTP API v2; look for `via` / `cloudfront-*` headers |

## Test a handler locally

Each handler is plain Python with no third-party dependencies, so you can feed
it the sample event directly:

```bash
cd lambda/events
python -c "import json, importlib.util as u; \
s=u.spec_from_file_location('h','s3/handler.py'); m=u.module_from_spec(s); s.loader.exec_module(m); \
print(m.lambda_handler(json.load(open('s3/event.json')), None))"
```

Or from a Python REPL:

```python
import json
from s3 import handler  # if running with lambda/events on the path

event = json.load(open("s3/event.json"))
print(handler.lambda_handler(event, None))
```

## Notes

- Runtime target: Python 3.12. Handlers use only the standard library.
- Batch sources (SQS, Kinesis, DynamoDB) support partial-batch responses;
  enable `ReportBatchItemFailures` on the event source mapping to use them.
- Sample account IDs, ARNs, and signatures are placeholders — replace with
  your own when wiring real infrastructure.

# KEDA (Kubernetes Event-driven Autoscaling)

## 1. Install KEDA via Helm

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore
helm install keda kedacore/keda -n keda --create-namespace
```

## 2. Create CloudWatch IAM Policy

Create an IAM policy that allows KEDA to query CloudWatch metrics:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3. Attach Policy to KEDA Service Account

Associate the IAM policy with the KEDA operator service account:

```bash
eksctl create iamserviceaccount \
  --cluster unicorn-cluster \
  --namespace keda \
  --name keda-operator \
  --attach-policy-arn arn:aws:iam::<AWS_ACCOUNT_ID>:policy/keda_cloudwatch \
  --override-existing-serviceaccounts \
  --approve
```

## 4. Deploy TriggerAuthentication and ScaledObject

Apply the KEDA `TriggerAuthentication` and `ScaledObject` in your application namespace (e.g. `my-app` scaling on an SQS queue):

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws-auth
  namespace: my-app
spec:
  podIdentity:
    provider: aws-eks
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-app-cw
  namespace: my-app
spec:
  scaleTargetRef:
    name: my-app          # Deployment name
  minReplicaCount: 2
  maxReplicaCount: 20
  pollingInterval: 30     # How often KEDA queries CloudWatch (seconds)
  cooldownPeriod: 300     # Wait before scale-in (seconds)
  triggers:
    - type: aws-cloudwatch
      authenticationRef:
        name: keda-aws-auth
      metadata:
        awsRegion: us-east-1
        namespace: AWS/SQS                    # or AWS/ApplicationELB, or custom
        metricName: ApproximateNumberOfMessagesVisible
        dimensions: QueueName=my-queue
        targetMetricValue: "10"
        minMetricValue: "0"
        metricStat: Average
        metricCollectionTime: "300"
        metricUnit: Count
        identityOwner: operator
```

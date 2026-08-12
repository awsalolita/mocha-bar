helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda -n keda --create-namespace


# Create this policy for keda
{
  "Effect": "Allow",
  "Action": [
    "cloudwatch:GetMetricData",
    "cloudwatch:GetMetricStatistics",
    "cloudwatch:ListMetrics"
  ],
  "Resource": "*"
}

### attach policy to the keda sa
eksctl create iamserviceaccount \
  --cluster unicorn-cluster \
  --namespace keda \
  --name keda-operator \
  --attach-policy-arn arn:aws:iam::298367968222:policy/keda_cloudwatch \
  --override-existing-serviceaccounts \
  --approve

### KEDA deploy in app namespace
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
  pollingInterval: 30     # how often KEDA queries CloudWatch
  cooldownPeriod: 300     # wait before scale-in
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
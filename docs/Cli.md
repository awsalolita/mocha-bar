## Enable log deletion policy and set log retention over 7 days
```bash
for group in $(aws logs describe-log-groups --query 'logGroups[*].logGroupName' --output text); do
  echo "Updating retention for $group"
  aws logs put-retention-policy --log-group-name "$group" --retention-in-days 14
done

for group in $(aws logs describe-log-groups --query 'logGroups[*].logGroupName' --output text); do
  echo "Enabling deletion protection for $group"
  aws logs put-log-group-deletion-protection \
    --log-group-identifier "$group" \
    --deletion-protection-enabled
done
```

## Put alarm cloudwatch
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "HighCPU-Alert" \
  --alarm-description "Triggers when CPU exceeds 80% for 10 minutes" \
  --metric-name "CPUUtilization" \
  --namespace "AWS/EC2" \
  --statistic "Average" \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=InstanceId,Value=i-1234567890abcdef0" \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:YourSNSTopicName"
```

## CloudFront: High 5xx Error Rate
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "CloudFront-High5xxErrorRate" \
  --alarm-description "Triggers if CloudFront 5xx errors exceed 5% for 5 minutes" \
  --metric-name "5xxErrorRate" \
  --namespace "AWS/CloudFront" \
  --statistic "Average" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=DistributionId,Value=YOUR_DISTRIBUTION_ID" "Name=Region,Value=Global" \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:YourSNSTopicName"
```

## Application Load Balancer (ALB): Target 5xx Errors
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ALB-HighTarget5xxErrors" \
  --alarm-description "Triggers if targets behind the ALB return >10 5xx errors in 5 minutes" \
  --metric-name "HTTPCode_Target_5XX_Count" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=LoadBalancer,Value=app/YOUR_ALB_NAME/1234567890abcdef" \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:YourSNSTopicName"
```

## Elastic Container Service (ECS): Cluster CPU Utilization
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "ECS-HighCPUUtilization" \
  --alarm-description "Triggers if ECS cluster CPU exceeds 80% for 10 minutes" \
  --metric-name "CPUUtilization" \
  --namespace "AWS/ECS" \
  --statistic "Average" \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=ClusterName,Value=YOUR_ECS_CLUSTER_NAME" \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:YourSNSTopicName"
```

## Elastic Kubernetes Service (EKS): Node CPU Utilization
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-NodeHighCPU" \
  --alarm-description "Triggers if EKS node CPU exceeds 80% for 10 minutes" \
  --metric-name "node_cpu_utilization" \
  --namespace "ContainerInsights" \
  --statistic "Average" \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=ClusterName,Value=YOUR_EKS_CLUSTER_NAME" \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:YourSNSTopicName"
```

## API Gateway: 5xx Server Errors
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "APIGateway-High5xxErrors" \
  --alarm-description "Triggers if API Gateway returns >10 5xx errors in 5 minutes" \
  --metric-name "5XXError" \
  --namespace "AWS/ApiGateway" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=ApiName,Value=YOUR_API_NAME" \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:YourSNSTopicName"
```

## VPC (NAT Gateway): Port Allocation Errors
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "NATGateway-ErrorPortAllocation" \
  --alarm-description "Triggers if NAT Gateway fails to allocate ports (SNAT exhaustion)" \
  --metric-name "ErrorPortAllocation" \
  --namespace "AWS/NATGateway" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 0 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=NatGatewayId,Value=YOUR_NAT_GATEWAY_ID" \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:YourSNSTopicName"
```

## EventBridge put event

```json
# event.json
[
  {
    "EventBusName": "default",
    "Source": "com.mycompany.myapp",
    "DetailType": "UserSignup",
    "Detail": "{\"userId\": \"12345\", \"status\": \"active\"}"
  }
]

```

```bash
aws events put-events --entries file://event.json
```


```bash
#!/bin/bash

TARGET_REGION=""
KMS_KEY_ARN=""

# Loop through all buckets in the account
for bucket in $(aws s3api list-buckets --query 'Buckets[*].Name' --output text); do
  
  # Determine the bucket's region
  LOCATION=$(aws s3api get-bucket-location --bucket "$bucket" --query 'LocationConstraint' --output text)
  
  # AWS returns "None" for buckets in us-east-1, standardizing it here
  if [ "$LOCATION" == "None" ]; then LOCATION="us-east-1"; fi
  
  # Only process buckets in the target region
  if [ "$LOCATION" == "$TARGET_REGION" ]; then
    echo "Processing $bucket in $LOCATION..."
    
    # 1. Apply Lifecycle Rule: Transition to Glacier after 90 days
    aws s3api put-bucket-lifecycle-configuration \
      --bucket "$bucket" \
      --lifecycle-configuration '{
        "Rules": [
          {
            "ID": "TransitionAllToGlacierAfter90Days",
            "Filter": {
              "Prefix": ""
            },
            "Status": "Enabled",
            "Transitions": [
              {
                "Days": 90,
                "StorageClass": "GLACIER"
              }
            ]
          }
        ]
      }'
      
    # 2. Enable Default Encryption with Customer Managed Key (CMK)
    # Note: BucketKeyEnabled=true reduces KMS costs by using S3 Bucket Keys
    aws s3api put-bucket-encryption \
      --bucket "$bucket" \
      --server-side-encryption-configuration "{
        \"Rules\": [
          {
            \"ApplyServerSideEncryptionByDefault\": {
              \"SSEAlgorithm\": \"aws:kms\",
              \"KMSMasterKeyID\": \"$KMS_KEY_ARN\"
            },
            \"BucketKeyEnabled\": true
          }
        ]
      }"
      
    echo "Successfully updated $bucket."
  fi
done
```
## Create this policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::YOUR_BUCKET"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:DeleteObject"
      ],
      "Resource": ["arn:aws:s3:::YOUR_BUCKET/*"]
    }
  ]
}

eksctl create iamserviceaccount \
  --name s3-csi-driver-sa \
  --namespace kube-system \
  --cluster unicorn \
  --attach-policy-arn arn:aws:iam::720691796403:policy/s3_readonly_policy \
  --approve \
  --role-name AmazonEKS_S3_CSI_DriverRole \
  --region us-east-1 \
  --role-only


helm repo add aws-mountpoint-s3-csi-driver https://awslabs.github.io/mountpoint-s3-csi-driver
helm repo update
helm upgrade --install aws-mountpoint-s3-csi-driver \
  --namespace kube-system \
  --set node.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="arn:aws:iam::720691796403:role/AmazonEKS_S3_CSI_DriverRole" \
  aws-mountpoint-s3-csi-driver/aws-mountpoint-s3-csi-driver
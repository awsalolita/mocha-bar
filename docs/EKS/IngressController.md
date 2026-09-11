# AWS Load Balancer Controller

## 1. Environment Variables

```bash
export NAMESPACE="kube-system"
export CLUSTER_NAME="concert-eks"
export VPC_ID="vpc-0fd0de8790becb5cd"
export REGION="us-east-1"
```

## 2. Tag Subnets for ALB

Tag public subnets for internet-facing ALBs:

```bash
PUBLIC_SUBNETS="subnet-0f734812c1db682b2 subnet-0682663ac766f65c7"
aws ec2 create-tags --resources $PUBLIC_SUBNETS --tags Key=kubernetes.io/cluster/$CLUSTER_NAME,Value=shared Key=kubernetes.io/role/elb,Value=1
```

Tag private subnets for internal ALBs:

```bash
PRIVATE_SUBNETS="subnet-0e1a02ac2bd74c889 subnet-0142d434bf07c9117"
aws ec2 create-tags --resources $PRIVATE_SUBNETS --tags Key=kubernetes.io/cluster/$CLUSTER_NAME,Value=shared Key=kubernetes.io/role/internal-elb,Value=1
```

## 3. Enable VPC DNS Attributes

```bash
# Enable DNS resolution
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
```

## 4. Create IAM Policy

Download the recommended IAM policy and create it in AWS:

```bash
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json
```

## 5. Create IAM Service Account

Create the service account and attach the IAM policy:

```bash
eksctl create iamserviceaccount \
  --cluster ${CLUSTER_NAME} \
  --region ${REGION} \
  --namespace kube-system \
  --name aws-lb \
  --attach-policy-arn arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve
```

## 6. Deploy AWS Load Balancer Controller via Helm

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace ${NAMESPACE} \
  --set clusterName=${CLUSTER_NAME} \
  --set region=${REGION} \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-lb \
  --set vpcId=${VPC_ID}
```

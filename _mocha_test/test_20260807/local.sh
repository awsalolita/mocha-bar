## for enabling OIDV provider in EKS
eksctl utils associate-iam-oidc-provider \
  --cluster project-cluster \
  --region us-east-1 \
  --approve

aws eks describe-cluster \
  --name YOUR_CLUSTER_NAME \
  --query "cluster.identity.oidc.issuer" \
  --output text

aws iam create-open-id-connect-provider \
  --url https://oidc.eks.REGION.amazonaws.com/id/OIDC_ID \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 9e99a48a9960b14926bb7f3b02e22da2b0ab7280


# Tag public subnets
PUBLIC_SUBNETS="subnet-09e1d10c77a35c52b subnet-09f6f58c7cc6a51ac"
PRIVATE_SUBNETS="subnet-03923e9bb28323962 subnet-06c1603bbf472d90a"
EKS_NAME="project-cluster"
VPC_ID="vpc-07a7440a55e94349f"

aws ec2 create-tags --resources $PUBLIC_SUBNETS --tags Key=kubernetes.io/cluster/$EKS_NAME,Value=shared Key=kubernetes.io/role/elb,Value=1

# Tag private subnets
aws ec2 create-tags --resources $PRIVATE_SUBNETS --tags Key=kubernetes.io/cluster/$EKS_NAME,Value=shared Key=kubernetes.io/role/internal-elb,Value=1


# Enable DNS resolution
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Create sa in kube-system namespace for granting permission
kubectl create sa aws-lb -n kube-system

# Create IAM Policy for the ALB
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

aws iam create-policy  --policy-name AWSLoadBalancerControllerIAMPolicy --policy-document file://iam_policy.json

# In the dashboard from PodIdentityRole, attach the policy to the Role with the sa.

helm repo add eks https://aws.github.io/eks-charts

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller --set clusterName=$EKS_NAME --set region=us-east-1 --set serviceAccount.create=false --set serviceAccount.name=aws-lb --set vpcId=$VPC_ID -n kube-system

# for guardduty i need to enable guardduty endpoints in vpc
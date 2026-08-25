# get config for a cluster in region 
aws eks update-kubeconfig --region us-east-1 --name unicorn

# enable OIDC provider
eksctl utils associate-iam-oidc-provider --cluster unicorn --region us-east-1 --approve

# describe cluster
aws eks describe-cluster --name YOUR_CLUSTER_NAME --query "cluster.identity.oidc.issuer" --output text

# EKS managed node group
aws eks update-nodegroup-config \
  --cluster-name unicorn \
  --nodegroup-name app-ng \
  --scaling-config minSize=3,maxSize=5,desiredSize=3

# increase the max pods
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true


## Tag subnets for alb
PUBLIC_SUBNETS="subnet-0e25872d6708dfd00 subnet-0258a22c15e82c3b1"
PRIVATE_SUBNETS="subnet-064f436baff8f0723 subnet-0862a9409c71a7aae"
EKS_NAME="app-cluster"
VPC_ID="vpc-0b8972f42da2b8497"

aws ec2 create-tags --resources $PUBLIC_SUBNETS --tags Key=kubernetes.io/cluster/$EKS_NAME,Value=shared Key=kubernetes.io/role/elb,Value=1

# Tag private subnets
aws ec2 create-tags --resources $PRIVATE_SUBNETS --tags Key=kubernetes.io/cluster/$EKS_NAME,Value=shared Key=kubernetes.io/role/internal-elb,Value=1


# Enable DNS resolution
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

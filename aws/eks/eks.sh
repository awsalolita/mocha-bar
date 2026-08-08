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
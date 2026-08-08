# get config for a cluster in region 
aws eks update-kubeconfig --region us-east-1 --name unicorn-cluster

# enable OIDC provider
eksctl utils associate-iam-oidc-provider \
  --cluster unicorn-cluster \
  --region us-east-1 \
  --approve

# describe cluster
aws eks describe-cluster \
  --name YOUR_CLUSTER_NAME \
  --query "cluster.identity.oidc.issuer" \
  --output text

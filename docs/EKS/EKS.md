# EKS Cluster Management

## 1. Update Kubeconfig

Retrieve the kubeconfig for a cluster in a given region:

```bash
aws eks update-kubeconfig --region us-east-1 --name unicorn
```

## 2. Enable IAM OIDC Provider

Associate the IAM OIDC provider for IRSA (IAM Roles for Service Accounts):

```bash
eksctl utils associate-iam-oidc-provider --cluster unicorn --region us-east-1 --approve
```

## 3. Describe Cluster OIDC Issuer

```bash
aws eks describe-cluster --name YOUR_CLUSTER_NAME --query "cluster.identity.oidc.issuer" --output text
```

## 4. Managed Node Group Scaling Configuration

Update the scaling configuration for an EKS managed node group:

```bash
aws eks update-nodegroup-config \
  --cluster-name unicorn \
  --nodegroup-name app-ng \
  --scaling-config minSize=3,maxSize=5,desiredSize=3
```

## 5. Increase Max Pods (Prefix Delegation)

Enable prefix delegation on the AWS VPC CNI daemonset to significantly increase the pod density per node:

```bash
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
```


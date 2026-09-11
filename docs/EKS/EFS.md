# AWS EFS CSI Driver

> **Note**: Before installing the driver, ensure you have created an EFS file system and an EFS Security Group that allows inbound NFS traffic from your EKS worker node security group.

## 1. Create IAM Service Account

Create the IAM service account for the EFS CSI driver:

```bash
eksctl create iamserviceaccount \
  --name efs-csi-controller-sa \
  --namespace kube-system \
  --cluster unicorn \
  --role-name EFSRole \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy \
  --approve \
  --region us-east-1
```

## 2. Install via Helm

```bash
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update aws-efs-csi-driver

helm upgrade --install aws-efs-csi-driver \
  --namespace kube-system \
  aws-efs-csi-driver/aws-efs-csi-driver \
  --set controller.serviceAccount.create=false \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

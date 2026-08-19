### Install EBS
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster unicorn \
  --role-name EBSRole \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve \
  --region us-east-1


eksctl create addon \
  --name aws-ebs-csi-driver \
  --cluster <CLUSTER_NAME> \
  --service-account-role-arn arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME> \
  --force

### or helm
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm repo update
helm upgrade --install aws-ebs-csi-driver \
  aws-ebs-csi-driver/aws-ebs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=false \
  --set controller.serviceAccount.name=ebs-csi-controller-sa


########### Install EFS csi controller on eks ###########
####### Before this create efs and efs-sg which allows inbound from eks node's sg #######
#########################################################################################
eksctl create iamserviceaccount \
  --name efs-csi-controller-sa \
  --namespace kube-system \
  --cluster unicorn \
  --role-name EFSRole \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy \
  --approve \
  --region us-east-1

helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update aws-efs-csi-driver
helm upgrade --install aws-efs-csi-driver \
  --namespace kube-system \
  aws-efs-csi-driver/aws-efs-csi-driver \
  --set controller.serviceAccount.create=false \
  --set controller.serviceAccount.name=efs-csi-controller-sa
##################### SET RESOURCES FOR PODS #####################

CLUSTER=unicorn
ASG=eks-app-ng-2ed0391f-fc4b-66f1-6b87-19d93cfc3d7a
AUTOSCALER_IMAGE_TAG=v1.36.1 # Set this to match your EKS cluster version

aws autoscaling create-or-update-tags --tags \
  "ResourceId=$ASG,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=true" \
  "ResourceId=$ASG,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/$CLUSTER,Value=owned,PropagateAtLaunch=true"

cat << EOF > cluster_autoscaler_policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "autoscaling:DescribeAutoScalingGroups",
                "autoscaling:DescribeAutoScalingInstances",
                "autoscaling:DescribeLaunchConfigurations",
                "autoscaling:DescribeScalingActivities",
                "autoscaling:DescribeTags",
                "ec2:DescribeImages",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeLaunchTemplateVersions",
                "ec2:GetInstanceTypesFromInstanceRequirements",
                "eks:DescribeNodegroup"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "autoscaling:SetDesiredCapacity",
                "autoscaling:TerminateInstanceInAutoScalingGroup"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:ResourceTag/k8s.io/cluster-autoscaler/enabled": "true",
                    "aws:ResourceTag/k8s.io/cluster-autoscaler/${CLUSTER}": "owned"
                }
            }
        }
    ]
}
EOF

# Create the IAM Policy first
POLICY_ARN=$(aws iam create-policy \
  --policy-name AmazonEKSClusterAutoscalerPolicy \
  --policy-document file://cluster_autoscaler_policy.json \
  --query 'Policy.Arn' \
  --output text)

eksctl create iamserviceaccount \
  --cluster=${CLUSTER} \
  --namespace=kube-system \
  --name=cluster-autoscaler \
  --attach-policy-arn=${POLICY_ARN} \
  --override-existing-serviceaccounts \
  --approve \
  --region=us-east-1

helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update
helm upgrade --install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set cloudProvider=aws \
  --set awsRegion=us-east-1 \
  --set autoDiscovery.clusterName=${CLUSTER} \
  --set rbac.serviceAccount.create=false \
  --set rbac.serviceAccount.name=cluster-autoscaler \
  --set image.tag=${AUTOSCALER_IMAGE_TAG} \
  --set extraArgs.balance-similar-node-groups=true \
  --set extraArgs.skip-nodes-with-local-storage=false \
  --set extraArgs.skip-nodes-with-system-pods=false \
  --set extraArgs.scale-down-unneeded-time=5m \
  --set extraArgs.scale-down-delay-after-add=2m \
  --set extraArgs.scan-interval=10s
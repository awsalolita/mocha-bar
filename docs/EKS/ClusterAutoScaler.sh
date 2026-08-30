CLUSTER=unicorn-cluster
ASG=eks-app-ng-42cff051-521e-402e-0f6f-b654ef7c6fa6

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
                    "aws:ResourceTag/k8s.io/cluster-autoscaler/unicorn": "owned"
                }
            }
        }
    ]
}
EOF

eksctl create iamserviceaccount \
  --cluster=${CLUSTER} \
  --namespace=kube-system \
  --name=cluster-autoscaler \
  --attach-policy-arn=arn:aws:iam::353615901360:policy/cluster-autoscaler-9f62bae2173af9928fe85f9701 \
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
  --set extraArgs.balance-similar-node-groups=true \
  --set extraArgs.skip-nodes-with-local-storage=false \
  --set extraArgs.skip-nodes-with-system-pods=false \
  --set extraArgs.scale-down-unneeded-time=5m \
  --set extraArgs.scale-down-delay-after-add=2m \
  --set extraArgs.scan-interval=10s
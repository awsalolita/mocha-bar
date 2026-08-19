export CLUSTER_NAME=unicorn-cluster
export AWS_REGION=us-east-1
export AWS_PARTITION=aws
export KARPENTER_NAMESPACE=kube-system
export KARPENTER_VERSION=1.14.0
export AWS_ACCOUNT_ID=298367968222
export OIDC_ENDPOINT=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query "cluster.identity.oidc.issuer" --output text)
export CLUSTER_ENDPOINT=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query "cluster.endpoint" --output text)
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION"
kubectl get nodes   # must work before continuing


## Node iam role
cat > node-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "ec2.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF
aws iam create-role \
  --role-name "KarpenterNodeRole-${CLUSTER_NAME}" \
  --assume-role-policy-document file://node-trust-policy.json
aws iam attach-role-policy --role-name "KarpenterNodeRole-${CLUSTER_NAME}" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
aws iam attach-role-policy --role-name "KarpenterNodeRole-${CLUSTER_NAME}" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
aws iam attach-role-policy --role-name "KarpenterNodeRole-${CLUSTER_NAME}" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly"
aws iam attach-role-policy --role-name "KarpenterNodeRole-${CLUSTER_NAME}" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"

## Create controller policy
cat > controller-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/${OIDC_ENDPOINT#*//}"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "${OIDC_ENDPOINT#*//}:aud": "sts.amazonaws.com",
        "${OIDC_ENDPOINT#*//}:sub": "system:serviceaccount:${KARPENTER_NAMESPACE}:karpenter"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name "KarpenterControllerRole-${CLUSTER_NAME}" \
  --assume-role-policy-document file://controller-trust-policy.json


### Create the controllet-policy json file
cat << EOF > controller-policy.json
{
    "Statement": [
        {
            "Action": [
                "ssm:GetParameter",
                "ec2:DescribeImages",
                "ec2:RunInstances",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeLaunchTemplates",
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeInstanceTypeOfferings",
                "ec2:DeleteLaunchTemplate",
                "ec2:CreateTags",
                "ec2:CreateLaunchTemplate",
                "ec2:CreateFleet",
                "ec2:DescribeSpotPriceHistory",
                "pricing:GetProducts"
            ],
            "Effect": "Allow",
            "Resource": "*",
            "Sid": "Karpenter"
        },
        {
            "Action": "ec2:TerminateInstances",
            "Condition": {
                "StringLike": {
                    "ec2:ResourceTag/karpenter.sh/nodepool": "*"
                }
            },
            "Effect": "Allow",
            "Resource": "*",
            "Sid": "ConditionalEC2Termination"
        },
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:${AWS_PARTITION}:iam::${AWS_ACCOUNT_ID}:role/KarpenterNodeRole-${CLUSTER_NAME}",
            "Sid": "PassNodeIAMRole"
        },
        {
            "Effect": "Allow",
            "Action": "eks:DescribeCluster",
            "Resource": "arn:${AWS_PARTITION}:eks:${AWS_REGION}:${AWS_ACCOUNT_ID}:cluster/${CLUSTER_NAME}",
            "Sid": "EKSClusterEndpointLookup"
        },
        {
            "Sid": "AllowScopedInstanceProfileCreationActions",
            "Effect": "Allow",
            "Resource": "*",
            "Action": [
                "iam:CreateInstanceProfile"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:RequestTag/kubernetes.io/cluster/${CLUSTER_NAME}": "owned",
                    "aws:RequestTag/topology.kubernetes.io/region": "${AWS_REGION}"
                },
                "StringLike": {
                    "aws:RequestTag/karpenter.k8s.aws/ec2nodeclass": "*"
                }
            }
        },
        {
            "Sid": "AllowScopedInstanceProfileTagActions",
            "Effect": "Allow",
            "Resource": "*",
            "Action": [
                "iam:TagInstanceProfile"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:ResourceTag/kubernetes.io/cluster/${CLUSTER_NAME}": "owned",
                    "aws:ResourceTag/topology.kubernetes.io/region": "${AWS_REGION}",
                    "aws:RequestTag/kubernetes.io/cluster/${CLUSTER_NAME}": "owned",
                    "aws:RequestTag/topology.kubernetes.io/region": "${AWS_REGION}"
                },
                "StringLike": {
                    "aws:ResourceTag/karpenter.k8s.aws/ec2nodeclass": "*",
                    "aws:RequestTag/karpenter.k8s.aws/ec2nodeclass": "*"
                }
            }
        },
        {
            "Sid": "AllowScopedInstanceProfileActions",
            "Effect": "Allow",
            "Resource": "*",
            "Action": [
                "iam:AddRoleToInstanceProfile",
                "iam:RemoveRoleFromInstanceProfile",
                "iam:DeleteInstanceProfile"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:ResourceTag/kubernetes.io/cluster/${CLUSTER_NAME}": "owned",
                    "aws:ResourceTag/topology.kubernetes.io/region": "${AWS_REGION}"
                },
                "StringLike": {
                    "aws:ResourceTag/karpenter.k8s.aws/ec2nodeclass": "*"
                }
            }
        },
        {
            "Sid": "AllowInstanceProfileReadActions",
            "Effect": "Allow",
            "Resource": "*",
            "Action": "iam:GetInstanceProfile"
        },
        {
            "Sid": "AllowUnscopedInstanceProfileListAction",
            "Effect": "Allow",
            "Resource": "*",
            "Action": "iam:ListInstanceProfiles"
        }
    ],
    "Version": "2012-10-17"
}
EOF

aws iam put-role-policy --role-name "KarpenterControllerRole-${CLUSTER_NAME}" \
    --policy-name "KarpenterControllerPolicy-${CLUSTER_NAME}" \
    --policy-document file://controller-policy.json


# Subnets (your private ones)
aws ec2 create-tags \
  --resources subnet-0e8aeab9ae39bbb54 subnet-07668594acb45a1cb \
  --tags Key=karpenter.sh/discovery,Value=${CLUSTER_NAME}

# Cluster security group
SG=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query "cluster.resourcesVpcConfig.clusterSecurityGroupId" --output text)
aws ec2 create-tags \
  --resources "$SG" \
  --tags Key=karpenter.sh/discovery,Value=${CLUSTER_NAME}

## Let karpenter nodes join the cluster
eksctl create iamidentitymapping \
  --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION" \
  --arn "arn:aws:iam::${AWS_ACCOUNT_ID}:role/KarpenterNodeRole-${CLUSTER_NAME}" \
  --username "system:node:{{EC2PrivateDNSName}}" \
  --group system:bootstrappers \
  --group system:nodes


helm upgrade --install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "${KARPENTER_VERSION}" \
  --namespace "${KARPENTER_NAMESPACE}" \
  --create-namespace \
  --set settings.disableDryRun=true \
  --set settings.isolatedVPC=true \
  --set "settings.clusterName=${CLUSTER_NAME}" \
  --set "settings.clusterEndpoint=${CLUSTER_ENDPOINT}" \
  --set "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=arn:aws:iam::${AWS_ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME}" \
  --set controller.resources.requests.cpu=100m \
  --set controller.resources.requests.memory=256Mi \
  --wait


cat <<EOF | kubectl apply -f -
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  role: KarpenterNodeRole-unicorn-cluster
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: unicorn-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: unicorn-cluster
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      requirements:
        - key: "karpenter.sh/capacity-type"
          operator: In
          values: ["on-demand"]
        - key: "node.kubernetes.io/instance-type"
          operator: In
          values: ["t3.medium"]
  limits:
    cpu: "100"
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
EOF

## Test
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inflate
spec:
  replicas: 0
  selector:
    matchLabels:
      app: inflate
  template:
    metadata:
      labels:
        app: inflate
    spec:
      terminationGracePeriodSeconds: 0
      containers:
        - name: inflate
          image: public.ecr.aws/eks-distro/kubernetes/pause:3.7
          resources:
            requests:
              cpu: 1
EOF
kubectl scale deployment inflate --replicas=5
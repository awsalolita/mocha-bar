export NAMESPACE="kube-system"
export CLUSTER_NAME="unicorn-cluster"
export VPC_ID="vpc-014b4c26e8138665b"
export REGION="us-east-1"

curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json
# 3) Create SA + role + policy (do NOT kubectl create sa first)

eksctl create iamserviceaccount \
  --cluster ${CLUSTER_NAME} \
  --region ${REGION} \
  --namespace kube-system \
  --name aws-lb \
  --attach-policy-arn arn:aws:iam::353615901360:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve


helm repo add eks https://aws.github.io/eks-charts

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
    --set clusterName=${CLUSTER_NAME} \
    --set region=${REGION}  \
    --set serviceAccount.create=false \
    --set serviceAccount.name=aws-lb \
    --set vpcId=${VPC_ID} \
    -n ${NAMESPACE}

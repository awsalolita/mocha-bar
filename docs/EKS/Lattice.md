## Install the gateway-api crds
```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.2/standard-install.yaml
```

## Create the policy

```bash
curl -o vpc-lattice-controller-policy.json https://raw.githubusercontent.com/aws/aws-application-networking-k8s/main/files/controller-installation/recommended-inline-policy.json

aws iam create-policy \
    --policy-name VPCLatticeControllerIAMPolicy \
    --policy-document file://vpc-lattice-controller-policy.json

eksctl create iamserviceaccount \
    --cluster=<CLUSTER_NAME> \
    --namespace=aws-application-networking-system \
    --name=gateway-api-controller \
    --attach-policy-arn=arn:aws:iam::<ACCOUNT_ID>:policy/VPCLatticeControllerIAMPolicy \
    --override-existing-serviceaccounts \
    --approve

```

## 1. Install helm chart

```bash
helm upgrade --install gateway-api-controller \
  oci://public.ecr.aws/aws-application-networking-k8s/aws-gateway-controller-chart \
  --version=v2.1.3 \
  --namespace aws-application-networking-system \
  --set clusterName=<CLUSTER_NAME> \
  --set serviceAccount.create=false \
  --set serviceAccount.name=gateway-api-controller \
  --set clusterVpcId=<VPC_ID> \
  --set awsRegion=<AWS_REGION> \
  --set awsAccountId=<YOUR_12_DIGIT_AWS_ACCOUNT_ID>
```

## 2. we should create lattice network in the name of Exact Gateway object

* the name of the lattice network should be match with the name of the kind Gateway in kubernetes
```bash
aws vpc-lattice create-service-network --name lattice-gateway

aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier lattice-gateway \
  --vpc-identifier vpc-02ece635f513b8fa4 \
  --region <YOUR_AWS_REGION>
```

`For creating the Lattice SG -> allow allTCP from the vpc source`

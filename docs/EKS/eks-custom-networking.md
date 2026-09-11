# EKS Custom Networking Setup: Dedicated Pod CIDR

This document outlines the procedure to configure an Amazon EKS cluster to use a secondary VPC CIDR (`172.10.0.0/16`) exclusively for Kubernetes Pods via the AWS VPC CNI.

## Prerequisites
*   The secondary IPv4 CIDR block `172.10.0.0/16` is already associated with the cluster's VPC.
*   `kubectl` is authenticated and connected to the EKS cluster.
*   Appropriate AWS CLI permissions to view EC2 and EKS configurations.

---

## 1. Create Dedicated Pod Subnets
Create new subnets within the VPC using the `172.10.0.0/16` range. You must create one subnet for each Availability Zone (AZ) utilized by your worker nodes.

*   **Example AZ-a:** `172.10.1.0/24` (Note ID: `subnet-0bb11111111111111`)
*   **Example AZ-b:** `172.10.2.0/24` (Note ID: `subnet-0cc33333333333333`)
*   **Example AZ-c:** `172.10.3.0/24` (Note ID: `subnet-0dd44444444444444`)

**Routing:** Ensure these subnets are associated with a Route Table that routes `0.0.0.0/0` traffic to a NAT Gateway if the Pods require outbound internet access.

## 2. Enable Custom Networking in the VPC CNI
Update the `aws-node` DaemonSet to instruct the CNI to use custom networking and dynamically match the `ENIConfig` to the node's Availability Zone.

Execute the following commands:
```bash
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
```

**Verification:**
```bash
kubectl get daemonset aws-node -n kube-system -o yaml | grep -A 1 -e AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG -e ENI_CONFIG_LABEL_DEF
```

## 3. Retrieve the Cluster Security Group ID
Pods require a security group for internal communication and control plane access. Retrieve the security group attached to your worker nodes.

Run the following AWS CLI command (replace `YOUR_CLUSTER_NAME`):
```bash
aws eks describe-cluster \
  --name YOUR_CLUSTER_NAME \
  --query "cluster.resourcesVpcConfig.clusterSecurityGroupId" \
  --output text
```
*Note the returned ID (e.g., `sg-0aa22222222222222`).*

## 4. Define and Apply ENIConfigs
Create an `ENIConfig` custom resource for every Availability Zone. The `metadata.name` **must exactly match** the AWS Availability Zone name (e.g., `eu-central-1a`).

Create a file named `pod-netconfig.yaml`:

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata: 
  name: eu-central-1a
spec: 
  securityGroups: 
    - sg-0aa22222222222222 # Replace with your Node Security Group ID
  subnet: subnet-0bb11111111111111 # Replace with the 172.10.x.x Subnet ID for this AZ
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata: 
  name: eu-central-1b
spec: 
  securityGroups: 
    - sg-0aa22222222222222
  subnet: subnet-0cc33333333333333
```

Apply the configuration:
```bash
kubectl apply -f pod-netconfig.yaml
```

**Verification:**
```bash
kubectl get eniconfig
```

## 5. Roll Out Worker Nodes
The VPC CNI assigns Pod IPs only when new Elastic Network Interfaces (ENIs) are attached during node initialization. Existing nodes will not automatically update.

*   **For New Clusters:** Deploy your Managed Node Groups or self-managed worker nodes.
*   **For Existing Clusters:** Perform a controlled node replacement. Scale the Managed Node Group to `0` to drain and terminate existing nodes, then scale back to the desired capacity.

## 6. Final Verification
Once the new nodes are fully operational and Pods are scheduled, verify that the Pods are receiving IPs from the new `172.10.0.0/16` CIDR block.

```bash
kubectl get pods -A -o wide
```
Check the `IP` column to confirm the new addressing scheme is active.

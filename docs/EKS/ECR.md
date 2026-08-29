# Create Helm Chart in ECR

```bash
helm package helm-test-chart

aws ecr create-repository \
     --repository-name helm-test-chart \
     --region us-west-2

aws ecr get-login-password \
     --region us-west-2 | helm registry login \
     --username AWS \
     --password-stdin aws_account_id.dkr.ecr.region.amazonaws.com

helm push helm-test-chart-0.1.0.tgz oci://aws_account_id.dkr.ecr.region.amazonaws.com/
```

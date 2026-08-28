## Create service with aws-cli
```bash
aws ecs create-service \
  --cluster fluffy-fish-awk9us \
  --service-name my-ecs-service \
  --task-definition vivid-server-jd43cb:2 \
  --desired-count 2 \
  --launch-type FARGATE \
  --deployment-controller type=CODE_DEPLOY \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-07534a195b68e02c4,subnet-04443c45f3a96d8a2],securityGroups=[sg-02e3354d220e51c50],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:851725449673:targetgroup/green-tg/9d06c296890816e7,containerName=web-container,containerPort=8080"

```

* to update the ECS service:
```bash
aws ecs update-service \
  --cluster fluffy-fish-awk9us \
  --service my-ecs-service \
  --desired-count 2 \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-07534a195b68e02c4,subnet-04443c45f3a96d8a2],securityGroups=[sg-086d1cc5286dd6c7a],assignPublicIp=DISABLED}"
```
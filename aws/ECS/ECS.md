## IAM policies
Nodes
* `AmazonEC2ContainerServiceforEC2Role`
* `AmazonSSMManagedInstanceCore`

## Health Check
```bash
CMD-SHELL, curl -f http://localhost/ || exit 1
```

## ECS exec command
* Task Role

```json
### policy
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssmmessages:CreateControlChannel",
                "ssmmessages:CreateDataChannel",
                "ssmmessages:OpenControlChannel",
                "ssmmessages:OpenDataChannel"
            ],
            "Resource": "*"
        }
    ]
}

### STS
{
    "Version": "2008-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

And for your EC2/IAM user role the below permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ecs:DescribeTasks",
            "Resource": "arn:aws:ecs:<region>:<accountID>:task/<clusterName>/*"
        },
        {
            "Effect": "Allow",
            "Action": "ecs:ExecuteCommand",
            "Resource": [
                "arn:aws:ecs:<region>:<accountID>:task/<clusterName>/*",
                "arn:aws:ecs:<region>:<accountID>:cluster/<clusterName>"
            ],
            "Condition": {
                "StringEquals": {
                    "ecs:container-name": "<containerName>"
                }
            }
        }
    ]
}

### STS
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

add this to the ecs task in the `containerDefinitions`:
```json
{
    "family": "<name>",
    "containerDefinitions": [
        {
            "name": "alpine",
            "image": "<accountID>.dkr.ecr.<region>.amazonaws.com/<imageName>:latest",
            "cpu": 0,
            "portMappings": [
                {
                    "name": "80-tcp",
                    "containerPort": 80,
                    "hostPort": 80,
                    "protocol": "tcp",
                    "appProtocol": "http"
                }
            ],
            "essential": true,
            "environment": [],
            "mountPoints": [],
            "volumesFrom": [],
            "linuxParameters": {
                "initProcessEnabled": true <HERE>
            },
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-create-group": "true",
                    "awslogs-group": "/ecs/<clusterName>",
                    "awslogs-region": "<region>",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ],
    "taskRoleArn": "arn:aws:iam::<accountID>:role/ECSTaskRole",
    "executionRoleArn": "arn:aws:iam::<accountID>:role/ECSTaskExecutionRole",
    "networkMode": "awsvpc",
    "requiresCompatibilities": [
        "FARGATE"
    ],
    "cpu": "1024",
    "memory": "3072",
    "runtimePlatform": {
        "cpuArchitecture": "X86_64",
        "operatingSystemFamily": "LINUX"
    }
}
```

update the ecs service and exec:
```bash
aws ecs update-service --cluster fargate-debug --enable-execute-command --task-definition fargate-debug --service alpine --desired-count 1
aws ecs execute-command --cluster <clusterName> --task "arn:aws:ecs:<region>:<accountID>:task/<cluster>/<taskID>" --container alpine --interactive --command "/bin/sh"
```


## Refrences
* https://aws.amazon.com/blogs/containers/new-using-amazon-ecs-exec-access-your-containers-fargate-ec2/

* https://alexanderhose.com/how-to-execute-commands-to-manage-your-containers-in-aws-ecs/##setup-of-iam-roles-%F0%9F%91%A5
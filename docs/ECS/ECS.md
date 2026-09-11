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


## Lattice
1. create service network
2. associate vpcs to that network
3. for Security Groups we allow listener lattice target group port from lattice prefix list
4. then create lattice service with security group inbound from lattice prefix list for cluster/service
5. enable the dns names for the domain name needed
6. we can call services with dns names


### Don't make the ECS task role None -> we get failure at EC2 endpoint metadata call

## AppConfig Integration

To integrate AWS AppConfig with ECS, deploy the AWS AppConfig Agent as a **sidecar container** within your task definition. Your main application container can then request configuration data directly from the agent via a local HTTP call (`localhost:2772`). The agent handles polling AppConfig and caching the data automatically.

### 1. Update Task Role IAM permissions
Add the following permissions to your ECS **Task Role** so the agent can fetch the configurations:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "appconfig:StartConfigurationSession",
                "appconfig:GetLatestConfiguration"
            ],
            "Resource": "*"
        }
    ]
}
```

### 2. Add the Sidecar to Task Definition
Add the AppConfig Agent to the `containerDefinitions` array in your task definition using the official public ECR image:

```json
{
    "name": "appconfig-agent",
    "image": "public.ecr.aws/aws-appconfig/aws-appconfig-agent:2.x",
    "essential": true,
    "portMappings": [
        {
            "containerPort": 2772,
            "protocol": "tcp"
        }
    ],
    "environment": [
        {
            "name": "SERVICE_REGION",
            "value": "<region>" 
        },
        {
            "name": "PREFETCH_LIST",
            "value": "/applications/<application_name>/environments/<environment_name>/configurations/<configuration_name>"
        }
    ]
}
```

### 3. Fetching the Configuration in your App
Because ECS containers in the same task share the `awsvpc` network namespace, your application can simply fetch the configuration by making an HTTP GET request to the local agent:

```bash
curl "http://localhost:2772/applications/<application_name>/environments/<environment_name>/configurations/<configuration_name>"
```

## Connect EFS in another vpc within ECS
1. create route53 private hosted zone with the name of the efs domain name
2. define A record with root `@` with the EFS ips
3. attach route53 to the ECS cluster VPC
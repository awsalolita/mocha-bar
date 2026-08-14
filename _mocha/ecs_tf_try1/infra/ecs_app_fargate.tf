module "ecs_service" {
  source = "terraform-aws-modules/ecs/aws//modules/service"

  force_new_deployment = true
  force_delete         = true

  name        = "${var.project_name}-myapp"
  cluster_arn = module.ecs.cluster_arn

  deployment_controller = {
    type = "ECS" # or CODE_DEPLOY
  }

  capacity_provider_strategy = {
    FARGATE = {
      capacity_provider = "FARGATE"
      weight            = 20
      base              = 1
    }
    FARGATE_SPOT = {
      capacity_provider = "FARGATE_SPOT"
      weight            = 80
    }
  }

  enable_execute_command   = true
  requires_compatibilities = ["FARGATE"]

  deployment_maximum_percent         = 150
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker = {
    enable   = true
    rollback = true
  }

  # Disable creation of the task definition; `task_definition_arn` should be provided
  create_task_definition = true
  # task_definition_arn = "arn:aws:iam::538573288964:role/game-ecs-task-role"

  # Disable creation of the task execution IAM role; `task_exec_iam_role_arn` should be provided
  create_task_exec_iam_role = false
  task_exec_iam_role_arn = "arn:aws:iam::538573288964:role/game-task-exec-role"

  # Disable creation of the task execution IAM role policy
  create_task_exec_policy = false

  # Disable creation of the tasks IAM role; `tasks_iam_role_arn` should be provided
  create_tasks_iam_role = false
  tasks_iam_role_arn = "arn:aws:iam::538573288964:role/game-ecs-task-role"

  # tasks_iam_role_policies = {
  #   CloudWatchLogsFullAccess = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
  # }

  # task_exec_iam_role_policies = {
  #   CloudWatchLogsFullAccess = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
  # }

  # CPU value 	    Memory value
  # 256 (.25 vCPU) 	512 MiB, 1 GB, 2 GB
  # 512 (.5 vCPU) 	1 GB, 2 GB, 3 GB, 4 GB
  # 1024 (1 vCPU) 	2 GB, 3 GB, 4 GB, 5 GB, 6 GB, 7 GB, 8 GB
  # 2048 (2 vCPU) 	Between 4 GB and 16 GB in 1 GB increments
  # 4096 (4 vCPU) 	Between 8 GB and 30 GB in 1 GB increments
  # 8192 (8 vCPU)   Between 16 GB and 60 GB in 4 GB increments
  # 16384 (16vCPU)  Between 32 GB and 120 GB in 8 GB increments

  cpu    = 256
  memory = 512

  # cpuArchitecture
  # Valid Values: X86_64 | ARM64

  runtime_platform = {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = {
    myapp = {
      essential = true
      image     = "538573288964.dkr.ecr.us-east-1.amazonaws.com/plant:v2"

      healthCheck = {
        command = [
          "CMD-SHELL",
          <<-EOF
            curl -f http://localhost:8080/health || exit 1
          EOF
        ]
        interval = 5
        timeout  = 2
        retries  = 1
      }

      # secrets = [{
      #   name      = "MYSQL_DBINFO"
      #   valueFrom = "arn:aws:secretsmanager:ap-northeast-2:<ACCOUNT_ID>:secret:project-rds-r5wn4n"
      # }]

      portMappings = [
        {
          name          = "myapp"
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
        }
      ]


      enable_cloudwatch_logging              = true
      create_cloudwatch_log_group            = true
      cloudwatch_log_group_name              = "/aws/ecs/${local.ecs_cluster_name}/plant_logs"
      cloudwatch_log_group_retention_in_days = 14

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/aws/ecs/${local.ecs_cluster_name}/plant_logs"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }

      readonlyRootFilesystem = false
    }


    # log_router = {
    #   essential = true
    #   image     = "009160052643.dkr.ecr.${var.region}.amazonaws.com/baseflue:latest"

    #   healthCheck = {
    #     command  = ["CMD-SHELL", "exit 0"]
    #     interval = 5
    #     timeout  = 2
    #     retries  = 1
    #   }

    #   environment = [
    #     {
    #       name = "CONFIG",
    #       value = base64encode(<<-EOF
    #         [SERVICE]
    #           Flush           1
    #           Daemon          off
    #           Log_Level       debug
    #           Parsers_File    /parsers.conf

    #         # [FILTER]
    #         #   Name parser
    #         #   Match *
    #         #   Key_Name log
    #         #   Parser custom
    #         #   Reserve_Data On

    #         [OUTPUT]
    #           Name cloudwatch
    #           Match *
    #           region ${var.region}
    #           log_group_name /aws/ecs/${module.ecs.cluster_name}/myapp
    #           log_stream_name $${TASK_ID}
    #           auto_create_group true
    #         EOF
    #       )
    #     },
    #     {
    #       name = "PARSERS",
    #       value = base64encode(<<-EOF
    #           [PARSER]
    #             Name custom
    #             Format regex
    #             Regex ^(?<remote_addr>.*) - - \[(?<time>.*)\] "(?<method>.*) (?<path>.*) (?<protocol>.*)" (?<status_code>.*) (?<latency>.*) "-" "(?<user_agent>.*)" "-"$
    #             Time_Key time
    #             Time_Format %d/%b/%Y:%H:%M:%S %z
    #             Time_Keep On
    #         EOF
    #       )
    #     }
    #   ]

    #   logConfiguration = {
    #     logDriver = "awslogs"
    #     options = {
    #       awslogs-group         = "/aws/ecs/${module.ecs.cluster_name}/myapp-logroute"
    #       awslogs-region        = var.region
    #       awslogs-stream-prefix = "ecs"
    #       awslogs-create-group  = "true"
    #     }
    #   }

    #   firelensConfiguration = {
    #     type = "fluentbit"
    #     options = {
    #       config-file-type  = "file"
    #       config-file-value = "/config.conf"
    #     }
    #   }

    #   create_cloudwatch_log_group = false
    #   readonlyRootFilesystem      = false
    # }
  }

  load_balancer = {
    service = {
      target_group_arn = module.alb.target_groups.myapp.arn
      container_name   = "myapp"
      container_port   = 8080
    }
  }

  subnet_ids = [for subnet in local.ecs_cluster_subnets : aws_subnet.this[subnet.key].id]

  security_group_ingress_rules = {
    alb_ingress = {
      from_port                    = 8080
      to_port                      = 8080
      ip_protocol                  = "tcp"
      description                  = "Service port"
      referenced_security_group_id = module.alb.security_group_id
    }
  }
  security_group_egress_rules = {
    egress_all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
    }
  }

  desired_count            = 2
  autoscaling_max_capacity = 64
  autoscaling_min_capacity = 2
  autoscaling_policies = {
    high = {
      policy_type = "StepScaling"
      step_scaling_policy_configuration = {
        adjustment_type         = "ChangeInCapacity"
        cooldown                = 0
        metric_aggregation_type = "Average"

        step_adjustment = [
          {
            scaling_adjustment          = 2
            metric_interval_upper_bound = 90 - 80
          },
          {
            scaling_adjustment          = 4
            metric_interval_lower_bound = 90 - 80
          }
        ]
      }
    }
    low = {
      policy_type = "StepScaling"
      step_scaling_policy_configuration = {
        adjustment_type         = "ChangeInCapacity"
        cooldown                = 60
        metric_aggregation_type = "Average"

        step_adjustment = [
          {
            scaling_adjustment          = -1
            metric_interval_lower_bound = 50 - 65
          },
          {
            scaling_adjustment          = -2
            metric_interval_upper_bound = 50 - 65
            metric_interval_lower_bound = 25 - 65
          },
          {
            scaling_adjustment          = -4
            metric_interval_upper_bound = 25 - 65
          }
        ]
      }
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_service_high" {
  alarm_name          = "ecs_service_high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  threshold           = 80

  metric_query {
    id          = "e1"
    expression  = "MAX([m1,m2])"
    label       = "MAX(CPUUtilization, MemoryUtilization)"
    return_data = "true"
  }

  metric_query {
    id = "m1"

    metric {
      metric_name = "CPUUtilization"
      namespace   = "AWS/ECS"
      stat        = "Average"
      period      = 60
      dimensions = {
        ClusterName = module.ecs.cluster_name
        ServiceName = module.ecs_service.name
      }
    }
  }

  metric_query {
    id = "m2"

    metric {
      metric_name = "MemoryUtilization"
      namespace   = "AWS/ECS"
      stat        = "Average"
      period      = 60
      dimensions = {
        ClusterName = module.ecs.cluster_name
        ServiceName = module.ecs_service.name
      }
    }
  }

  alarm_actions = [module.ecs_service.autoscaling_policies.high.arn]
}


resource "aws_cloudwatch_metric_alarm" "ecs_service_low" {
  alarm_name          = "ecs_service_low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  threshold           = 65

  metric_query {
    id          = "e1"
    expression  = "MAX([m1,m2])"
    label       = "MAX(CPUUtilization, MemoryUtilization)"
    return_data = "true"
  }

  metric_query {
    id = "m1"

    metric {
      metric_name = "CPUUtilization"
      namespace   = "AWS/ECS"
      stat        = "Average"
      period      = 60
      dimensions = {
        ClusterName = module.ecs.cluster_name
        ServiceName = module.ecs_service.name
      }
    }
  }

  metric_query {
    id = "m2"

    metric {
      metric_name = "MemoryUtilization"
      namespace   = "AWS/ECS"
      stat        = "Average"
      period      = 60
      dimensions = {
        ClusterName = module.ecs.cluster_name
        ServiceName = module.ecs_service.name
      }
    }
  }

  alarm_actions = [module.ecs_service.autoscaling_policies.low.arn]
}

# replace all name - ecs_service

module "ecs_service" {
  source = "terraform-aws-modules/ecs/aws//modules/service"

  force_new_deployment = true
  force_delete         = true

  name        = "${var.project_name}-myapp"
  cluster_arn = module.ecs.cluster_arn

  deployment_controller = {
    type = "ECS" # or CODE_DEPLOY
  }

  enable_execute_command = true

  deployment_maximum_percent         = 150
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker = {
    enable   = true
    rollback = true
  }

  requires_compatibilities = ["EC2"]
  capacity_provider_strategy = {
    EC2 = {
      capacity_provider = module.ecs.capacity_providers["EC2"].name
      weight            = 1
      base              = 1
    }
  }


  # Disable creation of the task execution IAM role; `task_exec_iam_role_arn` should be provided
  create_task_exec_iam_role = false
  task_exec_iam_role_arn = "arn:aws:iam::253862056991:role/game-ecs-task-exec-role"

  # Disable creation of the task execution IAM role policy
  create_task_exec_policy = false

  # Disable creation of the tasks IAM role; `tasks_iam_role_arn` should be provided
  create_tasks_iam_role = false
  tasks_iam_role_arn = "arn:aws:iam::253862056991:role/game-ecs-task-role"

  # tasks_iam_role_policies = {
  #   CloudWatchLogsFullAccess = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
  # }

  # task_exec_iam_role_policies = {
  #   CloudWatchLogsFullAccess = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
  # }

  cpu    = 512
  memory = 1024

  # cpuArchitecture
  # Valid Values: X86_64 | ARM64

  runtime_platform = {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = {
    myapp = {
      essential = true
      image     = "253862056991.dkr.ecr.us-east-1.amazonaws.com/plant:v2"

      health_check = {
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
          protocol      = "tcp"
        }
      ]

      log_configuration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/aws/ecs/${local.ecs_cluster_name}/plant-logs"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
          awslogs-create-group  = "true"
        }
      }

      # log_configuration = {
      #   logDriver = "awsfirelens"
      #   options   = {}
      # }

      # log_configuration = {
      #   logDriver = "fluentd"
      #   options = {
      #     fluentd-address = "unix:///var/run/fluent.sock",
      #     tag             = "app.{{.FullID}}"
      #   }
      # }
      enable_cloudwatch_logging              = true
      create_cloudwatch_log_group            = true
      cloudwatch_log_group_name              = "/aws/ecs/${local.ecs_cluster_name}/plant-logs"
      cloudwatch_log_group_retention_in_days = 14
      readonly_root_filesystem    = false
    }

    # log_router = {
    #   essential = true
    #   image     = "009160052643.dkr.ecr.${var.region}.amazonaws.com/baseflue:latest"

    #   health_check = {
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
    #           log_group_name /aws/ecs/${local.ecs_cluster_name}/myapp
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
    #  ]

    #   log_configuration = {
    #     logDriver = "awslogs"
    #     options = {
    #       awslogs-group         = "/aws/ecs/${local.ecs_cluster_name}/myapp-logroute"
    #       awslogs-region        = var.region
    #       awslogs-stream-prefix = "ecs"
    #       awslogs-create-group  = "true"
    #     }
    #   }

    #   firelens_configuration = {
    #     type = "fluentbit"
    #     options = {
    #       config-file-type  = "file"
    #       config-file-value = "/config.conf"
    #     }
    #   }

    #   create_cloudwatch_log_group = false
    #   readonly_root_filesystem = false
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

  ordered_placement_strategy = [
    {
      field = "attribute:ecs.availability-zone"
      type  = "spread"
    },
    {
      field = "instanceId"
      type  = "spread"
    }
  ]

  desired_count            = 2
  autoscaling_max_capacity = 64
  autoscaling_min_capacity = 2
  autoscaling_policies = {
    high = {
      policy_type = "StepScaling"
      step_scaling_policy_configuration = {
        adjustment_type          = "PercentChangeInCapacity"
        cooldown                 = 0
        min_adjustment_magnitude = 2
        metric_aggregation_type  = "Average"

        step_adjustment = [
          {
            scaling_adjustment          = 50
            metric_interval_upper_bound = 90 - 80
          },
          {
            scaling_adjustment          = 100
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
            scaling_adjustment          = -2
            metric_interval_lower_bound = 50 - 65
          },
          {
            scaling_adjustment          = -4
            metric_interval_upper_bound = 50 - 65
            metric_interval_lower_bound = 25 - 65
          },
          {
            scaling_adjustment          = -6
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

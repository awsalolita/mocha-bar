locals {
  ecs_cluster_name = "${var.project_name}-cluster"
}

resource "aws_ecs_account_setting_default" "containerInsights" {
  name  = "containerInsights"
  value = "enhanced"
}


resource "aws_ecs_account_setting_default" "awsvpcTrunking" {
  name  = "awsvpcTrunking"
  value = "enabled"
}

module "ecs" {
  source = "terraform-aws-modules/ecs/aws"

  cluster_name                = local.ecs_cluster_name
  create_cloudwatch_log_group = false

  cluster_setting = [
    {
      name  = "containerInsights"
      value = "enhanced"
    }
  ]

  # FARGATE (built-in providers — associate + default strategy)
  # cluster_capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  # default_capacity_provider_strategy = {
  #   FARGATE = {
  #     weight = 20
  #     base   = 1
  #   }
  #   FARGATE_SPOT = {
  #     weight = 80
  #   }
  # }

  # EC2
  capacity_providers = {
    EC2 = {
      auto_scaling_group_provider = {
        auto_scaling_group_arn         = module.autoscaling.autoscaling_group_arn
        managed_termination_protection = "ENABLED"

        managed_scaling = {
          instance_warmup_period    = 0
          maximum_scaling_step_size = 32
          minimum_scaling_step_size = 1
          status                    = "ENABLED"
          target_capacity           = 100
        }
      }
    }
  }
}

locals {
  ecs_ami_arch = "x86_64"        # arm64 or x86_64
  ecs_ami_os   = "al2023" # bottlerocket or al2023
}

module "autoscaling" {
  source = "terraform-aws-modules/autoscaling/aws"

  name = "${var.project_name}-node"

  image_id      = data.aws_ami.ecs["${local.ecs_ami_arch}:${local.ecs_ami_os}"].id
  instance_type = "t3.medium"

  update_default_version = true

  security_groups = [module.autoscaling_sg.id]
  user_data       = base64encode(local.ecs_userscript)

  ignore_desired_capacity_changes = true

  create_iam_instance_profile = true
  iam_role_name               = "${var.project_name}-role-node"
  iam_role_policies = {
    AmazonEC2ContainerServiceforEC2Role = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
    AmazonSSMManagedInstanceCore        = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  }

  vpc_zone_identifier = [for subnet in local.ecs_cluster_subnets : aws_subnet.this[subnet.key].id]

  health_check_type = "EC2"
  min_size          = 2
  max_size          = 32
  desired_capacity  = 2

  autoscaling_group_tags = {
    AmazonECSManaged = true
  }

  # use_mixed_instances_policy = true
  # mixed_instances_policy = {
  #   instances_distribution = {
  #     on_demand_base_capacity                  = 0
  #     on_demand_percentage_above_base_capacity = 20
  #     spot_allocation_strategy                 = "price-capacity-optimized"
  #   }
  # }

  protect_from_scale_in = true

  metadata_options = {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  tag_specifications = [
    {
      resource_type = "instance"
      tags = {
        Name    = "${var.project_name}-node"
        Project = var.project_name
      }
    }
  ]
}

locals {
  ecs_ami_filters = {
    "x86_64:al2023" = {
      name         = "al2023-ami-ecs-hvm-*-x86_64"
      architecture = "x86_64"
    }
    "arm64:al2023" = {
      name         = "al2023-ami-ecs-hvm-*-arm64"
      architecture = "arm64"
    }
    "x86_64:bottlerocket" = {
      name         = "bottlerocket-aws-ecs-2-x86_64-v*"
      architecture = "x86_64"
    }
    "arm64:bottlerocket" = {
      name         = "bottlerocket-aws-ecs-2-aarch64-v*"
      architecture = "arm64"
    }
  }

  ecs_userscript = {
    "al2023"       = <<-EOT
      #!/bin/bash
      echo 'ECS_CLUSTER=${local.ecs_cluster_name}' >> /etc/ecs/ecs.config
      echo 'ECS_ENABLE_CONTAINER_METADATA=true' >> /etc/ecs/ecs.config
      echo 'ECS_ENABLE_SPOT_INSTANCE_DRAINING=true' >> /etc/ecs/ecs.config
      echo 'ECS_AVAILABLE_LOGGING_DRIVERS=["json-file","awslogs","fluentd","none"]' >> /etc/ecs/ecs.config
    EOT
    "bottlerocket" = <<-EOT
      [settings.ecs]
      cluster = "${local.ecs_cluster_name}"
      enable-spot-instance-draining = true
      enable-container-metadata = true
      logging-drivers = ["json-file","awslogs","fluentd","none"]
    EOT
  }[local.ecs_ami_os]
}

data "aws_ami" "ecs" {
  for_each = local.ecs_ami_filters

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = [each.value.name]
  }

  filter {
    name   = "architecture"
    values = [each.value.architecture]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

module "autoscaling_sg" {
  source = "terraform-aws-modules/security-group/aws"

  name   = "${var.project_name}-sg-node"
  vpc_id = aws_vpc.this.id

  egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
    }
  }
}

###############################################################################
# Preconfigured IAM roles for the UnicornTech batch pipeline
# Names match the Day 1 test project exactly.
###############################################################################

locals {
  game_roles = {
    game-ec2-role = {
      services = ["ec2.amazonaws.com"]
      managed_policies = [
        "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
        "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
        "arn:aws:iam::aws:policy/AmazonS3FullAccess",
        "arn:aws:iam::aws:policy/AmazonSSMFullAccess",
        "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
        "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role",
      ]
    }

    # Stage 1: API Lambda in Data-Ingestion-VPC -> DynamoDB FeedbackTable
    game-lambda-role = {
      services = ["lambda.amazonaws.com"]
      managed_policies = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
        "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
        "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
      ]
    }

    # Stage 2/3 task role: DataProcessingAPP / DataExtractionAPP
    game-ecs-role = {
      services = ["ecs-tasks.amazonaws.com"]
      managed_policies = [
        "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
        "arn:aws:iam::aws:policy/AmazonS3FullAccess",
        "arn:aws:iam::aws:policy/AmazonSSMFullAccess",
        "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
        "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
      ]
    }

    game-ecs-execution-role = {
      services = ["ecs-tasks.amazonaws.com"]
      managed_policies = [
        "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
        "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
        "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess",
      ]
    }

    game-scheduler-role = {
      services = ["scheduler.amazonaws.com"]
      managed_policies = []
    }

    game-cloudwatch-event-role = {
      services = ["events.amazonaws.com"]
      managed_policies = []
    }

    # CI/CD with review for the ingestion Lambda (CodeDeploy recommended)
    game-codedeploy-role = {
      services = ["codedeploy.amazonaws.com"]
      managed_policies = [
        "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole",
        "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRoleForLambda",
        "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS",
      ]
    }

    game-codepipeline-role = {
      services = ["codepipeline.amazonaws.com"]
      managed_policies = []
    }
  }

  game_role_policy_attachments = {
    for item in flatten([
      for role_name, role in local.game_roles : [
        for policy_arn in role.managed_policies : {
          role       = role_name
          policy_arn = policy_arn
        }
      ]
    ]) : "${item.role}:${item.policy_arn}" => item
  }
}

resource "aws_iam_role" "game" {
  for_each = local.game_roles

  name = each.key

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = each.value.services
        }
        Action = "sts:AssumeRole"
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "game" {
  for_each = local.game_role_policy_attachments

  role       = aws_iam_role.game[each.value.role].name
  policy_arn = each.value.policy_arn
}

resource "aws_iam_instance_profile" "game_ec2_profile" {
  name = "game-ec2-profile"
  role = aws_iam_role.game["game-ec2-role"].name
}

resource "aws_iam_role_policy" "game_ecs_exec" {
  name = "game-ecs-exec"
  role = aws_iam_role.game["game-ecs-role"].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_role_policy" "game_scheduler" {
  name = "game-scheduler-invoke"
  role = aws_iam_role.game["game-scheduler-role"].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "ecs:RunTask",
          "ecs:TagResource",
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "iam:PassRole"
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_role_policy" "game_cloudwatch_event" {
  name = "game-cloudwatch-event-invoke"
  role = aws_iam_role.game["game-cloudwatch-event-role"].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "ecs:RunTask",
          "ecs:TagResource",
          "codepipeline:StartPipelineExecution",
          "ssm:SendCommand",
          "iam:PassRole"
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_role_policy" "game_codepipeline" {
  name = "game-codepipeline-policy"
  role = aws_iam_role.game["game-codepipeline-role"].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:GetBucketVersioning",
          "s3:PutObject"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "codecommit:GetBranch",
          "codecommit:GetCommit",
          "codecommit:UploadArchive",
          "codecommit:GetUploadArchiveStatus",
          "codecommit:CancelUploadArchive"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "codedeploy:CreateDeployment",
          "codedeploy:GetApplication",
          "codedeploy:GetApplicationRevision",
          "codedeploy:GetDeployment",
          "codedeploy:GetDeploymentConfig",
          "codedeploy:GetDeploymentGroup",
          "codedeploy:RegisterApplicationRevision"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "lambda:ListFunctions",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:PublishVersion",
          "lambda:UpdateAlias"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
    ]
  })
}

output "game_role_arns" {
  value = { for name, role in aws_iam_role.game : name => role.arn }
}

output "game_ec2_profile_arn" {
  value = aws_iam_instance_profile.game_ec2_profile.arn
}

output "game_ec2_profile_name" {
  value = aws_iam_instance_profile.game_ec2_profile.name
}

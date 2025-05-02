provider "aws" {
  region = var.aws_region
}

# Terraform configuration
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0.0"
}

# Create a CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 30
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Role for Lambda function
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for Lambda logging
resource "aws_iam_policy" "lambda_logging_policy" {
  name        = "${var.project_name}-lambda-logging-policy"
  description = "Allow Lambda to log to CloudWatch"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "${aws_cloudwatch_log_group.lambda_log_group.arn}:*"
      }
    ]
  })
}

# IAM Policy for Lambda networking (if using VPC)
resource "aws_iam_policy" "lambda_vpc_policy" {
  count       = var.vpc_id != "" ? 1 : 0
  name        = "${var.project_name}-lambda-vpc-policy"
  description = "Allow Lambda to create network interfaces"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Attach policies to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_logs_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_logging_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_attachment" {
  count      = var.vpc_id != "" ? 1 : 0
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_vpc_policy[0].arn
}

# Create a zip file with Lambda code
data "archive_file" "lambda_package" {
  type        = "zip"
  source_file = "${path.module}/lambda_function.py"
  output_path = "${path.module}/lambda_function.zip"
}

# Lambda function
resource "aws_lambda_function" "ai_agent_lambda" {
  function_name = var.lambda_function_name
  description   = "AI Agent API using ChromaDB and LlamaIndex"
  
  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  
  handler     = "lambda_function.lambda_handler"
  runtime     = "python3.9"
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout
  
  role = aws_iam_role.lambda_execution_role.arn
  
  # VPC configuration if needed
  dynamic "vpc_config" {
    for_each = var.vpc_id != "" ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [aws_security_group.lambda_sg.id]
    }
  }
  
  # Environment variables
  environment {
    variables = {
      CHROMA_HOST                  = var.chroma_host
      CHROMA_PORT                  = var.chroma_port
      CHROMA_COLLECTION_NAME       = var.chroma_collection_name
      OPENAI_API_KEY               = var.openai_api_key
      OPENAI_MODEL_NAME            = var.openai_model_name
      OPENAI_EMBEDDING_MODEL_NAME  = var.openai_embedding_model_name
      FUNCTION_API_TOKEN           = var.function_api_token
      VERBOSE                      = var.verbose
    }
  }
  
  # Use Lambda Layers for dependencies
  layers = [var.lambda_layer_arn]
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# API Gateway for Lambda function
resource "aws_apigatewayv2_api" "api_gateway" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = var.cors_allow_origins
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "api_stage" {
  api_id      = aws_apigatewayv2_api.api_gateway.id
  name        = var.environment
  auto_deploy = true
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      path           = "$context.path"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integrationLatency"
    })
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/api_gateway/${aws_apigatewayv2_api.api_gateway.name}"
  retention_in_days = 30
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# API Gateway integration with Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.api_gateway.id
  integration_type = "AWS_PROXY"
  
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.ai_agent_lambda.invoke_arn
  payload_format_version = "2.0"
}

# API Gateway route
resource "aws_apigatewayv2_route" "lambda_route" {
  api_id    = aws_apigatewayv2_api.api_gateway.id
  route_key = "POST /query"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ai_agent_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  
  source_arn = "${aws_apigatewayv2_api.api_gateway.execution_arn}/*/*/query"
}

# Output API Endpoint URL
output "api_endpoint" {
  value       = "${aws_apigatewayv2_stage.api_stage.invoke_url}/query"
  description = "API Gateway endpoint URL"
}

# Output Lambda function name
output "lambda_function_name" {
  value       = aws_lambda_function.ai_agent_lambda.function_name
  description = "Lambda function name"
}

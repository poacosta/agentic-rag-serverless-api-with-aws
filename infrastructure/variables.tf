variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "ai-agent"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "ai-agent-api"
}

variable "lambda_memory_size" {
  description = "Memory allocation for Lambda function in MB"
  type        = number
  default     = 1024
}

variable "lambda_timeout" {
  description = "Timeout for Lambda function in seconds"
  type        = number
  default     = 30
}

variable "openai_api_key" {
  description = "OpenAI API Key (sensitive)"
  type        = string
  sensitive   = true
}

variable "function_api_token" {
  description = "Authentication token for API access (sensitive)"
  type        = string
  sensitive   = true
}

variable "chroma_host" {
  description = "ChromaDB host address"
  type        = string
}

variable "chroma_port" {
  description = "ChromaDB port"
  type        = number
  default     = 8000
}

variable "chroma_collection_name" {
  description = "ChromaDB collection name"
  type        = string
  default     = "knowledge"
}

variable "openai_embedding_model_name" {
  description = "OpenAI embedding model name"
  type        = string
  default     = "text-embedding-3-small"
}

variable "openai_model_name" {
  description = "OpenAI LLM model name"
  type        = string
  default     = "o3-mini"
}

variable "verbose" {
  description = "Enable verbose mode for the agent"
  type        = string
  default     = "false"
}

variable "vpc_id" {
  description = "VPC ID if Lambda needs VPC access (leave empty for no VPC)"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs if Lambda needs VPC access"
  type        = list(string)
  default     = []
}

variable "cors_allow_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "lambda_layer_arn" {
  description = "ARN of Lambda Layer containing dependencies"
  type        = string
}

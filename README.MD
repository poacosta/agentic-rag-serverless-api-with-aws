# Agentic RAG Serverless API (with AWS)

A serverless API implementation demonstrating how to deploy retrieval-augmented generation with basic agent capabilities using ChromaDB and LlamaIndex. This project provides a starting point for building serverless AI interfaces with AWS Lambda and API Gateway.

## IMPORTANT! 🚨

While this approach might work, AWS Lambda's size restrictions prevent deploying functions with large packages (both scripts and dependencies). Therefore, I suggest maintaining the same agent approach but using another provider that offers greater storage capacity. If the serverless option is not viable, we can opt for the traditional method of a server with the necessary environment or a PaaS. The [local](local) folder illustrates how the API would work in a local environment and can serve as a basis for this latter alternative.

![Lambda Limitations](artifacts/lambda-limitations.jpg)

*Image taken from: https://awsfundamentals.com/blog/lambda-limitations*

## Overview

This project demonstrates a practical approach to transforming a simple ChromaDB and LlamaIndex agent into a serverless API endpoint. It illustrates foundational patterns for building AI-powered information retrieval systems through AWS Lambda functions with API Gateway.

This implementation serves as a basic example and starting point, addressing several fundamental concerns:

- **Serverless Architecture**: Using on-demand computation that eliminates the need for dedicated servers
- **Vector Search Integration**: Basic connection to ChromaDB for semantic retrieval
- **Simple Authentication**: Request validation through authorization headers
- **Infrastructure as Code**: Terraform configuration for reproducible deployments
- **Environment Variables**: Direct configuration of credentials and settings

## Architectural Components

![Architecture Diagram](artifacts/architecture_diagram.png)

The implementation follows a straightforward design pattern with these primary components:

1. **API Layer**: API Gateway to handle HTTP requests with basic CORS support
2. **Authentication Layer**: Simple token verification for requests
3. **Application Layer**: Lambda function running LlamaIndex query processing
4. **Vector Store Layer**: ChromaDB connection for semantic search
5. **Configuration Layer**: Environment variables for settings and credentials

This architecture represents a starting point that can be extended with additional components and security measures for production use cases.

## Implementation Notes

This project serves primarily as a demonstration and starting point rather than a production-ready solution. It illustrates:

1. **Basic Agent Implementation**: The ReActAgent implementation shown here is intentionally simple, providing a foundation that can be extended with more sophisticated agent capabilities.

2. **RAG Architecture**: The retrieval-augmented generation pattern implemented is straightforward - documents stored in ChromaDB are retrieved semantically and passed to an LLM.

3. **Extensibility**: The code is structured to allow for customization and extension with additional tools, reasoning capabilities, or data sources.

For production use cases, you would likely want to implement additional features such as:

- Multiple agent tools beyond the basic query engine
- Enhanced reasoning capabilities
- Memory and context persistence
- Streaming responses
- Structured outputs
- Chain-of-thought prompting techniques
- Fine-tuned models for your specific domain

## Prerequisites

- AWS Account with appropriate IAM permissions
- Terraform ≥ 1.0.0 installed locally
- AWS CLI configured with credentials
- Accessible ChromaDB instance
- OpenAI API key or compatible LLM API credentials

## Deployment Workflow

### 1. Dependencies Layer Setup

The Lambda function requires specific Python packages that exceed the deployment package size limit. Creating a Lambda Layer addresses this constraint:

```bash
# Create a directory structure for dependencies
mkdir -p lambda-layer/python

# Install required packages
pip install chromadb llama-index-llms-openai llama-index-embeddings-openai \
    llama-index-vector-stores-chroma llama-index-core boto3 \
    -t lambda-layer/python

# Package the layer
cd lambda-layer
zip -r ../lambda-layer.zip python/
cd ..

# Publish layer to AWS
aws lambda publish-layer-version \
    --layer-name ai-agent-dependencies \
    --description "Dependencies for AI Agent Lambda" \
    --zip-file fileb://lambda-layer.zip \
    --compatible-runtimes python3.9

# Note the returned LayerVersionArn for the terraform configuration
```

### 2. Configuration Setup

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/ai-agent-lambda.git
   cd ai-agent-lambda
   ```

2. Create your terraform variables file:

   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. Configure your deployment parameters in `terraform.tfvars`:

   ```hcl
   # Infrastructure configuration
   aws_region          = "us-east-1"
   environment         = "dev"
   project_name        = "ai-agent"
   
   # Lambda settings
   lambda_function_name = "ai-agent-api"
   lambda_memory_size  = 1024
   lambda_timeout      = 30
   
   # Security credentials (treat as sensitive)
   openai_api_key               = "sk-proj-xxxxxxxx"
   function_api_token           = "your-secure-api-token"
   
   # ChromaDB configuration
   chroma_host                  = "your-chromadb-ip-or-hostname"
   chroma_port                  = 8000
   chroma_collection_name       = "knowledge"
   
   # Model configuration
   openai_model_name            = "o3-mini"
   openai_embedding_model_name  = "text-embedding-3-small"
   verbose                      = "false"
   
   # CORS configuration
   cors_allow_origins  = ["https://your-frontend-domain.com"]
   
   # Lambda Layer ARN from previous step
   lambda_layer_arn    = "arn:aws:lambda:us-east-1:123456789012:layer:ai-agent-dependencies:1"
   ```

## Security Considerations

The implementation includes basic security measures:

1. **Simple Token Authentication**: Requests require an API token
2. **Environment Variables**: Credentials managed through environment variables
3. **Basic IAM Permissions**: Lambda uses restricted permissions
4. **Input Validation**: Simple checks on incoming requests
5. **Logging**: Authentication attempts and errors are tracked

For production deployment, you would likely want to enhance security with additional measures such as:

- API key rotation mechanisms
- AWS Secrets Manager or Parameter Store for sensitive values
- More granular IAM policies
- Rate limiting and request throttling
- WAF integration for API Gateway

### Environment Variables

The system uses the following environment variables for configuration:

| Variable | Description | Required |
|----------|-------------|----------|
| `FUNCTION_API_TOKEN` | Authentication token for API access | Yes |
| `CHROMA_HOST` | ChromaDB server host address | Yes |
| `CHROMA_PORT` | ChromaDB server port | No (default: 8000) |
| `CHROMA_COLLECTION_NAME` | ChromaDB collection name to query | No (default: knowledge) |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `OPENAI_MODEL_NAME` | OpenAI model name | No (default: o3-mini) |
| `OPENAI_EMBEDDING_MODEL_NAME` | OpenAI embedding model name | No (default: text-embedding-3-small) |
| `VERBOSE` | Enable verbose agent output | No (default: false) |

## Deployment Options

### Terraform AWS Deployment

Execute the Terraform workflow to deploy to AWS:

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy infrastructure
terraform apply
```

The Terraform output will provide the API endpoint URL for testing.

## API Usage Guide

### Authentication Protocol

All requests require token authentication via the `Authorization` header:

```
Authorization: Bearer your-secure-api-token
```

The token must match exactly the value configured in the FUNCTION_API_TOKEN environment variable.

### Query Endpoint

**Endpoint**: `POST /query`

**Headers**:

- `Content-Type: application/json`
- `Authorization: Bearer your-secure-api-token`

**Request Body**:

```json
{
  "query": "Your search or question text"
}
```

**Success Response** (200 OK):

```json
{
  "status": "success",
  "result": "The agent's response to your query"
}
```

**Authentication Error** (401 Unauthorized):

```json
{
  "status": "error",
  "message": "Missing authentication token"
}
```

**Authorization Error** (403 Forbidden):

```json
{
  "status": "error",
  "message": "Invalid authentication token"
}
```

### Example: cURL Integration

```bash
curl -X POST \
  https://your-api-endpoint.execute-api.us-east-1.amazonaws.com/dev/query \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-secure-api-token' \
  -d '{"query": "Search the database for people name and descriptions."}'
```

### Example: Python Client

```python
import requests
import json

def query_ai_agent(query_text, api_url, auth_token):
    """Query the AI agent API with authentication.
    
    Args:
        query_text: Text query to process
        api_url: Full API endpoint URL
        auth_token: Authentication token
        
    Returns:
        Parsed JSON response
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    payload = {"query": query_text}
    
    response = requests.post(
        api_url, 
        headers=headers, 
        data=json.dumps(payload)
    )
    
    # Handle HTTP errors
    response.raise_for_status()
    
    return response.json()

# Usage example
try:
    result = query_ai_agent(
        "Search the database for people name and descriptions.",
        "https://your-api-endpoint.execute-api.us-east-1.amazonaws.com/dev/query",
        "your-secure-api-token"
    )
    print(f"Result: {result['result']}")
except requests.exceptions.HTTPError as e:
    print(f"API request failed: {e}")
```

## Operational Considerations

### Monitoring

Basic CloudWatch logs capture:

- Authentication attempts
- Query processing
- Error states

Consider monitoring:

- Authentication failure rates
- Query latency
- Error percentages
- Lambda cold starts

### Performance Factors

Lambda performance can be adjusted through:

1. **Memory Allocation**: Higher memory also increases CPU allocation

   ```hcl
   lambda_memory_size = 1024  # Can be increased if needed
   ```

2. **Timeout Settings**: Adjust based on query complexity

   ```hcl
   lambda_timeout = 30  # May need to be increased for complex queries
   ```

## Limitations and Disclaimer

This implementation is provided as a learning resource and starting point. It has several limitations:

1. **Basic Agent Capabilities**: The ReActAgent implementation is minimal and would need enhancement for complex reasoning.
2. **Limited Error Handling**: The error handling is simple and would need expansion for production use.
3. **Security Considerations**: While basic authentication is implemented, a comprehensive security review would be needed for production.
4. **Scalability Testing**: This implementation hasn't been tested at scale.

This project is meant to demonstrate core concepts rather than provide a complete, production-grade solution. Use it as inspiration and a learning tool rather than deploying it directly to production without further development and security hardening.

## Advanced Configuration

### VPC Integration

For private network communication with ChromaDB:

```hcl
# terraform.tfvars
vpc_id     = "vpc-0123456789abcdef0"
subnet_ids = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
```

### Custom Domain and HTTPS

To use a custom domain with API Gateway:

1. Create an ACM certificate
2. Configure a custom domain in API Gateway
3. Update DNS records to point to the API Gateway endpoint

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

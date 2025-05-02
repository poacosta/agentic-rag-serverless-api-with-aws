"""
Lambda handler for AI agent query API using ChromaDB and LlamaIndex.
Implements token-based authentication for API security.
"""
import json
import logging
import os
from typing import Dict, Any, Optional, Union

import boto3
import chromadb
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.tools import QueryEngineTool
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.agent import ReActAgent

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SSM client for parameter store
ssm = boto3.client('ssm')

# Get configuration from environment variables
CHROMA_HOST = os.environ.get('CHROMA_HOST')
CHROMA_PORT = int(os.environ.get('CHROMA_PORT', 8000))
CHROMA_COLLECTION = os.environ.get('CHROMA_COLLECTION', 'knowledge')
SSM_PARAM_API_KEY = os.environ.get('SSM_PARAM_API_KEY')
SSM_PARAM_AUTH_TOKEN = os.environ.get('SSM_PARAM_AUTH_TOKEN')
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'text-embedding-3-small')
LLM_MODEL = os.environ.get('LLM_MODEL', 'o3-mini')


def get_api_key() -> str:
    """Retrieve API key from Parameter Store."""
    try:
        response = ssm.get_parameter(Name=SSM_PARAM_API_KEY, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to retrieve API key: {e}")
        raise


def get_auth_token() -> str:
    """Retrieve authentication token from Parameter Store."""
    try:
        response = ssm.get_parameter(Name=SSM_PARAM_AUTH_TOKEN, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to retrieve auth token: {e}")
        raise


# Initialize these variables outside the handler to improve cold start performance
api_key = None
auth_token = None
agent = None


def initialize_agent() -> None:
    """Initialize the LLM agent with ChromaDB vector store."""
    global api_key, auth_token, agent
    
    if agent is not None:
        return
    
    # Get API key and auth token from SSM Parameter Store
    api_key = get_api_key()
    auth_token = get_auth_token()
    os.environ["OPENAI_API_KEY"] = api_key
    
    logger.info(f"Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
    try:
        # Initialize ChromaDB client
        client = chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT
        )
        chroma_collection = client.get_collection(CHROMA_COLLECTION_NAME)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        # Initialize embeddings and LLM
        embed_model = OpenAIEmbedding(
            model=OPENAI_EMBEDDING_MODEL_NAME,
            api_key=OPENAI_API_KEY
        )
        
        llm = OpenAI(
            model=OPENAI_MODEL_NAME,
            api_key=OPENAI_API_KEY,
            temperature=0
        )
        
        # Configure global settings
        Settings.embed_model = embed_model
        Settings.llm = llm
        
        # Create index and query engine
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model
        )
        
        query_engine = index.as_query_engine(llm=llm)
        
        # Create query engine tool
        query_engine_tool = QueryEngineTool.from_defaults(
            query_engine=query_engine,
            name="people",
            description="descriptions for various types of people",
            return_direct=False,
        )
        
        # Initialize agent
        agent = ReActAgent.from_tools(
            tools=[query_engine_tool],
            llm=llm,
            verbose=VERBOSE
        )
        
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise


def run_query(query_text: str) -> Dict[str, Any]:
    """Execute a query against the agent.
    
    Args:
        query_text: The query string to process
        
    Returns:
        Dict containing the response and metadata
    """
    try:
        logger.info(f"Processing query: {query_text}")
        response = agent.query(query_text)
        
        # Handle different response types from the agent
        if hasattr(response, 'response'):
            # For newer versions of LlamaIndex that return a response object
            result = response.response
        else:
            # For versions that return a string directly
            result = str(response)
            
        return {
            "result": result,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return {
            "error": str(e),
            "status": "error"
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function.
    
    Args:
        event: The event dict from API Gateway
        context: The Lambda context object
        
    Returns:
        Response dict with status code and body
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Initialize agent if not already done
    try:
        initialize_agent()
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'status': 'error',
                'message': 'Failed to initialize agent'
            })
        }
    
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': ''
        }
    
    # Process POST request
    if event.get('httpMethod') != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'error', 'message': 'Method not allowed'})
        }
        
    # Validate authentication token
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization') or headers.get('authorization')
    
    if not auth_header:
        logger.warning("Missing Authorization header")
        return {
            'statusCode': 401,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'error', 'message': 'Missing authentication token'})
        }
    
    # Extract token (support for both "Bearer token" and "token" formats)
    token_parts = auth_header.split()
    received_token = token_parts[-1] if len(token_parts) > 1 else token_parts[0]
    
    if received_token != FUNCTION_API_TOKEN:
        logger.warning("Invalid authentication token")
        return {
            'statusCode': 403,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'error', 'message': 'Invalid authentication token'})
        }
    
    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'error', 'message': 'Invalid JSON in request body'})
        }
    
    # Get query from request body
    query = body.get('query')
    if not query:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'error', 'message': 'Missing query parameter'})
        }
    
    # Run the query
    try:
        result = run_query(query)
        status_code = 200 if result.get('status') == 'success' else 500
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'error',
                'message': 'Internal server error'
            })
        }

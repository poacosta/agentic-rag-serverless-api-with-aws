import chromadb
import os
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.tools import QueryEngineTool
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.agent import ReActAgent
from flask import Flask, request, jsonify
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("FUNCTION_API_TOKEN")
if not API_TOKEN:
    raise ValueError("FUNCTION_API_TOKEN environment variable is not set")

app = Flask(__name__)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')

        if auth_header:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Unauthorized: Missing token'}), 401

        if token != API_TOKEN:
            return jsonify({'error': 'Unauthorized: Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated


client = chromadb.HttpClient(
    host=os.getenv("CHROMA_HOST", "localhost"),
    port=int(os.getenv("CHROMA_PORT", 8000))
)
chroma_collection = client.get_collection(os.getenv("CHROMA_COLLECTION_NAME"))
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

embed_model = OpenAIEmbedding(
    model=os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-small"),
    api_key=os.getenv("OPENAI_API_KEY")
)

llm = OpenAI(
    model=os.getenv("OPENAI_MODEL_NAME", "o3-mini"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)

Settings.embed_model = embed_model
Settings.llm = llm

index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    embed_model=embed_model
)

query_engine = index.as_query_engine(llm=llm)

query_engine_tool = QueryEngineTool.from_defaults(
    query_engine=query_engine,
    name="people",
    description="descriptions for various types of people",
    return_direct=False,
)

agent = ReActAgent.from_tools(
    tools=[query_engine_tool],
    llm=llm,
    verbose=os.getenv("VERBOSE", "false").lower() == "true",
)


def run_query(query_text):
    response = agent.query(query_text)
    return response


@app.route('/query', methods=['POST'])
@token_required
def query_endpoint():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing query parameter"}), 400

    query_text = data['query']
    try:
        result = run_query(query_text)
        return jsonify({"result": str(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    # For local development only, use a proper WSGI server for production
    app.run(host='0.0.0.0', port=5000, debug=False)

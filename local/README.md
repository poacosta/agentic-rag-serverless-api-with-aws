# Agentic RAG • Local API using Flask

## API Endpoints

### Query Endpoint

- **URL**: `/query`
- **Method**: `POST`
- **Content Type**: `application/json`
- **Authentication**: Bearer token required in Authorization header
- **Request Body**:
  ```json
  {
    "query": "Your query text here"
  }
  ```
- **Success Response**:
  ```json
  {
    "result": "Response from the agent"
  }
  ```
- **Error Response** (401 Unauthorized):
  ```json
  {
    "error": "Unauthorized: Invalid or missing token"
  }
  ```

### Health Check

- **URL**: `/health`
- **Method**: `GET`
- **Success Response**:
  ```json
  {
    "status": "healthy"
  }
  ```

## Example Usage

Using curl with authentication:

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token" \
  -d '{"query": "Search the database for people name and descriptions."}'
```

Using Python requests:

```python
import requests

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-secret-token"
}
data = {"query": "Search the database for people name and descriptions."}

response = requests.post("http://localhost:5000/query", headers=headers, json=data)
print(response.json())
```

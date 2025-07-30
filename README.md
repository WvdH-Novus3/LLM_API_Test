# Ollama API Server

A FastAPI-based server that provides an Anthropic-style API interface for your local Ollama models.

## Features

- **Streaming responses** - Real-time token streaming like Anthropic's API
- **System prompts** - Customize model behavior with system messages
- **Anthropic-compatible** - Uses similar request/response structure
- **Multiple endpoints** - Chat completions, models list, health check

## Setup

1. **Install dependencies:**
```bash
pip install fastapi uvicorn chatlas requests
```

2. **Make sure Ollama is running** with the phi4:latest model:
```bash
ollama run phi4:latest
```

3. **Start the API server:**
```bash
python api_server.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### POST /v1/chat/completions

Main chat endpoint supporting both streaming and non-streaming responses.

**Request body:**
```json
{
  "messages": [
    {"role": "user", "content": "Your question here"}
  ],
  "system": "Optional system prompt to guide the model",
  "model": "phi4:latest",
  "stream": true
}
```

**Parameters:**
- `messages` (required): Array of message objects with `role` and `content`
- `system` (optional): System prompt to customize model behavior
- `model` (optional): Model name (defaults to "phi4:latest")
- `stream` (optional): Enable streaming responses (default: true)

### GET /v1/models

List available models.

### GET /health

Health check endpoint.

## Usage Examples

### Using requests (Python)

```python
import requests
import json

# Streaming request
payload = {
    "messages": [
        {"role": "user", "content": "What is the capital of France?"}
    ],
    "system": "You are a helpful geography assistant.",
    "stream": True
}

response = requests.post("http://localhost:8000/v1/chat/completions", 
                        json=payload, stream=True)

for line in response.iter_lines():
    if line and line.startswith(b'data: '):
        data = line.decode('utf-8')[6:]  # Remove 'data: '
        if data != '[DONE]':
            chunk = json.loads(data)
            if 'choices' in chunk:
                content = chunk['choices'][0]['delta'].get('content', '')
                print(content, end='', flush=True)
```

### Using curl

```bash
# Streaming request
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "system": "Be friendly and helpful",
    "stream": true
  }'

# Non-streaming request
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "system": "Be friendly and helpful",
    "stream": false
  }'
```

## Testing

Run the test client to verify everything works:

```bash
python test_client.py
```

This will test:
- Models endpoint
- Non-streaming chat completion
- Streaming chat completion

## Integration with Anthropic Client Libraries

You can use this API with Anthropic's client libraries by changing the base URL:

```python
# Example with anthropic Python client (hypothetical)
client = anthropic.Anthropic(
    api_key="dummy-key",  # Not used but required
    base_url="http://localhost:8000/v1"
)
```

## Notes

- The API mimics Anthropic's structure but uses your local Ollama model
- Streaming is simulated by chunking the complete response
- System prompts are supported and work with the phi4 model
- The server runs on port 8000 by default
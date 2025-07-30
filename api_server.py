from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio
from chatlas import ChatOllama

app = FastAPI(title="Ollama API Server", version="1.0.0")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    system: Optional[str] = None
    model: Optional[str] = "phi4:latest"
    stream: bool = True
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]

# Initialize the Ollama chat client
chat_client = None
current_model = None

def get_chat_client(model: str = "phi4:latest"):
    global chat_client, current_model
    if chat_client is None or current_model != model:
        chat_client = ChatOllama(model=model)
        current_model = model
    return chat_client

async def generate_stream_response(messages: List[Message], system: Optional[str] = None, model: str = "phi4:latest"):
    try:
        client = get_chat_client(model)
        
        # Prepare the conversation - ChatOllama doesn't handle system prompts separately
        user_messages = [msg.content for msg in messages if msg.role == "user"]
        user_message = user_messages[-1] if user_messages else ""
        
        # Combine system prompt with user message for streaming too
        if system and user_message:
            user_message = f"{system}\n\nUser: {user_message}\n\nAssistant:"
        elif system:
            user_message = system
        
        # For streaming, we'll simulate the response generation
        # Note: chatlas may not support true streaming, so we'll chunk the response
        raw_response = await asyncio.to_thread(client.chat, user_message)
        
        # Handle different response types for streaming too
        if isinstance(raw_response, str):
            response = raw_response
        elif hasattr(raw_response, 'content'):
            response = raw_response.content
        elif isinstance(raw_response, dict) and 'content' in raw_response:
            response = raw_response['content']
        elif isinstance(raw_response, list) and len(raw_response) > 0:
            response = str(raw_response[0]) if raw_response else "No response"
        else:
            response = str(raw_response)
        
        # Simulate streaming by chunking the response
        chunk_size = 10
        words = response.split()
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            if i + chunk_size < len(words):
                chunk_text += " "
            
            chunk_data = {
                "id": "chatcmpl-ollama",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": chunk_text},
                    "finish_reason": None
                }]
            }
            
            yield f"data: {json.dumps(chunk_data)}\n\n"
            await asyncio.sleep(0.05)  # Small delay to simulate streaming
        
        # Final chunk
        final_chunk = {
            "id": "chatcmpl-ollama",
            "object": "chat.completion.chunk",
            "created": 1234567890,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "server_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    try:
        if request.stream:
            return StreamingResponse(
                generate_stream_response(
                    messages=request.messages,
                    system=request.system,
                    model=request.model
                ),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream"
                }
            )
        else:
            # Non-streaming response
            client = get_chat_client(request.model)
            
            # Prepare conversation - ChatOllama doesn't handle system prompts separately
            # So we need to combine system prompt with user message
            user_messages = [msg.content for msg in request.messages if msg.role == "user"]
            user_message = user_messages[-1] if user_messages else ""
            
            # Combine system prompt with user message
            if request.system and user_message:
                user_message = f"{request.system}\n\nUser: {user_message}\n\nAssistant:"
            elif request.system:
                user_message = request.system
            
            # Debug: Let's see what chatlas returns
            raw_response = await asyncio.to_thread(client.chat, user_message)
            print(f"Debug - Raw response type: {type(raw_response)}")
            print(f"Debug - Raw response: {raw_response}")
            
            # Handle different response types
            if isinstance(raw_response, str):
                response = raw_response
            elif hasattr(raw_response, 'content'):
                response = raw_response.content
            elif isinstance(raw_response, dict) and 'content' in raw_response:
                response = raw_response['content']
            elif isinstance(raw_response, list) and len(raw_response) > 0:
                response = str(raw_response[0]) if raw_response else "No response"
            else:
                response = str(raw_response)
            
            return ChatResponse(
                id="chatcmpl-ollama",
                created=1234567890,
                model=request.model,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response
                    },
                    "finish_reason": "stop"
                }]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "phi4:latest",
                "object": "model",
                "created": 20250101,
                "owned_by": "ollama"
            },
                        {
                "id": "gemma3:latest",
                "object": "model",
                "created": 20250526,
                "owned_by": "ollama"
            },
                        {
                "id": "phi4-mini-reasoning:latest",
                "object": "model",
                "created": 20250730,
                "owned_by": "ollama"
            },
            {
                "id": "smollm:latest",
                "object": "model",
                "created": 20250530,
                "owned_by": "ollama"
            },
            {
                "id": "granite3.3:2b",
                "object": "model",
                "created": 20250730,
                "owned_by": "ollama"
            }
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": "phi4:latest"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
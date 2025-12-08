import os
import sys
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.models.schema import CharacterProfile

# Load environment variables
load_dotenv()

app = FastAPI(title="Character Memory API", description="API for AI Character Memory System")

# Global MemoryManager instance
memory_manager: Optional[MemoryManager] = None

def get_memory_manager() -> MemoryManager:
    global memory_manager
    if memory_manager is None:
        # Ensure directories exist
        os.makedirs("data", exist_ok=True)
        profile_path = "data/profile.json"
        vector_db_path = "data/chroma_db"
        
        llm_service = LLMService()
        # Check for API Key
        env_api_key = os.getenv("OPENROUTER_API_KEY")
        if env_api_key and env_api_key != "sk-or-v1-your-key-here":
            llm_service.set_api_key(env_api_key)
            
        memory_manager = MemoryManager(profile_path, vector_db_path, llm_service)
    return memory_manager

@app.on_event("startup")
async def startup_event():
    get_memory_manager()

# --- Request/Response Models ---

class ChatRequest(BaseModel):
    user_input: str
    user_name: str = "Traveler"
    user_persona: str = "A mysterious traveler."

class ChatResponse(BaseModel):
    response: str
    relevant_memories: List[Dict[str, Any]]

class ReflectRequest(BaseModel):
    user_name: str = "Traveler"

class ReflectResponse(BaseModel):
    result: str

class MemoryQuery(BaseModel):
    query: str
    limit: int = 10

class AddMemoryRequest(BaseModel):
    content: str
    type: str = "observation"
    importance: int = 5

# --- Endpoints ---

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    mm = get_memory_manager()
    try:
        # 1. Retrieve relevant memories
        relevant_memories = mm.retrieve_relevant_memories(request.user_input)
        context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])

        # 2. Construct System Prompt
        system_prompt = mm._construct_system_prompt(user_name=request.user_name, user_persona=request.user_persona)

        # 3. Generate Response
        response = mm.llm_service.generate_response(system_prompt, request.user_input, context_str)

        # 4. Store interaction
        mm.save_interaction(request.user_input, response, user_name=request.user_name)

        return ChatResponse(response=response, relevant_memories=relevant_memories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reflect", response_model=ReflectResponse)
async def reflect(request: ReflectRequest):
    mm = get_memory_manager()
    try:
        # We need the chat history for reflection. 
        # Since the API is stateless, we might need to rely on what's in the vector store or 
        # the client needs to pass history. 
        # However, `reflect_on_interaction` in `MemoryManager` takes `chat_history`.
        # For now, let's assume we want to reflect on recent interactions found in memory or 
        # just trigger a general reflection based on the last few turns if we tracked them.
        # BUT, `MemoryManager.reflect_on_interaction` explicitly asks for `chat_history` list.
        
        # WORKAROUND: Retrieve recent memories to form a "history" or ask client to send it.
        # To keep it simple for Unity, we'll ask Unity to send the session history if possible,
        # OR we can just reflect on the *last interaction* if we had a stateful session.
        
        # Let's update the request model to accept history, or just return a message saying 
        # "Reflection requires history" if not provided.
        # For this implementation, let's add `chat_history` to the request.
        return ReflectResponse(result="Reflection requires chat history. Please use the /reflect_with_history endpoint.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ReflectWithHistoryRequest(BaseModel):
    user_name: str
    chat_history: List[Dict[str, str]] # [{"role": "user", "content": "..."}, ...]

@app.post("/reflect_with_history", response_model=ReflectResponse)
async def reflect_with_history(request: ReflectWithHistoryRequest):
    mm = get_memory_manager()
    try:
        result = mm.reflect_on_interaction(request.chat_history, user_name=request.user_name)
        return ReflectResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile")
async def get_profile():
    mm = get_memory_manager()
    return mm.profile.dict()

@app.post("/memories/search")
async def search_memories(query: MemoryQuery):
    mm = get_memory_manager()
    results = mm.retrieve_relevant_memories(query.query, n_results=query.limit)
    return results

@app.post("/memories")
async def add_memory(mem: AddMemoryRequest):
    mm = get_memory_manager()
    mm.add_memory(mem.content, type=mem.type, importance=mem.importance)
    return {"status": "success", "message": "Memory added"}

@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    mm = get_memory_manager()
    mm.delete_memory(memory_id)
    return {"status": "success", "message": "Memory deleted"}

# --- Sidecar Streaming Endpoint ---

from fastapi.responses import StreamingResponse
import json
import time

class OpenAIChatMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: List[OpenAIChatMessage]
    stream: bool = False

@app.post("/v1/chat/completions")
async def chat_completions(request: OpenAIChatRequest):
    """
    OpenAI-compatible endpoint for streaming chat completions.
    Used by Unity Client (Sidecar).
    """
    mm = get_memory_manager()
    
    # Extract user input from the last message
    user_input = request.messages[-1].content
    
    # 1. Retrieve relevant memories (Context)
    # We can use the last user message as the query
    relevant_memories = mm.retrieve_relevant_memories(user_input)
    context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])
    
    # 2. Construct System Prompt
    # For now, we use default or extract from messages if a system message exists
    system_prompt = "You are a helpful AI assistant in a text adventure game."
    for msg in request.messages:
        if msg.role == "system":
            system_prompt = msg.content
            break
            
    # 3. Generate Stream
    async def event_generator():
        # Call the synchronous generator in a way that works with FastAPI
        # Since LLMService.generate_response_stream is a generator, we iterate it.
        # Note: In a real async app, we might want to run this in a threadpool if it's blocking.
        # But for now, direct iteration.
        
        stream = mm.llm_service.generate_response_stream(system_prompt, user_input, context_str)
        
        for chunk_content in stream:
            # Format as OpenAI SSE
            chunk_data = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": chunk_content},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"
            
        # Send [DONE]
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/candidates")
async def get_candidates():
    """
    Return the list of candidate characters.
    """
    try:
        with open("candidates.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {"candidates": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

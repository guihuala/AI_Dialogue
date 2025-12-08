import os
import sys
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Body, Header, Depends
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

# Global Manager Cache
# Dict[session_id, MemoryManager]
active_managers: Dict[str, MemoryManager] = {}

def get_memory_manager(x_session_id: str = Header("default", alias="X-Session-ID")) -> MemoryManager:
    """
    Dependency that retrieves or creates a MemoryManager for the given session ID.
    The session ID is passed via the X-Session-ID header.
    Default is 'default' for backward compatibility.
    """
    global active_managers
    
    if x_session_id not in active_managers:
        # Define paths for this session
        # Base: Server/data/saves/{session_id}/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Server/
        save_dir = os.path.join(base_dir, "data", "saves", x_session_id)
        
        os.makedirs(save_dir, exist_ok=True)
        
        profile_path = os.path.join(save_dir, "profile.json")
        vector_db_path = os.path.join(save_dir, "chroma_db")
        
        # Initialize Services
        llm_service = LLMService()
        env_api_key = os.getenv("OPENROUTER_API_KEY")
        if env_api_key and env_api_key != "sk-or-v1-your-key-here":
            llm_service.set_api_key(env_api_key)
            
        print(f"Loading MemoryManager for session: {x_session_id} at {save_dir}")
        active_managers[x_session_id] = MemoryManager(profile_path, vector_db_path, llm_service)
        
    return active_managers[x_session_id]

@app.on_event("startup")
async def startup_event():
    # Ensure base data dir exists
    os.makedirs(os.path.join("data", "saves"), exist_ok=True)

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
async def chat(request: ChatRequest, mm: MemoryManager = Depends(get_memory_manager)):
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
async def reflect(request: ReflectRequest, mm: MemoryManager = Depends(get_memory_manager)):
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
async def reflect_with_history(request: ReflectWithHistoryRequest, mm: MemoryManager = Depends(get_memory_manager)):
    try:
        result = mm.reflect_on_interaction(request.chat_history, user_name=request.user_name)
        return ReflectResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile")
async def get_profile(mm: MemoryManager = Depends(get_memory_manager)):
    return mm.profile.dict()

@app.post("/memories/search")
async def search_memories(query: MemoryQuery, mm: MemoryManager = Depends(get_memory_manager)):
    results = mm.retrieve_relevant_memories(query.query, n_results=query.limit)
    return results

@app.post("/memories")
async def add_memory(mem: AddMemoryRequest, mm: MemoryManager = Depends(get_memory_manager)):
    mm.add_memory(mem.content, type=mem.type, importance=mem.importance)
    return {"status": "success", "message": "Memory added"}

@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, mm: MemoryManager = Depends(get_memory_manager)):
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
async def chat_completions(request: OpenAIChatRequest, mm: MemoryManager = Depends(get_memory_manager)):
    """
    OpenAI-compatible endpoint for streaming chat completions.
    Used by Unity Client (Sidecar).
    """
    
    # Extract user input from the last message
    user_input = request.messages[-1].content
    
    # 1. Retrieve relevant memories (Context)
    # We can use the last user message as the query
    relevant_memories = mm.retrieve_relevant_memories(user_input)
    context_str = "\n".join([f"- {m['content']}" for m in relevant_memories])
    
    # 2. Construct System Prompt
    # Load static prompts from Server/data/prompts
    try:
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'prompts')
        with open(os.path.join(base_path, 'Prompt_CoreRules.txt'), 'r', encoding='utf-8') as f:
            rules = f.read()
        with open(os.path.join(base_path, 'Prompt_World.txt'), 'r', encoding='utf-8') as f:
            world = f.read()
        with open(os.path.join(base_path, 'Prompt_Characters.txt'), 'r', encoding='utf-8') as f:
            chars = f.read()
        
        static_prompt = f"{rules}\n\n{world}\n\n{chars}"
    except Exception as e:
        print(f"Error loading prompts: {e}")
        static_prompt = ""

    # The client now sends only the dynamic context (Game State) as the system message
    client_system_msg = ""
    for msg in request.messages:
        if msg.role == "system":
            client_system_msg = msg.content
            break
            
    # Combine static and dynamic prompts
    system_prompt = f"{static_prompt}\n\n{client_system_msg}"
    
    print("="*50)
    print("SYSTEM PROMPT SENT TO AI:")
    print(system_prompt)
    print("="*50)

            
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
        # candidates.json is now in Server/data/
        json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'candidates.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

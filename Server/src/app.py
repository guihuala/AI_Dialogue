import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# --- 1. 路径设置 (保留原逻辑，确保能找到 src) ---
# Add project root to sys.path to allow 'src' imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
# 也可以导入预设角色
from src.core.presets import DEMO_CHARACTER 

# --- 2. 初始化环境与服务 ---
load_dotenv() # 加载 .env 文件中的 API KEY

app = FastAPI()

# 初始化核心服务 (这是全局唯一的，服务器运行期间一直存在)
print("正在初始化记忆系统...")

# 确保数据目录存在
os.makedirs("data", exist_ok=True)
profile_path = "data/profile.json"
vector_db_path = "data/chroma_db"

# 初始化 LLM 和 记忆管理器
llm_service = LLMService() 

# 检查 API Key (保留原逻辑的健壮性)
env_api_key = os.getenv("OPENROUTER_API_KEY")
if env_api_key:
    llm_service.set_api_key(env_api_key)
    print("✅ API Key loaded from environment.")
else:
    print("⚠️ Warning: No API Key found in environment variables.")

mm = MemoryManager(profile_path, vector_db_path, llm_service)

# 如果想每次启动都重置为特定角色，在这里赋值
mm.profile = DEMO_CHARACTER
mm.save_profile()

print(f"DEBUG: 数据存储路径是 -> {os.path.abspath('data')}")

print(f"系统就绪。当前角色: {mm.profile.name}")

# --- 3. 定义数据格式 (供 Unity 发送用) ---
class ChatRequest(BaseModel):
    user_input: str
    user_name: str = "Traveler"

class ReflectRequest(BaseModel):
    user_name: str = "Traveler"

# --- 4. API 接口 ---

@app.get("/")
def health_check():
    """测试服务器是否活着的接口"""
    return {"status": "online", "character": mm.profile.name}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    """
    Unity 对话接口
    """
    print(f"收到消息: {req.user_input} (来自: {req.user_name})")
    
    try:
        # 核心逻辑：检索记忆 -> 生成回复
        response, relevant_memories = mm.chat(req.user_input)
        
        # 保存这一轮的交互到向量数据库
        mm.save_interaction(req.user_input, response, req.user_name)
        
        # 返回给 Unity 的数据
        return {
            "response": response,
            "character_name": mm.profile.name,
            "mood": mm.profile.personality.mood,
            "hp": mm.profile.health.hp,
            "credits": mm.profile.wealth.currency
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reflect")
def reflect_endpoint(req: ReflectRequest):
    """
    触发反思接口 (Unity 点击'休息'或'结算'按钮时调用)
    """
    print("正在进行记忆反思与整合...")
    try:
        # 注意：这里我们简化了逻辑，不传入具体的 history list，
        # 而是依赖 MemoryManager 内部状态或假设最近的交互已在 Short-term memory 中。
        # 在完整版中，你可能需要维护一个 session history。
        result = mm.reflect_on_interaction([], user_name=req.user_name)
        print(f"反思结果: {result}")
        return {
            "success": True, 
            "message": result,
            "updates": "Profile updated successfully"
        }
    except Exception as e:
        print(f"Reflect Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # 启动服务器，IP '0.0.0.0' 允许局域网访问 (手机测试时有用)
    uvicorn.run(app, host="0.0.0.0", port=8000)
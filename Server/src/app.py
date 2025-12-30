import os
import sys
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.core.presets import CHARACTER_REGISTRY 

load_dotenv()

app = FastAPI()

# --- 全局状态 ---
# 这一步很关键：我们需要同时把所有角色加载到内存里，而不是随用随取
managers = {}

def load_character(char_id: str):
    """加载单个角色到内存"""
    if char_id in managers:
        return managers[char_id]
    
    if char_id not in CHARACTER_REGISTRY:
        return None
        
    base_dir = f"data/{char_id}"
    os.makedirs(base_dir, exist_ok=True)
    
    # 不同的角色用不同的文件夹，互不干扰
    mm = MemoryManager(
        profile_path=f"{base_dir}/profile.json", 
        vector_db_path=f"{base_dir}/chroma_db", 
        llm_service=LLMService()
    )
    
    # 初始化预设
    if not os.path.exists(f"{base_dir}/profile.json"):
        print(f"Initializing {char_id}...")
        mm.profile = CHARACTER_REGISTRY[char_id]
        mm.save_profile()
        
    managers[char_id] = mm
    return mm

# 启动时预加载所有注册的角色（诸葛亮 和 老维克）
print("正在初始化群聊场景...")
for char_id in CHARACTER_REGISTRY.keys():
    load_character(char_id)
print(f"场景加载完毕。在场角色: {list(managers.keys())}")


# --- 数据模型 ---
class GroupChatRequest(BaseModel):
    user_input: str
    target_char_id: str  # 你当前看着谁说话
    user_name: str = "Traveler"

# --- API ---

@app.post("/group_chat")
def group_chat_endpoint(req: GroupChatRequest):
    """
    群聊接口：
    1. 用户说话 -> 所有人都能听到 (写入记忆)
    2. 目标角色 -> 进行思考并回复
    3. 目标角色的回复 -> 其他人也能听到 (写入记忆)
    """
    
    # 1. 检查目标是否存在
    if req.target_char_id not in managers:
        raise HTTPException(status_code=404, detail="Character not found")
    
    target_mm = managers[req.target_char_id]
    other_mms = [mm for id, mm in managers.items() if id != req.target_char_id]

    print(f"[{req.user_name}] 对 [{target_mm.profile.name}] 说: {req.user_input}")

    # --- 阶段 A: 处理用户输入 ---
    
    # 2. 目标角色：正常 Chat (检索 + 生成)
    response_text, _ = target_mm.chat(req.user_input)
    # 保存目标角色自己的交互记忆
    target_mm.save_interaction(req.user_input, response_text, req.user_name)

    # 3. 旁听角色：听到用户说话 (只存不回)
    for mm in other_mms:
        mm.observe_interaction(req.user_name, req.user_input)

    # --- 阶段 B: 处理 AI 回复 ---
    
    # 4. 旁听角色：听到目标角色回复 (只存不回)
    # 这让老维克能知道诸葛亮刚才回答了什么
    for mm in other_mms:
        mm.observe_interaction(target_mm.profile.name, response_text)

    return {
        "response": response_text,
        "speaker": target_mm.profile.name,
        "mood": target_mm.profile.personality.mood,
        "context_sync": f"Synced with {len(other_mms)} other characters."
    }

print("--- Registered Routes ---")
for route in app.routes:
    print(f"Path: {route.path} | Methods: {route.methods}")
print("-------------------------")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
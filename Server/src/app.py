import os
import sys
import re
import random
import shutil # 新增：用于删除文件夹
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
# 导入 PLAYER_PROFILE
from src.core.presets import CHARACTER_REGISTRY, PLAYER_PROFILE 
from src.models.schema import PlayerStats 

load_dotenv()

app = FastAPI()

# --- 全局状态 ---
managers = {}
player_state = PlayerStats() 

# --- 核心辅助函数 ---

def load_character(char_id: str):
    if char_id in managers:
        return managers[char_id]
    
    if char_id not in CHARACTER_REGISTRY:
        return None
        
    base_dir = f"data/{char_id}"
    os.makedirs(base_dir, exist_ok=True)
    
    mm = MemoryManager(
        profile_path=f"{base_dir}/profile.json", 
        vector_db_path=f"{base_dir}/chroma_db", 
        llm_service=LLMService()
    )
    
    # 强制更新人设 (保留记忆)
    if char_id in CHARACTER_REGISTRY:
        preset = CHARACTER_REGISTRY[char_id]
        mm.profile.name = preset.name
        mm.profile.context = preset.context
        mm.profile.personality = preset.personality
        mm.save_profile()
        
    managers[char_id] = mm
    return mm

def apply_stat_changes(response_text: str):
    global player_state
    
    san_matches = re.findall(r'\[SAN([+-]\d+)\]', response_text)
    for val in san_matches:
        player_state.san = max(0, min(100, player_state.san + int(val)))

    money_matches = re.findall(r'\[MONEY([+-]\d+)\]', response_text)
    for val in money_matches:
        player_state.money += float(val)

    gpa_matches = re.findall(r'\[GPA([+-]?\d*\.?\d+)\]', response_text)
    for val in gpa_matches:
        player_state.gpa = max(0.0, min(4.0, player_state.gpa + float(val)))

# --- API 接口 ---

class GroupChatRequest(BaseModel):
    user_input: str
    target_char_id: str 
    user_name: str = "Player"

class NpcChatRequest(BaseModel):
    active_char_ids: List[str]

@app.get("/")
def health_check():
    return {"status": "online", "characters": list(managers.keys())}

@app.get("/player_status")
def get_player_status():
    return player_state

# --- 新增：重置游戏数据接口 ---
@app.post("/reset_game")
def reset_game():
    """
    删除所有本地存档数据，重置玩家状态。
    Unity 端在点击“新游戏”时调用此接口。
    """
    global managers, player_state
    
    print("⚠️ 收到重置请求，正在清理数据...")
    
    # 1. 清空内存对象
    managers.clear()
    player_state = PlayerStats() # 重置为初始值 (1000, 80, 3.5)
    
    # 2. 删除硬盘数据
    data_dir = "data"
    if os.path.exists(data_dir):
        try:
            # 递归删除 data 文件夹
            shutil.rmtree(data_dir)
            # 重新创建空文件夹
            os.makedirs(data_dir, exist_ok=True)
            print("✅ 数据清理完毕")
            return {"status": "success", "message": "Game data has been reset."}
        except Exception as e:
            print(f"❌ 数据清理失败: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete data: {e}")
    
    return {"status": "success", "message": "No data found, reset complete."}

@app.post("/group_chat")
def group_chat_endpoint(req: GroupChatRequest):
    if req.target_char_id not in managers:
        if not load_character(req.target_char_id):
            raise HTTPException(status_code=404, detail="Character not found")
    
    target_mm = managers[req.target_char_id]
    
    stats_str = f"Money: ${player_state.money}, SAN: {player_state.san}/100, GPA: {player_state.gpa:.2f}"
    
    # 传入 PLAYER_PROFILE
    response_text, _ = target_mm.chat(
        req.user_input, 
        player_stats_str=stats_str,
        player_persona_str=PLAYER_PROFILE 
    )
    
    apply_stat_changes(response_text)
    
    target_mm.save_interaction(req.user_input, response_text, req.user_name)
    
    for char_id, mm in managers.items():
        if char_id != req.target_char_id:
            mm.observe_interaction(req.user_name, req.user_input) 
            mm.observe_interaction(target_mm.profile.name, response_text) 

    return {
        "response": response_text,
        "speaker": target_mm.profile.name,
        "mood": target_mm.profile.personality.mood,
        "player_stats": player_state.dict()
    }

@app.post("/npc_chat")
def npc_chat_endpoint(req: NpcChatRequest):
    available_ids = [cid for cid in req.active_char_ids if cid in CHARACTER_REGISTRY]
    if len(available_ids) < 2:
        return {
            "response": "(Silence...)",
            "speaker": "System",
            "mood": "Neutral",
            "player_stats": player_state.dict()
        }

    for cid in available_ids:
        load_character(cid)

    speaker_id, listener_id = random.sample(available_ids, 2)
    speaker_mm = managers[speaker_id]
    listener_mm = managers[listener_id]

    print(f"👁️ [观察模式] {speaker_id} -> {listener_id}")

    stats_str = f"Money: ${player_state.money}, SAN: {player_state.san}/100, GPA: {player_state.gpa:.2f}"
    
    prompt_override = (
        f"(Turning to {listener_mm.profile.name}) "
        f"Start a conversation about dorm life or art. "
        f"Ignore the player ({PLAYER_PROFILE.splitlines()[1]}), they are just watching."
    )

    # 传入 PLAYER_PROFILE
    response_text, _ = speaker_mm.chat(
        prompt_override, 
        player_stats_str=stats_str,
        player_persona_str=PLAYER_PROFILE
    )

    apply_stat_changes(response_text)

    speaker_mm.save_interaction(f"(To {listener_mm.profile.name})", response_text, user_name="System")
    for cid in available_ids:
        if cid != speaker_id:
            managers[cid].observe_interaction(speaker_mm.profile.name, response_text)

    return {
        "response": f"(To {listener_mm.profile.name}): {response_text}",
        "speaker": speaker_mm.profile.name,
        "mood": speaker_mm.profile.personality.mood,
        "player_stats": player_state.dict()
    }

if __name__ == "__main__":
    print("正在预加载所有角色数据...")
    for char_id in CHARACTER_REGISTRY.keys():
        print(f"🔄 Loading/Updating profile for {char_id}...")
        load_character(char_id)
    print("✅ 系统就绪")
    uvicorn.run(app, host="0.0.0.0", port=8000)
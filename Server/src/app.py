import os
import sys
import re
import random
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# --- 1. 路径与环境设置 ---
# 将项目根目录加入路径，确保能找到 src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.core.presets import CHARACTER_REGISTRY 
from src.models.schema import PlayerStats 

load_dotenv()

# --- 2. 初始化 App (全局只做一次!) ---
app = FastAPI()

# --- 3. 全局状态 ---
managers = {}
player_state = PlayerStats() # 玩家状态 (Money, SAN, GPA)

# --- 4. 核心辅助函数 ---

def load_character(char_id: str):
    """加载角色并确保数据存在"""
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
    
    # [开发模式] 强制更新人设 (保留记忆，但更新性格/背景)
    if char_id in CHARACTER_REGISTRY:
        # print(f"🔄 Loading/Updating profile for {char_id}...")
        preset = CHARACTER_REGISTRY[char_id]
        mm.profile.name = preset.name
        mm.profile.context = preset.context
        mm.profile.personality = preset.personality
        mm.save_profile()
        
    managers[char_id] = mm
    return mm

def apply_stat_changes(response_text: str):
    """解析回复中的标签 [SAN-5] 并应用到玩家状态"""
    global player_state
    
    # 解析 SAN
    san_matches = re.findall(r'\[SAN([+-]\d+)\]', response_text)
    for val in san_matches:
        player_state.san = max(0, min(100, player_state.san + int(val)))

    # 解析 Money
    money_matches = re.findall(r'\[MONEY([+-]\d+)\]', response_text)
    for val in money_matches:
        player_state.money += float(val)

    # 解析 GPA
    gpa_matches = re.findall(r'\[GPA([+-]?\d*\.?\d+)\]', response_text)
    for val in gpa_matches:
        player_state.gpa = max(0.0, min(4.0, player_state.gpa + float(val)))

# --- 5. 请求数据模型 ---

class GroupChatRequest(BaseModel):
    user_input: str
    target_char_id: str 
    user_name: str = "Player"

class NpcChatRequest(BaseModel):
    active_char_ids: List[str] # Unity 传过来的在场角色ID列表

# --- 6. API 接口 ---

@app.get("/")
def health_check():
    return {"status": "online", "characters": list(managers.keys())}

@app.get("/player_status")
def get_player_status():
    return player_state

@app.post("/group_chat")
def group_chat_endpoint(req: GroupChatRequest):
    """
    玩家主动说话接口
    """
    if req.target_char_id not in managers:
        # 尝试懒加载
        if not load_character(req.target_char_id):
            raise HTTPException(status_code=404, detail="Character not found")
    
    target_mm = managers[req.target_char_id]
    
    # 准备状态字符串
    stats_str = f"Money: ${player_state.money}, SAN: {player_state.san}/100, GPA: {player_state.gpa:.2f}"
    
    # 生成回复
    response_text, _ = target_mm.chat(req.user_input, player_stats_str=stats_str)
    
    # 应用数值影响
    apply_stat_changes(response_text)
    
    # 保存交互
    target_mm.save_interaction(req.user_input, response_text, req.user_name)
    
    # 广播给其他人
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
    """
    观察模式接口：随机触发两个 NPC 之间的对话
    """
    # 验证与加载
    available_ids = [cid for cid in req.active_char_ids if cid in CHARACTER_REGISTRY]
    if len(available_ids) < 2:
        return {
            "response": "(Silence... not enough people to talk)",
            "speaker": "System",
            "mood": "Neutral",
            "player_stats": player_state.dict()
        }

    for cid in available_ids:
        load_character(cid)

    # 随机选择两人
    speaker_id, listener_id = random.sample(available_ids, 2)
    speaker_mm = managers[speaker_id]
    listener_mm = managers[listener_id]

    print(f"👁️ [观察模式] {speaker_id} -> {listener_id}")

    # 构建 Prompt
    stats_str = f"Money: ${player_state.money}, SAN: {player_state.san}/100, GPA: {player_state.gpa:.2f}"
    prompt_override = (
        f"(Turning to {listener_mm.profile.name}) "
        f"Start a conversation or make a comment about the dorm life, art projects, or recent events. "
        f"Ignore the player for now, they are just watching."
    )

    # 生成回复
    response_text, _ = speaker_mm.chat(prompt_override, player_stats_str=stats_str)

    # 应用数值影响
    apply_stat_changes(response_text)

    # 广播记忆
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

# --- 7. 启动逻辑 ---
if __name__ == "__main__":
    print("正在预加载所有角色数据...")
    for char_id in CHARACTER_REGISTRY.keys():
        print(f"🔄 Loading/Updating profile for {char_id}...")
        load_character(char_id)
    print("✅ 系统就绪")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
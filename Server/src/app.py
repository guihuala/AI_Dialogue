import os
import sys
import re
import random
import shutil
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.core.presets import CHARACTER_REGISTRY, PLAYER_PROFILE 
from src.models.schema import PlayerStats 

load_dotenv()

app = FastAPI()

managers = {}
player_state = PlayerStats() 

# --- 辅助函数 ---

def load_character(char_id: str):
    # 确保传入的是小写，防止 key error
    char_id = char_id.lower() 
    
    if char_id in managers: return managers[char_id]
    if char_id not in CHARACTER_REGISTRY: return None
    
    base_dir = f"data/{char_id}"
    os.makedirs(base_dir, exist_ok=True)
    mm = MemoryManager(f"{base_dir}/profile.json", f"{base_dir}/chroma_db", LLMService())
    
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
    for val in san_matches: player_state.san = max(0, min(100, player_state.san + int(val)))
    money_matches = re.findall(r'\[MONEY([+-]\d+)\]', response_text)
    for val in money_matches: player_state.money += float(val)
    gpa_matches = re.findall(r'\[GPA([+-]?\d*\.?\d+)\]', response_text)
    for val in gpa_matches: player_state.gpa = max(0.0, min(4.0, player_state.gpa + float(val)))

# --- 请求模型 ---

class PerformActionRequest(BaseModel):
    action_content: str
    active_char_ids: List[str]
    user_name: str = "Player"

class SuggestOptionsRequest(BaseModel):
    active_char_ids: List[str]
    user_name: str = "Player"

# --- 接口 ---

@app.post("/suggest_options")
def suggest_options_endpoint(req: SuggestOptionsRequest):
    """
    根据当前情境，为玩家生成 3 个行动选项
    """
    llm = LLMService()
    
    # 获取在场角色的名字
    char_names = []
    for cid in req.active_char_ids:
        # 🟢 修改处：强制转小写
        mm = load_character(cid.lower()) 
        if mm: char_names.append(mm.profile.name)
    
    # 如果没找到任何角色（比如传来的ID全是错的），加一个保底，防止 LLM 瞎编
    names_str = ', '.join(char_names) if char_names else "nobody (empty room)"

    system_prompt = f"""
    You are the Game Master of a visual novel.
    The Player ({req.user_name}) is in a dorm room with {names_str}.
    Player Profile: {PLAYER_PROFILE}
    Current Stats: Money {player_state.money}, SAN {player_state.san}, GPA {player_state.gpa}.
    
    Generate 3 distinct, short action options for the player to advance the plot.
    1. A polite/normal option.
    2. A risky/emotional option (might affect SAN or relationships).
    3. A practical/selfish option (might affect Money or GPA).
    
    Output ONLY the 3 options separated by newlines. No numbering.
    """
    
    raw_res = llm.generate_response(system_prompt, "Generate options now.")
    options = [line.strip().lstrip("123.- ") for line in raw_res.split('\n') if line.strip()]
    
    if len(options) < 3:
        options = ["Say hello.", "Ask for money.", "Study silently."]
        
    return {"options": options[:3]}

@app.post("/perform_action")
def perform_action_endpoint(req: PerformActionRequest):
    """
    玩家执行选择 -> 触发多角色连锁反应
    """
    active_mms = []
    for cid in req.active_char_ids:
        # 🟢 修改处：强制转小写，这能解决 No characters found 问题
        mm = load_character(cid.lower())
        if mm: active_mms.append(mm)
        
    # 如果这里报错，说明 Unity 传过来的 ID 和 presets.py 里定义的完全对不上
    if not active_mms:
        print(f"❌ Error: Received IDs {req.active_char_ids}, but none matched registry keys.")
        raise HTTPException(status_code=404, detail="No characters found")

    dialogue_sequence = []
    
    # 步骤 1: 记录玩家的行动
    for mm in active_mms:
        mm.observe_interaction(req.user_name, req.action_content)
        
    # 步骤 2: 决定发言顺序 (随机 1-3 人)
    speakers = random.sample(active_mms, k=min(len(active_mms), 3))
    
    current_context = f"{req.user_name} said: '{req.action_content}'"
    stats_str = f"Money: ${player_state.money}, SAN: {player_state.san}, GPA: {player_state.gpa}"

    for i, mm in enumerate(speakers):
        prompt = f"""
        [Scene Update]
        {current_context}
        
        You are {mm.profile.name}.
        Respond to the situation based on your personality.
        If someone else already spoke, you can reply to them OR the player.
        Keep it short (1-2 sentences).
        """
        
        # 调用 Chat
        response, _ = mm.chat(prompt, player_stats_str=stats_str, player_persona_str=PLAYER_PROFILE)
        apply_stat_changes(response)
        
        dialogue_sequence.append({
            "speaker": mm.profile.name,
            "content": response,
            "mood": mm.profile.personality.mood
        })
        
        # 更新上下文和记忆
        current_context += f"\n{mm.profile.name} said: '{response}'"
        mm.save_interaction(f"(Context: {current_context})", response, user_name="System")
        
        for other in active_mms:
            if other != mm:
                other.observe_interaction(mm.profile.name, response)

    return {
        "dialogue_sequence": dialogue_sequence,
        "player_stats": player_state.dict()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
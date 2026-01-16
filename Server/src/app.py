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
# 引入新定义的 GameState 和 EventSystem
from src.models.schema import PlayerStats, GameState 
from src.core.event_system import EventSystem

load_dotenv()

app = FastAPI()

# --- 全局状态管理 ---
managers = {}
# 使用 GameState 来统一管理 时间、玩家属性、当前事件
game_state = GameState() 

# --- 辅助函数 ---

def load_character(char_id: str):
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
    """解析回复中的标签并更新 game_state.stats"""
    global game_state
    
    san_matches = re.findall(r'\[SAN([+-]\d+)\]', response_text)
    for val in san_matches: 
        game_state.stats.san = max(0, min(100, game_state.stats.san + int(val)))

    money_matches = re.findall(r'\[MONEY([+-]\d+)\]', response_text)
    for val in money_matches: 
        game_state.stats.money += float(val)

    gpa_matches = re.findall(r'\[GPA([+-]?\d*\.?\d+)\]', response_text)
    for val in gpa_matches: 
        game_state.stats.gpa = max(0.0, min(4.0, game_state.stats.gpa + float(val)))

# --- 请求模型 ---

class PerformActionRequest(BaseModel):
    action_content: str
    active_char_ids: List[str]
    user_name: str = "Player"

class SuggestOptionsRequest(BaseModel):
    active_char_ids: List[str]
    user_name: str = "Player"

# --- 接口 ---

@app.get("/player_status")
def get_player_status():
    return game_state

@app.post("/reset_game")
def reset_game():
    global managers, game_state
    managers.clear()
    game_state = GameState() # 重置回大一 9月
    
    data_dir = "data"
    if os.path.exists(data_dir):
        try:
            shutil.rmtree(data_dir)
            os.makedirs(data_dir, exist_ok=True)
        except Exception:
            pass
    return {"status": "success", "message": "Game reset."}

GAME_MASTER_STYLE = """
你是一个视觉小说游戏的GM（主持人）。
叙事风格：冷静、客观，略带神秘感的旁观者视角。
重点描述艺术学院的氛围、角色之间微妙的张力以及环境细节。
使用第二人称（“你看到...”、“你感觉到...”）。
**重要：所有输出必须使用中文。**
"""

@app.post("/suggest_options")
def suggest_options_endpoint(req: SuggestOptionsRequest):
    if game_state.is_game_over:
        return {"options": ["Game Over. Restart?"]}

    llm = LLMService()
    
    char_names = []
    for cid in req.active_char_ids:
        mm = load_character(cid.lower()) 
        if mm: char_names.append(mm.profile.name)
    
    names_str = ', '.join(char_names) if char_names else "nobody"

    # 构建 Prompt: 加入时间、事件、属性
    time_str = f"Year {game_state.time.year}, Month {game_state.time.month}, Week {game_state.time.week}"
    
    system_prompt = f"""
    You are the Game Master of a visual novel.

    [Narrative Style]
    {GAME_MASTER_STYLE}
    
    [Context]
    Time: {time_str}
    Current Event: {game_state.current_event}
    Location: Dorm Room with {names_str}
    
    [Player Status]
    Money: {game_state.stats.money}, SAN: {game_state.stats.san}, GPA: {game_state.stats.gpa}
    Profile: {PLAYER_PROFILE}
    
    Generate 3 distinct, short action options for the player.
    Options should relate to the Current Event ({game_state.current_event}) if possible.
    **Output Language: Chinese (Simplified)**
    
    Output ONLY the 3 options separated by newlines. No numbering.
    """
    
    raw_res = llm.generate_response(system_prompt, "Generate options now.")
    options = [line.strip().lstrip("123.- ") for line in raw_res.split('\n') if line.strip()]
    
    if len(options) < 3:
        options = ["Chat with roommates.", "Study for GPA.", "Rest for SAN."]
        
    return {"options": options[:3]}

@app.post("/perform_action")
def perform_action_endpoint(req: PerformActionRequest):
    # 0. 游戏结束检查
    if game_state.is_game_over:
        return {
            "dialogue_sequence": [{"speaker": "System", "content": f"Game Over: {game_state.game_over_reason}"}],
            "player_stats": game_state.stats.dict()
        }

    # 1. 加载角色
    active_mms = []
    for cid in req.active_char_ids:
        mm = load_character(cid.lower())
        if mm: active_mms.append(mm)
        
    if not active_mms:
        raise HTTPException(status_code=404, detail="No characters found")

    # 2. 执行演出逻辑 (生成对话)
    dialogue_sequence = []
    
    # 记录玩家行动
    for mm in active_mms:
        mm.observe_interaction(req.user_name, req.action_content)
        
    speakers = random.sample(active_mms, k=min(len(active_mms), 3))
    current_context = f"{req.user_name} said: '{req.action_content}'"
    
    # 准备状态字符串传给 MemoryManager
    stats_str = f"Money: {game_state.stats.money}, SAN: {game_state.stats.san}, GPA: {game_state.stats.gpa}"
    time_str = f"Year {game_state.time.year} Month {game_state.time.month}"

    for i, mm in enumerate(speakers):
        prompt = f"""
        [Scene Update]
        {current_context}
        
        You are {mm.profile.name}.
        Respond naturally. Keep it short.
        """
        
        # 传入时间和事件
        response, _ = mm.chat(
            prompt, 
            player_stats_str=stats_str, 
            player_persona_str=PLAYER_PROFILE,
            current_time_str=time_str,
            current_event_str=game_state.current_event
        )
        apply_stat_changes(response)
        
        dialogue_sequence.append({
            "speaker": mm.profile.name,
            "content": response,
            "mood": mm.profile.personality.mood
        })
        
        current_context += f"\n{mm.profile.name} said: '{response}'"
        mm.save_interaction(f"(Context: {current_context})", response, user_name="System")
        
        for other in active_mms:
            if other != mm:
                other.observe_interaction(mm.profile.name, response)

    # 3. --- 核心循环：推进游戏 ---
    
    # A. 推进时间
    game_state.time.advance()
    
    # B. 检查新事件
    new_event = EventSystem.check_event(game_state.time.month, game_state.time.week)
    game_state.current_event = new_event
    
    # C. 失败判定 (Game Over Check)
    is_over, reason = EventSystem.check_game_over(game_state.stats)
    if is_over:
        game_state.is_game_over = True
        game_state.game_over_reason = reason
        # 在对话序列最后追加一条系统通知
        dialogue_sequence.append({
            "speaker": "System", 
            "content": f"<color=red>GAME OVER: {reason}</color>",
            "mood": "System"
        })

    # D. 返回完整数据
    return {
        "dialogue_sequence": dialogue_sequence,
        "player_stats": game_state.stats.dict(),
        "game_time": game_state.time.dict(),      # 前端可用于更新 UI
        "current_event": game_state.current_event # 前端显示 "当前: 期末考"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
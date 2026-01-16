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
from src.core.event_script import get_event
from src.core.event_system import EventSystem
from src.core.presets import CHARACTER_REGISTRY, PLAYER_PROFILE 
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

# 🟢 修正：Suggest Options
@app.post("/suggest_options")
def suggest_options_endpoint(req: SuggestOptionsRequest):
    if game_state.is_game_over:
        return {"options": ["Game Over. Restart?"]}

    llm = LLMService()
    
    # 获取当前剧本
    current_evt = get_event(game_state.current_event_id)
    
    # 构造 Prompt
    conflicts_str = "\n".join([f"- {c}" for c in current_evt.potential_conflicts])
    time_str = f"Year {game_state.time.year}, Month {game_state.time.month}"
    
    system_prompt = f"""
    You are the Game Master.
    
    [Current Event]: {current_evt.name}
    [Scene]: {current_evt.description}
    [Conflicts]: 
    {conflicts_str}
    
    [Progress]: The player has chatted for {game_state.current_phase_progress} turns in this event.
    
    Generate 3 distinct options for the player.
    
    **CRITICAL RULES**:
    1. If the conversation has gone on for a while (Progress > 3) OR the player seems to have resolved a conflict, YOU MUST provide an option to advance time, e.g., "【结束这一天】" or "【前往下一阶段】".
    2. Otherwise, provide options to interact with roommates or the environment.
    3. Output Language: Chinese.
    4. Output ONLY the 3 options.
    """

    raw_res = llm.generate_response(system_prompt, "Generate options now.")
    options = [line.strip().lstrip("123.- ") for line in raw_res.split('\n') if line.strip()]
    
    # 强制保底：如果聊太久了，强制替换最后一个选项为结束
    if game_state.current_phase_progress > 5:
        if len(options) >= 3:
            options[2] = "【结束这一天，回宿舍休息】"
        else:
            options.append("【结束这一天】")
            
    return {"options": options[:3]}

# 🟢 修正：Perform Action
@app.post("/perform_action")
def perform_action_endpoint(req: PerformActionRequest):
    # 1. 检查是否是推进剧情的特殊指令
    if "结束" in req.action_content or "下一阶段" in req.action_content or "休息" in req.action_content:
        success, msg = EventSystem.advance_event(game_state)
        
        # 返回转场信息，不触发对话
        return {
            "dialogue_sequence": [
                {"speaker": "System", "content": f"(时间流逝...) {msg}", "mood": "System"}
            ],
            "player_stats": game_state.stats.dict(),
            "game_time": game_state.time.dict(),
            "current_event": game_state.display_event_name
        }

    # 2. 正常对话逻辑
    # 增加轮数计数
    game_state.current_phase_progress += 1
    
    # 获取当前事件对象，传给 MemoryManager
    current_evt = get_event(game_state.current_event_id)
    
    active_mms = []
    for cid in req.active_char_ids:
        mm = load_character(cid.lower())
        if mm: active_mms.append(mm)
    
    dialogue_sequence = []
    
    # 记录玩家发言
    for mm in active_mms:
        mm.observe_interaction(req.user_name, req.action_content)
        
    speakers = random.sample(active_mms, k=min(len(active_mms), 3))
    current_context = f"{req.user_name} said: '{req.action_content}'"
    
    stats_str = f"Money: {game_state.stats.money}, SAN: {game_state.stats.san}"
    time_str = f"Y{game_state.time.year} M{game_state.time.month}"

    for i, mm in enumerate(speakers):
        prompt = f"""
        [Scene Update]
        {current_context}
        """
        
        response, _ = mm.chat(
            prompt, 
            player_stats_str=stats_str, 
            player_persona_str=PLAYER_PROFILE,
            current_time_str=time_str,
            current_event_obj=current_evt # 传对象
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

    # 这里删除了 game_state.time.advance()
    # 时间只在上面的 if "结束" 里推进

    # 检查失败
    is_over, reason = EventSystem.check_game_over(game_state.stats)
    if is_over:
        game_state.is_game_over = True
        game_state.game_over_reason = reason
        dialogue_sequence.append({
            "speaker": "System", 
            "content": f"<color=red>GAME OVER: {reason}</color>", 
            "mood": "System"
        })

    return {
        "dialogue_sequence": dialogue_sequence,
        "player_stats": game_state.stats.dict(),
        "game_time": game_state.time.dict(),
        "current_event": game_state.display_event_name
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
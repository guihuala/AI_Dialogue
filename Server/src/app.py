import os
import sys
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# 设置路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService
from src.core.presets import CHARACTER_REGISTRY 
from src.models.schema import PlayerStats # 导入玩家属性定义

load_dotenv()

app = FastAPI()

# --- 全局状态 ---
managers = {}
# 初始化玩家状态：1000元, 80 SAN, 3.5 GPA
player_state = PlayerStats() 

def load_character(char_id: str):
    """加载角色并强制应用 Presets 设置 (开发模式)"""
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
    
    # --- 强制更新逻辑 (解决旧存档污染问题) ---
    # 每次启动时，都用代码里的 Presets 覆盖存档里的“人设”部分
    # 但保留记忆 (Memory)
    print(f"🔄 Force updating profile for {char_id} from presets...")
    preset = CHARACTER_REGISTRY[char_id]
    
    # 覆盖静态属性
    mm.profile.name = preset.name
    mm.profile.context = preset.context
    mm.profile.personality = preset.personality
    # mm.profile.relationships = preset.relationships # 关系如果想保留记忆就不要覆盖
    
    mm.save_profile()
    # -------------------------------------
        
    managers[char_id] = mm
    return mm

# 启动时预加载所有 6 个室友
print("正在初始化艺术学院宿舍场景...")
for char_id in CHARACTER_REGISTRY.keys():
    load_character(char_id)
print(f"场景加载完毕。在场室友: {list(managers.keys())}")


# --- 辅助逻辑：解析数值变更 ---
def apply_stat_changes(response_text: str):
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


# --- 数据模型 ---
class GroupChatRequest(BaseModel):
    user_input: str
    target_char_id: str 
    user_name: str = "Player"

# --- API 接口 ---

@app.post("/group_chat")
def group_chat_endpoint(req: GroupChatRequest):
    # 1. 检查角色
    if req.target_char_id not in managers:
        raise HTTPException(status_code=404, detail="Character not found")
    
    target_mm = managers[req.target_char_id]
    other_mms = [mm for id, mm in managers.items() if id != req.target_char_id]

    print(f"[{req.user_name}] -> [{target_mm.profile.name}]: {req.user_input}")

    # 2. 准备玩家状态字符串 (让 AI 知道你现在有多惨)
    stats_str = f"Money: ${player_state.money}, SAN: {player_state.san}/100, GPA: {player_state.gpa:.2f}"
    
    # 3. 目标角色回复
    response_text, _ = target_mm.chat(req.user_input, player_stats_str=stats_str)
    
    # 4. 应用数值变更 (解析 [SAN-5] 等标签)
    apply_stat_changes(response_text)
    
    # 5. 保存记忆 & 广播给其他人 (旁听机制)
    target_mm.save_interaction(req.user_input, response_text, req.user_name)
    for mm in other_mms:
        mm.observe_interaction(req.user_name, req.user_input)
        mm.observe_interaction(target_mm.profile.name, response_text)

    # 6. 返回数据给 Unity
    return {
        "response": response_text, # 包含标签，Unity 可正则解析高亮
        "speaker": target_mm.profile.name,
        "mood": target_mm.profile.personality.mood,
        "player_stats": {
            "money": player_state.money,
            "san": player_state.san,
            "gpa": player_state.gpa
        }
    }

# 增加一个查询状态的接口
@app.get("/player_status")
def get_player_status():
    return player_state

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
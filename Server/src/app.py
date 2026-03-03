from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import sys

# 把当前文件的上一级目录加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.presets import CANDIDATE_POOL
from src.core.game_engine import GameEngine
from src.models.schema import PlayerStats

# 定义存档目录
SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

app = FastAPI(title="Roommate Survival Game API")

# 初始化 GameEngine 核心引擎
try:
    engine = GameEngine()
except Exception as e:
    print(f"Warning: Failed to initialize GameEngine fully, error: {e}")
    engine = None

# --- 请求体定义 ---
class StartGameRequest(BaseModel):
    # 可选：如果 Unity 想指定初始室友，或者使用一套默认池
    roommates: List[str] = []

class GameTurnRequest(BaseModel):
    choice: str
    active_roommates: List[str]
    current_evt_id: str
    is_transition: bool = False
    chapter: int = 1
    turn: int = 0
    san: int = 100
    money: float = 2000.0
    gpa: float = 4.0
    arg_count: int = 0
    affinity: Dict[str, float] = {}
    wechat_data_dict: Dict[str, List[Any]] = {}

class SaveGameRequest(BaseModel):
    slot_id: str
    game_state: Dict[str, Any]

class SettingsRequest(BaseModel):
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    custom_model: Optional[str] = None

# --- 路由与接口 ---

@app.post("/api/game/start")
def start_game(req: StartGameRequest):
    """
    初始化游戏：分配室友，设置初始状态
    """
    if not engine:
        raise HTTPException(status_code=500, detail="GameEngine not initialized.")
        
    selected_ids = req.roommates
    if not selected_ids:
        # 如果未指定，随便选 3 个
        import random
        all_ids = list(CANDIDATE_POOL.keys())
        selected_ids = random.sample(all_ids, min(3, len(all_ids)))
        
    # 第一回合可以认为是一次 Transition，交给 GameEngine 生成场景和选项
    try:
        init_res = engine.play_main_turn(
            action_text="",
            selected_chars=selected_ids,
            current_evt_id="",
            is_transition=True,
            api_key="",  # 默认使用环境变量里配置好的
            base_url="",
            model="",
            tmp=0.7, top_p=1.0, max_t=800, pres_p=0.3, freq_p=0.5,
            san=100, money=2000, gpa=4.0, arg_count=0, chapter=1, turn=0,
            affinity={sid: 50 for sid in selected_ids},
            wechat_data_dict={}
        )
        return init_res
    except Exception as e:
        print(f"Init Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/game/turn")
def perform_turn(req: GameTurnRequest):
    """
    回合制核心：提交玩家选择及状态，返回下一事件脚本和新选项
    """
    if not engine:
        raise HTTPException(status_code=500, detail="GameEngine not initialized.")
        
    try:
        res = engine.play_main_turn(
            action_text=req.choice,
            selected_chars=req.active_roommates,
            current_evt_id=req.current_evt_id,
            is_transition=req.is_transition,
            api_key="", 
            base_url="",
            model="",
            tmp=0.7, top_p=1.0, max_t=800, pres_p=0.3, freq_p=0.5,
            san=req.san,
            money=req.money,
            gpa=req.gpa,
            arg_count=req.arg_count,
            chapter=req.chapter,
            turn=req.turn,
            affinity=req.affinity,
            wechat_data_dict=req.wechat_data_dict
        )
        return res
    except Exception as e:
        print(f"Turn Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/game/save")
def save_game(req: SaveGameRequest):
    """
    保存游戏状态到本地 JSON 文件
    """
    try:
        file_path = os.path.join(SAVE_DIR, f"save_{req.slot_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(req.game_state, f, ensure_ascii=False, indent=4)
        return {"status": "success", "message": f"Saved to slot {req.slot_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

@app.get("/api/game/load/{slot_id}")
def load_game(slot_id: str):
    """
    从本地 JSON 文件读取游戏状态
    """
    file_path = os.path.join(SAVE_DIR, f"save_{slot_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="存档不存在")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_state = json.load(f)
        return {"status": "success", "game_state": game_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取存档失败: {str(e)}")

@app.post("/api/game/reset")
def reset_game():
    """
    重置当前后端可能缓存的状态
    当前服务端是无状态设计，所以这只是个占位符，如果以后加入了会话隔离 (Session Memory) 则用于清空
    """
    # 如果还需要重置引擎内的会话信息的话
    try:
        if engine and hasattr(engine, 'mm'):
            engine.mm.clear_game_history()
        return {"status": "success", "message": "Backend memory cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/system/settings")
def update_settings(req: SettingsRequest):
    """
    调整后端的 LLM 生成参数 (如温度，使用模型)
    """
    if getattr(engine, 'llm', None):
        if req.temperature is not None:
            engine.llm.temperature = req.temperature
        if req.max_tokens is not None:
            engine.llm.max_tokens = req.max_tokens
    
    return {
        "status": "success", 
        "current_settings": {
            "temperature": getattr(engine.llm, 'temperature', None) if getattr(engine, 'llm', None) else None,
            "max_tokens": getattr(engine.llm, 'max_tokens', None) if getattr(engine, 'llm', None) else None,
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
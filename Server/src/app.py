from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import uuid
import sys  # 🌟 修复点 1：补上缺少的 sys 模块引入！

# 把当前文件的上一级目录加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.presets import CANDIDATE_POOL
from src.core.game_engine import GameEngine
from src.models.schema import PlayerStats
from datetime import datetime

# 🌟 修复点 2：确保在启动服务器前，把 CSV 剧本数据加载进内存（避免一进游戏就通关）
try:
    from src.core.data_loader import load_all_events
    from src.core.event_script import EVENT_DATABASE
    EVENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "events")
    EVENT_DATABASE.update(load_all_events(EVENTS_DIR))
except Exception as e:
    print(f"Warning: Failed to load events data: {e}")

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
    wechat_data_list: List[Dict[str, Any]] = []

# 🌟 修复点 3：清理了冗余的旧版存档结构，保留完美的 3 槽位结构
class SaveGameRequest(BaseModel):
    slot_id: int  # 规定只能是 1, 2, 或 3
    active_roommates: List[str]
    current_evt_id: str
    chapter: int
    turn: int
    san: int
    money: float
    gpa: float
    arg_count: int
    wechat_data_list: List[Dict[str, Any]] = []

class SettingsRequest(BaseModel):
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    custom_model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None

# --- 路由与接口 ---

@app.post("/api/game/start")
def start_game(req: StartGameRequest):
    """初始化游戏：分配室友，设置初始状态"""
    if not engine:
        raise HTTPException(status_code=500, detail="GameEngine not initialized.")
        
    engine.reset() # 强制每次重新开始游戏都重洗抽卡池并归零剧情
    
    selected_ids = req.roommates
    if not selected_ids:
        import random
        all_ids = list(CANDIDATE_POOL.keys())
        selected_ids = random.sample(all_ids, min(3, len(all_ids)))
        
    try:
        init_res = engine.play_main_turn(
            action_text="",
            selected_chars=selected_ids,
            current_evt_id="",
            is_transition=True,
            api_key="",  
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
    """回合制核心：提交玩家选择及状态，返回下一事件脚本和新选项"""
    if not engine:
        raise HTTPException(status_code=500, detail="GameEngine not initialized.")
        
    try:
        wechat_dict = {}
        if req.wechat_data_list:
            for session in req.wechat_data_list:
                chat_name = session.get("chat_name")
                messages = [[m.get("sender", ""), m.get("message", "")] for m in session.get("messages", [])]
                if chat_name:
                    wechat_dict[chat_name] = messages

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
            wechat_data_dict=wechat_dict
        )
        return res
    except Exception as e:
        print(f"Turn Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 💾 存档与读档系统 (支持 3 槽位与 UI 摘要)
# ==========================================

@app.post("/api/game/save")
def save_game(req: SaveGameRequest):
    """保存游戏状态到指定的槽位 (1-3)"""
    if req.slot_id not in [1, 2, 3]:
    raise HTTPException(status_code=400, detail="无效的槽位ID")
        
    file_path = os.path.join(SAVE_DIR, f"slot_{req.slot_id}.json")
    
    save_data = {
        "slot_id": req.slot_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chapter_info": f"第 {req.chapter} 章 - 第 {req.turn} 回合",
        "state": req.dict() 
    }
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        return {"status": "success", "slot_id": req.slot_id, "message": f"槽位 {req.slot_id} 保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存存档失败: {str(e)}")

@app.get("/api/game/saves_info")
def get_saves_info():
    """读取 3 个槽位的摘要信息，供前端选单界面展示"""
    info_list = []
    for i in range(1, 4):
        file_path = os.path.join(SAVE_DIR, f"slot_{i}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    info_list.append({
                        "slot_id": i, 
                        "is_empty": False,
                        "timestamp": data.get("timestamp"), 
                        "chapter_info": data.get("chapter_info")
                    })
            except:
                info_list.append({"slot_id": i, "is_empty": True, "chapter_info": "存档损坏"})
        else:
            info_list.append({"slot_id": i, "is_empty": True, "chapter_info": "空槽位", "timestamp": ""})
            
    return {"status": "success", "slots": info_list}

@app.get("/api/game/load/{slot_id}")
def load_game(slot_id: int):
    """根据槽位编号读取完整游戏状态"""
    if slot_id not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="无效的槽位ID")
        
    file_path = os.path.join(SAVE_DIR, f"slot_{slot_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="该槽位为空")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
        return {"status": "success", "data": save_data["state"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取存档失败: {str(e)}")

@app.post("/api/game/reset")
def reset_game():
    try:
        if engine and hasattr(engine, 'mm'):
            engine.mm.clear_game_history()
        return {"status": "success", "message": "Backend memory cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/system/settings")
def update_settings(req: SettingsRequest):
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

# 1. 扩充 SettingsRequest 模型 (大约在 130 行附近)

# 2. 覆盖原有的 /api/system/settings 接口
@app.post("/api/system/settings")
def update_settings(req: SettingsRequest):
    """更新大模型底层配置"""
    if getattr(engine, 'llm', None):
        if req.temperature is not None: engine.llm.temperature = req.temperature
        if req.max_tokens is not None: engine.llm.max_tokens = req.max_tokens
        
        # 调用 llm_service.py 中你写好的 update_config 方法
        current_api = req.api_key if req.api_key else engine.llm.api_key
        current_url = req.base_url if req.base_url else engine.llm.base_url
        current_model = req.model_name if req.model_name else engine.llm.model
        
        engine.llm.update_config(api_key=current_api, base_url=current_url, model=current_model)
    
    return {"status": "success", "message": "大模型配置已更新"}

# 3. 新增 CMS 热重载接口
@app.post("/api/system/rebuild_knowledge")
def rebuild_knowledge():
    """游戏内触发：重建向量知识库并重载剧本"""
    try:
        # 1. 重建 ChromaDB 语料库
        from build_knowledge import build_knowledge
        build_knowledge()
        
        # 2. 热重载剧本事件
        if engine and hasattr(engine, 'director'):
            engine.director.reload_timeline()
            
        # 3. 热重载 Prompt
        if engine and hasattr(engine, 'pm'):
            engine.pm.__init__() # 重新读取 md 文件
            
        return {"status": "success", "message": "✅ 知识库、剧本与提示词已热重载成功！"}
    except Exception as e:
        return {"status": "error", "message": f"重建失败: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
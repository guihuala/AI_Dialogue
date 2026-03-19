from fastapi import FastAPI, HTTPException, File, UploadFile, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
from typing import List, Dict, Any, Optional
import json
import os
import sys
import concurrent.futures
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Avoid noisy HuggingFace tokenizers fork-parallelism warning in multi-worker/background contexts.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# 把当前文件的上一级目录加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.presets import CANDIDATE_POOL
from src.core.game_engine import GameEngine
from datetime import datetime
from src.core.config import (
    PROMPTS_DIR, ROSTER_PATH, DATA_ROOT, SAVES_DIR, EVENTS_DIR,
    DEFAULT_PROMPTS_DIR, DEFAULT_EVENTS_DIR,
    get_user_saves_dir, get_user_chroma_path,
    get_user_prompts_dir, get_user_events_dir, get_user_library_dir
)

# --- 动态列表管理器 ---
# Paths are now managed in src.core.config

def get_current_roster(user_id: str = "default"):
    """动态获取当前角色档案库集"""
    user_prompts_dir = get_user_prompts_dir(user_id)
    user_roster_path = os.path.join(user_prompts_dir, "characters", "roster.json")
    
    # 1. 如果存在用户专属 roster.json，优先使用
    if os.path.exists(user_roster_path):
        try:
            with open(user_roster_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading user roster.json ({user_id}): {e}")
            
    # 2. 如果不存在，从汇编好的 presets 中提取并生成一个基础版存入用户目录
    roster = {}
    for cid, profile in CANDIDATE_POOL.items():
        roster[cid] = {
            "name": profile.Name,
            "archetype": profile.Core_Archetype,
            "tags": profile.Tags,
            "description": profile.Background_Secret[:40] + "...",
            "file": f"{cid}.md",
            "is_player": profile.Name == "陆陈安然"
        }
    
    # 将其写入用户磁盘，使之后的 MOD 能够直接覆盖它
    try:
        os.makedirs(os.path.dirname(user_roster_path), exist_ok=True)
        with open(user_roster_path, 'w', encoding='utf-8') as f:
            json.dump(roster, f, ensure_ascii=False, indent=4)
    except: pass
    
    return roster

try:
    from src.core.data_loader import load_all_events
    import src.core.event_script as es
    EVENT_DATABASE = getattr(es, 'EVENT_DATABASE', {})
    EVENT_DATABASE.update(load_all_events(EVENTS_DIR))
except Exception as e:
    print(f"Warning: Failed to load events data: {e}")
    EVENT_DATABASE = {}

# SAVE_DIR is now SAVES_DIR from config.py
SAVE_DIR = SAVES_DIR

# Global shared pool for background tasks (Prefetching, Reflection)
PREFETCH_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=10)

app = FastAPI(title="Roommate Survival Game API")

@app.on_event("shutdown")
def _shutdown_background_pool():
    try:
        PREFETCH_POOL.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass

# --- Multi-user Engine Manager ---
engines: Dict[str, GameEngine] = {}

def get_user_id(x_visitor_id: Optional[str] = Header(None)):
    """Extract visitor ID from header, fallback to 'default'"""
    return x_visitor_id or "default"

def get_engine(user_id: str) -> GameEngine:
    """Get or create a GameEngine for a specific user"""
    if user_id not in engines:
        engines[user_id] = GameEngine(user_id)
    return engines[user_id]

@app.get("/api/game/candidates")
def get_candidates(user_id: str = Depends(get_user_id)):
    """获取所有可用角色（室友候选人）"""
    roster = get_current_roster(user_id)
    candidates = []
    for cid, info in roster.items():
        # 过滤掉主角 (陆陈安然)，只返回室友候选人
        if info.get("is_player") or info.get("name") == "陆陈安然":
            continue
            
        candidates.append({
            "id": cid,
            "name": info.get("name"),
            "archetype": info.get("archetype"),
            "tags": info.get("tags", []),
            "description": info.get("description"),
            "is_player": False # 候选人肯定不是玩家
        })
    return {"status": "success", "data": candidates}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow any origin for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- 请求体定义 ---
class StartGameRequest(BaseModel):
    roommates: List[str] = []
    custom_prompts: Optional[Dict[str, str]] = None
    is_prefetch: bool = False
    save_id: str = "slot_0" # 默认为临时槽位

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
    hygiene: int = 100
    reputation: int = 100
    arg_count: int = 0
    affinity: Dict[str, float] = {}
    wechat_data_list: List[Dict[str, Any]] = []
    custom_prompts: Optional[Dict[str, str]] = None
    is_prefetch: bool = False
    save_id: str = "slot_0"

class SaveGameRequest(BaseModel):
    slot_id: int
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
    typewriter_speed: Optional[int] = None
    latency_mode: Optional[str] = None
    dialogue_mode: Optional[str] = None

class ReflectionRequest(BaseModel):
    active_roommates: List[str]
    recent_events: str

class AgentChatRequest(BaseModel):
    character: str
    event_context: str
    player_action: str

class GenerateSkillPromptReq(BaseModel):
    concept: str

# --- 路由与接口 ---

@app.post("/api/game/start")
def start_game(req: StartGameRequest, user_id: str = Depends(get_user_id)):
    engine = get_engine(user_id)
    if not engine:
        raise HTTPException(status_code=500, detail="GameEngine not initialized.")
        
    engine.reset()
    
    selected_ids = req.roommates
    roster = get_current_roster()
    
    if not selected_ids:
        import random
        all_ids = list(roster.keys())
        selected_ids = random.sample(all_ids, min(3, len(all_ids)))
        
    try:
        if engine and hasattr(engine, 'mm'):
            engine.mm.current_save_id = req.save_id

        # Ensure user save directory exists
        user_save_dir = get_user_saves_dir(user_id)
        os.makedirs(user_save_dir, exist_ok=True)

        init_res = engine.play_main_turn(
            action_text="", selected_chars=selected_ids, current_evt_id="", is_transition=True,
            api_key="", base_url="", model="", tmp=0.7, top_p=1.0, max_t=350, pres_p=0.3, freq_p=0.5,
            hygiene=100, reputation=100,
            san=100, money=2000,
            gpa=4.0, arg_count=0, chapter=1, turn=0,
            affinity={sid: 50 for sid in selected_ids}, wechat_data_dict={},
            custom_prompts=req.custom_prompts
        )
        engine.latest_game_state_cache = {"request": req.model_dump(), "response": init_res}
        return init_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/game/turn")
def perform_turn(req: GameTurnRequest, user_id: str = Depends(get_user_id)):
    engine = get_engine(user_id)
    if not engine:
        raise HTTPException(status_code=500, detail="GameEngine not initialized.")
        
    try:
        if engine and hasattr(engine, 'mm'):
            engine.mm.current_save_id = req.save_id
            
        wechat_dict = {}
        if req.wechat_data_list:
            for session in req.wechat_data_list:
                chat_name = session.get("chat_name")
                if chat_name:
                    wechat_dict[chat_name] = [[m.get("sender", ""), m.get("message", "")] for m in session.get("messages", [])]

        # 直接调用 play_main_turn，它内部会由 PrefetchManager 检查缓存并触发下一轮预取
        res = engine.play_main_turn(
            action_text=req.choice, selected_chars=req.active_roommates, 
            current_evt_id=req.current_evt_id, is_transition=req.is_transition,
            api_key="", base_url="", model="", tmp=0.7, top_p=1.0, max_t=350, 
            pres_p=0.3, freq_p=0.5,
            hygiene=req.hygiene, reputation=req.reputation,
            san=req.san, money=req.money,
            gpa=req.gpa, arg_count=req.arg_count, 
            chapter=req.chapter, turn=req.turn,
            affinity=req.affinity, wechat_data_dict=wechat_dict,
            is_prefetch=req.is_prefetch,
            custom_prompts=req.custom_prompts
        )
        
        # 触发反思逻辑 (保持原样)
        if engine.event_completion_count >= 3:
            print("🧠 [自动反思] 阈值已到，启动后台提炼...")
            active_roommates = req.active_roommates.copy()
            event_context = ", ".join(engine.recent_event_ids)
            current_chapter = req.chapter
            from src.core.agent_system import ReflectionSystem
            def run_reflection_task():
                try:
                    rs = ReflectionSystem(engine.llm, PROMPTS_DIR)
                    rs.trigger_night_reflection(current_chapter, event_context, active_roommates)
                except Exception as e: print(f"后台反思失败: {e}")
            PREFETCH_POOL.submit(run_reflection_task)
            engine.event_completion_count = 0
            engine.recent_event_ids = []
            res["reflection_triggered"] = True 

        engine.latest_game_state_cache = {"request": req.model_dump(), "response": res}
        return res
    except Exception as e:
        print(f"Turn Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/game/prefetch")
async def pre_generate_script(req: GameTurnRequest, user_id: str = Depends(get_user_id)):
    """后台静默预取下一个事件的剧本"""
    try:
        engine = get_engine(user_id)
        # 分支树已下线：在 single_dm / npc_dm 模式中，prefetch 不再触发主生成，避免重复耗时。
        if engine and getattr(engine, "dialogue_mode", "single_dm") in ["single_dm", "npc_dm"]:
            return {"status": "success", "message": "Prefetch skipped in current dialogue mode"}
        # 强制设置 is_prefetch 为 True 避免干扰正常保存
        req.is_prefetch = True
        
        # 异步启动预取，不等待结果
        PREFETCH_POOL.submit(
            engine.play_main_turn,
            action_text=req.choice, selected_chars=req.active_roommates, 
            current_evt_id=req.current_evt_id, is_transition=req.is_transition,
            api_key="", base_url="", model="", tmp=0.7, top_p=1.0, max_t=350, 
            pres_p=0.3, freq_p=0.5,
            hygiene=req.hygiene, reputation=req.reputation,
            san=req.san, money=req.money,
            gpa=req.gpa, arg_count=req.arg_count, 
            chapter=req.chapter, turn=req.turn,
            affinity=req.affinity, wechat_data_dict={},
            is_prefetch=True,
            custom_prompts=req.custom_prompts
        )
        return {"status": "success", "message": "Prefetch task queued"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/game/monitor")
def monitor_game(user_id: str = Depends(get_user_id)):
    engine = get_engine(user_id)
    # 引擎的计数状态
    engine_stats = {
        "event_completion_count": engine.event_completion_count if engine else 0,
        "recent_event_ids": engine.recent_event_ids if engine else []
    }
    prefetch_stats = {}
    if engine and hasattr(engine, "prefetch_mgr") and hasattr(engine, "llm") and hasattr(engine, "pm"):
        try:
            prefetcher = engine.prefetch_mgr.get_prefetcher(user_id, engine.llm, engine.pm)
            prefetch_stats = prefetcher.get_metrics()
        except Exception:
            prefetch_stats = {}
    return {
        "status": "success", 
        "data": engine.latest_game_state_cache,
        "engine_stats": engine_stats,
        "prefetch_stats": prefetch_stats
    }

@app.post("/api/game/save")
def save_game(req: SaveGameRequest, user_id: str = Depends(get_user_id)):
    if req.slot_id not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="无效的槽位ID")
    
    user_save_dir = get_user_saves_dir(user_id)
    os.makedirs(user_save_dir, exist_ok=True)
    file_path = os.path.join(user_save_dir, f"slot_{req.slot_id}.json")
    
    save_data = {
        "slot_id": req.slot_id, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chapter_info": f"第 {req.chapter} 章 - 第 {req.turn} 回合", "state": req.model_dump() 
    }
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        return {"status": "success", "slot_id": req.slot_id, "message": f"槽位 {req.slot_id} 保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存存档失败: {str(e)}")

@app.get("/api/game/saves_info")
def get_saves_info(user_id: str = Depends(get_user_id)):
    user_save_dir = get_user_saves_dir(user_id)
    os.makedirs(user_save_dir, exist_ok=True)
    info_list = []
    for i in range(1, 4):
        file_path = os.path.join(user_save_dir, f"slot_{i}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    info_list.append({"slot_id": i, "is_empty": False, "timestamp": data.get("timestamp"), "chapter_info": data.get("chapter_info")})
            except:
                info_list.append({"slot_id": i, "is_empty": True, "chapter_info": "存档损坏"})
        else:
            info_list.append({"slot_id": i, "is_empty": True, "chapter_info": "空槽位", "timestamp": ""})
    return {"status": "success", "slots": info_list}

@app.get("/api/game/load/{slot_id}")
def load_game(slot_id: int, user_id: str = Depends(get_user_id)):
    if slot_id not in [1, 2, 3]: raise HTTPException(status_code=400, detail="无效的槽位ID")
    user_save_dir = get_user_saves_dir(user_id)
    file_path = os.path.join(user_save_dir, f"slot_{slot_id}.json")
    if not os.path.exists(file_path): raise HTTPException(status_code=404, detail="该槽位为空")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
        
        # 加载存档时，同步更新 MemoryManager 的 save_id
        engine = get_engine(user_id)
        if engine and hasattr(engine, 'mm'):
            engine.mm.current_save_id = f"slot_{slot_id}"
            
        return {"status": "success", "data": save_data["state"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取存档失败: {str(e)}")

@app.delete("/api/game/save/{slot_id}")
def delete_save_slot(slot_id: int, user_id: str = Depends(get_user_id)):
    """强制抹除指定槽位的存档"""
    if slot_id not in [1, 2, 3]: 
        raise HTTPException(status_code=400, detail="无效的槽位ID")
    
    user_save_dir = get_user_saves_dir(user_id)
    file_path = os.path.join(user_save_dir, f"slot_{slot_id}.json")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return {"status": "success", "message": f"槽位 {slot_id} 已被彻底清空"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")
    return {"status": "success", "message": "该槽位本就为空"}

@app.post("/api/game/reset")
def reset_game(user_id: str = Depends(get_user_id)):
    try:
        engine = get_engine(user_id)
        if engine and hasattr(engine, 'mm'):
            engine.mm.clear_game_history()
        return {"status": "success", "message": "Backend memory cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# 记忆管理接口 (Memory Viewer)
# ==========================================

@app.get("/api/game/memories")
def get_memories(save_id: str = "slot_0", char_name: Optional[str] = None, type: Optional[str] = None, user_id: str = Depends(get_user_id)):
    """获取指定存档下的记忆流数据"""
    engine = get_engine(user_id)
    if not engine or not hasattr(engine, 'mm'):
        raise HTTPException(status_code=500, detail="Memory module offline")
    
    try:
        # 构造过滤条件
        where = {"save_id": save_id}
        if type: where["type"] = type
        
        data = engine.mm.vector_store.collection.get(where=where)
        
        results = []
        if data and data['ids']:
            for i in range(len(data['ids'])):
                meta = data['metadatas'][i]
                doc = data['documents'][i]
                
                # 手动过滤角色名 (简单的文本匹配)
                if char_name and char_name not in doc:
                    continue
                    
                results.append({
                    "id": data['ids'][i],
                    "content": doc,
                    "metadata": meta
                })
        
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/game/memories/{memory_id}")
def delete_memory(memory_id: str, user_id: str = Depends(get_user_id)):
    """删除指定的记忆片段"""
    engine = get_engine(user_id)
    if not engine or not hasattr(engine, 'mm'):
        raise HTTPException(status_code=500, detail="Memory module offline")
    
    try:
        engine.mm.vector_store.delete_memory(memory_id)
        return {"status": "success", "message": f"Memory {memory_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 系统设置接口
# ==========================================

@app.get("/api/system/settings")
def get_settings(user_id: str = Depends(get_user_id)):
    """读取大模型的当前运行配置"""
    engine = get_engine(user_id)
    if engine and hasattr(engine, 'llm'):
        return {
            "status": "success",
            "data": {
                "api_key": engine.llm.api_key or "",
                "base_url": engine.llm.base_url or "",
                "model_name": engine.llm.model or "",
                "temperature": getattr(engine.llm, 'temperature', 0.7),
                "max_tokens": getattr(engine.llm, 'max_tokens', 800),
                "typewriter_speed": getattr(engine.llm, 'typewriter_speed', 30),
                "latency_mode": getattr(engine, 'latency_mode', 'balanced'),
                "dialogue_mode": getattr(engine, 'dialogue_mode', 'single_dm')
            }
        }
    return {"status": "error", "message": "Engine not ready"}

@app.post("/api/system/settings")
def update_settings(req: SettingsRequest, user_id: str = Depends(get_user_id)):
    """更新大模型底层配置"""
    engine = get_engine(user_id)
    if engine and hasattr(engine, 'llm'):
        if req.temperature is not None: engine.llm.temperature = req.temperature
        if req.max_tokens is not None: engine.llm.max_tokens = req.max_tokens
        if req.typewriter_speed is not None: engine.llm.typewriter_speed = req.typewriter_speed
        if req.latency_mode is not None:
            mode = str(req.latency_mode).strip().lower()
            if mode not in ["balanced", "fast", "story"]:
                raise HTTPException(status_code=400, detail="latency_mode must be one of: balanced, fast, story")
            engine.latency_mode = mode
        if req.dialogue_mode is not None:
            dmode = str(req.dialogue_mode).strip().lower()
            if dmode in ["hybrid", "tree_only"]:
                dmode = "single_dm"
            if dmode not in ["single_dm", "npc_dm"]:
                raise HTTPException(status_code=400, detail="dialogue_mode must be one of: single_dm, npc_dm")
            engine.dialogue_mode = dmode
        
        current_api = req.api_key if req.api_key else engine.llm.api_key
        current_url = req.base_url if req.base_url else engine.llm.base_url
        current_model = req.model_name if req.model_name else engine.llm.model
        
        engine.llm.update_config(api_key=current_api, base_url=current_url, model=current_model)
    
    return {"status": "success", "message": "大模型配置已更新"}

# ==========================================
# Web 管理后台专属接口
# ==========================================
class AdminFileSaveReq(BaseModel):
    type: str
    name: str
    content: str

# Paths are now resolved dynamically per user

@app.get("/api/admin/files")
def get_admin_files(user_id: str = Depends(get_user_id)):
    """获取所有剧情配置文件列表"""
    user_prompts_dir = get_user_prompts_dir(user_id)
    user_events_dir = get_user_events_dir(user_id)
    
    # 1. Gather files from both default and user-specific directories
    dirs_to_scan = [DEFAULT_PROMPTS_DIR, user_prompts_dir]
    md_files_set = set()
    for d in dirs_to_scan:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for file in files:
                    if file.endswith((".md", ".json", ".csv")):
                        rel_path = os.path.relpath(os.path.join(root, file), d).replace("\\", "/")
                        md_files_set.add(rel_path)
    md_files = list(md_files_set)
    # 2. Gather CSV files from events directories
    event_dirs = [DEFAULT_EVENTS_DIR, user_events_dir]
    csv_files_set = set()
    for d in event_dirs:
        if os.path.exists(d):
            for file in os.listdir(d):
                if file.endswith((".csv", ".json")):
                    csv_files_set.add(file)
    csv_files = list(csv_files_set)
    
    return {"status": "success", "md": sorted(md_files), "csv": sorted(csv_files)}

@app.get("/api/admin/file")
def read_admin_file(type: str, name: str, user_id: str = Depends(get_user_id)):
    """读取单个文件内容"""
    base_dir = get_user_prompts_dir(user_id) if type == "md" else get_user_events_dir(user_id)
    file_path = os.path.join(base_dir, name)
    
    # 如果用户目录没有该文件，尝试从默认目录读取
    if not os.path.exists(file_path):
        default_base = DEFAULT_PROMPTS_DIR if type == "md" else DEFAULT_EVENTS_DIR
        file_path = os.path.join(default_base, name)
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(file_path, "r", encoding="utf-8") as f:
        return {"status": "success", "content": f.read()}

@app.post("/api/admin/file")
def save_admin_file(req: AdminFileSaveReq, user_id: str = Depends(get_user_id)):
    """保存单个文件内容 (保存到用户私有目录)"""
    base_dir = get_user_prompts_dir(user_id) if req.type == "md" else get_user_events_dir(user_id)
    file_path = os.path.join(base_dir, req.name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "success", "message": f"{req.name} 保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/upload_portrait")
async def upload_portrait(file: UploadFile = File(...)):
    """上传角色立绘图片"""
    portraits_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "WebClient", "public", "assets", "portraits")
    if not os.path.exists(portraits_dir):
        os.makedirs(portraits_dir, exist_ok=True)
    
    # 简单的安全处理：只允许图片格式
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise HTTPException(status_code=400, detail="Only images are allowed")

    file_path = os.path.join(portraits_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"status": "success", "url": f"/assets/portraits/{file.filename}"}

# CMS 热重载接口
@app.post("/api/system/rebuild_knowledge")
def rebuild_knowledge(user_id: str = Depends(get_user_id)):
    """游戏内触发：重建向量知识库并重载剧本"""
    try:
        from src.core.build_knowledge import build_knowledge
        # 重建是全局的还是用户的？如果是重建向量库，可能需要传入 user_id 以隔离路径
        # 这里的 build_knowledge 脚本暂时可能不支持 user_id，如果它只处理原始数据到全局，则保留。
        # 但我们至少要重载当前用户的 engine 状态。
        engine = get_engine(user_id)
        build_knowledge() 
        if engine and hasattr(engine, 'director'): engine.director.reload_timeline()
        if engine and hasattr(engine, 'pm'): engine.pm.__init__() 
        return {"status": "success", "message": "知识库、剧本与提示词已热重载成功！"}
    except Exception as e:
        return {"status": "error", "message": f"重建失败: {str(e)}"}
    
@app.post("/api/game/reflect")
def trigger_reflection(req: ReflectionRequest, user_id: str = Depends(get_user_id)):
    engine = get_engine(user_id)
    if not engine: 
        raise HTTPException(status_code=500, detail="Engine not initialized.")
    try:
        from src.core.agent_system import ReflectionSystem
        
        # 1. 修复初始化：需要传入该用户的 prompts_dir
        user_prompts_dir = get_user_prompts_dir(user_id)
        rs = ReflectionSystem(engine.llm, user_prompts_dir) 
        
        # 2. 修复函数名与参数：调用 trigger_night_reflection，并补全 chapter
        current_chapter = getattr(engine.director, 'current_chapter', 1)
        
        logs = rs.trigger_night_reflection(
            chapter=current_chapter,
            recent_history=req.recent_events,
            active_chars=req.active_roommates
        )
        
        return {"status": "success", "logs": logs}
    except Exception as e:
        import traceback
        print(f"❌ 反思接口崩溃 Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent/chat")
async def agent_chat(req: AgentChatRequest, user_id: str = Depends(get_user_id)):
    engine = get_engine(user_id)
    if not engine: raise HTTPException(status_code=500, detail="Engine not initialized.")
    try:
        from src.core.agent_system import NPCAgent
        from src.core.prompt_manager import PromptManager
        import csv
        
        pm = PromptManager(user_id)
        char_file = pm.char_file_map.get(req.character, "")
        profile_text = pm._read_md(f"characters/{char_file}") if char_file else ""
        rel_text = ""
        rel_csv_path = os.path.join(pm.chars_dir, "relationship.csv")
        if os.path.exists(rel_csv_path):
            with open(rel_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("评价者", "").strip() == req.character:
                        target = row.get("被评价者", "").strip()
                        surface = row.get("表面态度", "").strip()
                        inner = row.get("内心真实评价", "").strip()
                        rel_text += f"- 对待【{target}】：表面[{surface}]，内心觉得[{inner}]。\n"
                        
        agent = NPCAgent(req.character, profile_text, rel_text, engine.llm)
        # 这里可能需要后续的 agent.chat() 调用，目前原始代码只到初始化
        return {"status": "success", "message": "Agent initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ==========================================
# ==========================================
# 个人模组库 Library 接口
# ==========================================

class LibrarySaveReq(BaseModel):
    name: str
    description: str

def _package_mod(user_id: str):
    """助手函数：将用户当前的 active 目录打包为 Content 字典"""
    prompts_dir = get_user_prompts_dir(user_id)
    events_dir = get_user_events_dir(user_id)
    pack_content = {"md": {}, "csv": {}}
    
    # 1. 扫描 Prompts
    if os.path.exists(prompts_dir):
        for root, dirs, files in os.walk(prompts_dir):
            for file in files:
                if file.endswith((".md", ".json")):
                    rel_path = os.path.relpath(os.path.join(root, file), prompts_dir)
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        pack_content["md"][rel_path] = f.read()

    # 2. 扫描 Events
    if os.path.exists(events_dir):
        for file in os.listdir(events_dir):
            if file.endswith((".csv", ".json")):
                with open(os.path.join(events_dir, file), 'r', encoding='utf-8-sig') as f:
                    pack_content["csv"][file] = f.read()
    return pack_content

def _apply_mod_content(user_id: str, content: dict):
    """助手函数：将 Content 字典解包到用户的 active 目录"""
    prompts_dir = get_user_prompts_dir(user_id)
    events_dir = get_user_events_dir(user_id)
    
    # 1. 应用 MD
    md_files = content.get("md", {})
    for rp, text in md_files.items():
        abs_p = os.path.join(prompts_dir, rp)
        os.makedirs(os.path.dirname(abs_p), exist_ok=True)
        with open(abs_p, 'w', encoding='utf-8') as f:
            f.write(text)
            
    # 2. 应用 CSV/JSON
    csv_files = content.get("csv", {})
    for fn, text in csv_files.items():
        abs_p = os.path.join(events_dir, fn)
        os.makedirs(os.path.dirname(abs_p), exist_ok=True)
        with open(abs_p, 'w', encoding='utf-8') as f:
            f.write(text)

@app.post("/api/library/save_current")
def save_to_library(req: LibrarySaveReq, user_id: str = Depends(get_user_id)):
    """将当前活动配置另存为库中的一个模组包"""
    content = _package_mod(user_id)
    import uuid
    item_id = str(uuid.uuid4())[:8]
    data = {
        "id": item_id,
        "name": req.name,
        "author": f"User_{user_id[:4]}",
        "description": req.description,
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    lib_dir = get_user_library_dir(user_id)
    file_path = os.path.join(lib_dir, f"{item_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"status": "success", "id": item_id}

@app.get("/api/library/list")
def list_library(user_id: str = Depends(get_user_id)):
    """列出当前用户库中所有的模组包"""
    lib_dir = get_user_library_dir(user_id)
    items = []
    if os.path.exists(lib_dir):
        for fn in os.listdir(lib_dir):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(lib_dir, fn), 'r', encoding='utf-8') as f:
                        d = json.load(f)
                        items.append({
                            "id": d.get("id"),
                            "name": d.get("name"),
                            "description": d.get("description"),
                            "timestamp": d.get("timestamp")
                        })
                except: pass
    return {"status": "success", "data": sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)}

@app.post("/api/library/apply/{item_id}")
def apply_from_library(item_id: str, user_id: str = Depends(get_user_id)):
    """从个人库中选择一个模组包并应用到当前活动环境"""
    lib_dir = get_user_library_dir(user_id)
    file_path = os.path.join(lib_dir, f"{item_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Mod not found in library")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    _apply_mod_content(user_id, data.get("content", {}))
    
    # 热重载
    engine = get_engine(user_id)
    if engine:
        if hasattr(engine, 'director'): engine.director.reload_timeline()
        if hasattr(engine, 'pm'): engine.pm.__init__(user_id)
        
    return {"status": "success", "message": f"模组 [{data.get('name')}] 已成功应用"}

@app.delete("/api/library/{item_id}")
def delete_from_library(item_id: str, user_id: str = Depends(get_user_id)):
    lib_dir = get_user_library_dir(user_id)
    file_path = os.path.join(lib_dir, f"{item_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
    return {"status": "success"}

# ==========================================
# 创意工坊 Workshop 接口
# ==========================================

WORKSHOP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "workshop")
if not os.path.exists(WORKSHOP_DIR):
    os.makedirs(WORKSHOP_DIR)

class WorkshopPublishReq(BaseModel):
    name: str
    author: str
    description: str

@app.post("/api/workshop/publish_current")
def publish_current_mod(req: WorkshopPublishReq, user_id: str = Depends(get_user_id)):
    """将该玩家当前的活动模组打包并在工坊发布"""
    print(f"📦 [Workshop] User {user_id} publishing mod: {req.name}")
    pack_content = _package_mod(user_id)
    
    import uuid
    item_id = str(uuid.uuid4())[:8]
    data = {
        "id": item_id,
        "type": "prompt_pack",
        "name": req.name,
        "author": req.author,
        "description": req.description,
        "content": pack_content,
        "downloads": 0,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    file_path = os.path.join(WORKSHOP_DIR, f"{item_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {"status": "success", "id": item_id}

@app.get("/api/workshop/list")
def get_workshop_list():
    """列出工坊中所有已发布的模组"""
    items = []
    if os.path.exists(WORKSHOP_DIR):
        for filename in sorted(os.listdir(WORKSHOP_DIR), reverse=True):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(WORKSHOP_DIR, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        items.append({
                            "id": data.get("id"),
                            "type": data.get("type", "prompt_pack"),
                            "name": data.get("name"),
                            "author": data.get("author"),
                            "description": data.get("description"),
                            "downloads": data.get("downloads", 0),
                            "timestamp": data.get("timestamp")
                        })
                except Exception as e:
                    print(f"[Workshop] Error reading {filename}: {e}")
    return {"status": "success", "data": items}

@app.post("/api/workshop/download/{item_id}")
def download_workshop_mod(item_id: str, user_id: str = Depends(get_user_id)):
    """将工坊模组下载到个人模组库"""
    workshop_path = os.path.join(WORKSHOP_DIR, f"{item_id}.json")
    if not os.path.exists(workshop_path):
        raise HTTPException(status_code=404, detail="Item not found")
        
    lib_dir = get_user_library_dir(user_id)
    lib_path = os.path.join(lib_dir, f"{item_id}.json")
    
    shutil.copy2(workshop_path, lib_path)
    
    # 增加下载计数
    try:
        with open(workshop_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data["downloads"] = data.get("downloads", 0) + 1
        with open(workshop_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass
    
    return {"status": "success", "message": "模组已成功添加到您的收藏库"}

@app.post("/api/workshop/apply/{item_id}")
def apply_workshop_mod(item_id: str, user_id: str = Depends(get_user_id)):
    """从工坊直接应用 (内部包含下载到库的步骤)"""
    download_workshop_mod(item_id, user_id)
    return apply_from_library(item_id, user_id)

@app.delete("/api/workshop/{item_id}")
def delete_workshop_item(item_id: str):
    """从工坊仓库彻底删除指定的模组包文件"""
    file_path = os.path.join(WORKSHOP_DIR, f"{item_id}.json")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail="Not found")

class WorkshopUpdateReq(BaseModel):
    name: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None

@app.patch("/api/workshop/{item_id}")
def update_workshop_item(item_id: str, req: WorkshopUpdateReq):
    """更新工坊条目的基础元数据"""
    file_path = os.path.join(WORKSHOP_DIR, f"{item_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if req.name is not None: data["name"] = req.name
        if req.author is not None: data["author"] = req.author
        if req.description is not None: data["description"] = req.description
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 系统干预专属接口
# ==========================================

class MemoryAddReq(BaseModel):
    content: str

@app.get("/api/intervention/memory")
def get_intervention_memories(user_id: str = Depends(get_user_id)):
    """提取底层向量数据库中的所有记忆节点"""
    engine = get_engine(user_id)
    if not engine or not hasattr(engine, 'mm'): return {"status": "error"}
    try:
        data = engine.mm.vector_store.collection.get()
        mems = []
        if data and data['ids']:
            for i, mid in enumerate(data['ids']):
                meta = data['metadatas'][i] or {}
                doc = data['documents'][i] if data.get('documents') else meta.get('content', '')
                mems.append({"id": mid, "type": meta.get("type", "unknown"), "content": doc})
        # 倒序返回，让最新记忆在最前面
        return {"status": "success", "data": mems[::-1]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/intervention/memory")
def add_memory(req: MemoryAddReq, user_id: str = Depends(get_user_id)):
    """强制注入记忆片段"""
    engine = get_engine(user_id)
    from src.models.schema import MemoryItem
    import uuid
    # 标注 type 为 intervention，区别于普通 observation
    mem = MemoryItem(id=str(uuid.uuid4()), type="intervention", content=f"【思想钢印】{req.content}")
    engine.mm.vector_store.add_memories([mem])
    return {"status": "success", "message": "思想钢印注入成功"}

@app.delete("/api/intervention/memory/{mem_id}")
def delete_intervention_memory(mem_id: str, user_id: str = Depends(get_user_id)):
    """抹除指定记忆节点"""
    engine = get_engine(user_id)
    engine.mm.vector_store.collection.delete(ids=[mem_id])
    return {"status": "success"}

@app.get("/api/intervention/tools")
def get_tools(user_id: str = Depends(get_user_id)):
    """获取所有可用的底层挂载工具"""
    engine = get_engine(user_id)
    if not engine: return {"status": "error"}
    # 反射提取 tool_manager 中的自定义工具函数
    methods = [func for func in dir(engine.tm) if callable(getattr(engine.tm, func)) and not func.startswith("__") and func not in ["execute", "get_tool_logs"]]
    return {"status": "success", "data": methods}

class ToolTriggerReq(BaseModel):
    tool_name: str
    args: dict

@app.post("/api/intervention/tool")
def trigger_tool(req: ToolTriggerReq, user_id: str = Depends(get_user_id)):
    """强制越权调用系统工具"""
    engine = get_engine(user_id)
    res = engine.tm.execute(req.tool_name, req.args)
    # 将工具产生的影响（数值/文本）强制注入到当前的全局状态缓存中，从而影响游戏前端
    if engine.latest_game_state_cache and "response" in engine.latest_game_state_cache:
        engine.latest_game_state_cache["response"]["display_text"] += res.get("display_text", "")
        if "san_delta" in res:
            engine.latest_game_state_cache["response"]["san"] += res["san_delta"]
            engine.latest_game_state_cache["response"]["san"] = max(0, min(100, engine.latest_game_state_cache["response"]["san"]))
        if "money_delta" in res:
            engine.latest_game_state_cache["response"]["money"] += res["money_delta"]
        if "gpa_delta" in res:
            engine.latest_game_state_cache["response"]["gpa"] += res["gpa_delta"]
    return {"status": "success", "result": res}

class OverrideAffinityReq(BaseModel):
    char_name: str
    value: int

@app.post("/api/intervention/affinity")
def override_affinity(req: OverrideAffinityReq, user_id: str = Depends(get_user_id)):
    """强制篡改当前会话的好感度缓存"""
    engine = get_engine(user_id)
    if engine.latest_game_state_cache and "response" in engine.latest_game_state_cache and "affinity" in engine.latest_game_state_cache["response"]:
        engine.latest_game_state_cache["response"]["affinity"][req.char_name] = req.value
    return {"status": "success"}

class StatsOverrideReq(BaseModel):
    san: int
    money: float
    gpa: float
    hygiene: int
    reputation: int

@app.post("/api/intervention/stats")
def override_stats(req: StatsOverrideReq, user_id: str = Depends(get_user_id)):
    """强制篡改全局状态缓存中的主角数值"""
    engine = get_engine(user_id)
    if engine.latest_game_state_cache and "response" in engine.latest_game_state_cache:
        engine.latest_game_state_cache["response"]["san"] = req.san
        engine.latest_game_state_cache["response"]["money"] = req.money
        engine.latest_game_state_cache["response"]["gpa"] = req.gpa
        engine.latest_game_state_cache["response"]["hygiene"] = req.hygiene
        engine.latest_game_state_cache["response"]["reputation"] = req.reputation
        return {"status": "success", "message": "数值已强制同步"}
    return {"status": "error", "message": "当前没有运行中的游戏实例"}

@app.post("/api/admin/generate_skill_prompt")
def generate_skill_prompt(req: GenerateSkillPromptReq, user_id: str = Depends(get_user_id)):
    """调用 AI 一键生成 Skill 提示词"""
    engine = get_engine(user_id)
    if not engine or not engine.llm:
        raise HTTPException(status_code=500, detail="LLM service not available")
    
    system_prompt = """你是一个专业的 AI 跑团游戏策划。
你的任务是将玩家模糊的“设想”转化为具体的“系统插件指令 (Skill Prompt)”。

要求：
1. 输出内容必须是直接发给 AI 跑团 DM 的系统指令。
2. 语言要专业、严谨、具有强约束力，能够被大模型精准执行。
3. 如果玩家设想涉及数值（如好感度、金钱、SAN值），请给出明确的判定规则或计算公式。
4. 使用 Markdown 格式（可以包含二级标题、列表等）增强条理性。
5. 不要包含 JSON 格式，直接输出 Markdown 指令正文。
"""
    
    user_prompt = f"玩家的原始设想：{req.concept}\n\n请以此生成一段高质量的系统逻辑提示词，用于扩展游戏功能："
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        completion = engine.llm.client.chat.completions.create(
            model=engine.llm.model,
            messages=messages,
            temperature=0.8,
            max_tokens=1500
        )
        content = completion.choices[0].message.content
        return {"status": "success", "prompt": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)}")

# ==========================================
# 调试与监控接口
# ==========================================

@app.get("/api/debug/chat_history")
def get_chat_history(user_id: str = Depends(get_user_id)):
    engine = get_engine(user_id)
    if not engine or not hasattr(engine, 'mm'):
        return {"status": "error", "message": "Memory module not ready"}
    return {"status": "success", "history": engine.mm.game_history}

@app.get("/api/debug/state")
def get_debug_state(user_id: str = Depends(get_user_id)):
    engine = get_engine(user_id)
    if not engine:
        return {"status": "error", "message": "Engine not ready"}
    
    # 转换 Set 为 List
    recent_events = list(engine.recent_event_ids) if hasattr(engine, 'recent_event_ids') else []
    
    return {
        "status": "success",
        "data": {
            "current_chapter": engine.director.current_chapter if hasattr(engine, 'director') else 1,
            "current_turn": engine.director.current_turn if hasattr(engine, 'director') else 1,
            "event_count": engine.event_completion_count if hasattr(engine, 'event_completion_count') else 0,
            "recent_event_ids": recent_events,
            "roommates": engine.director.active_roommates if hasattr(engine, 'director') else []
        }
    }

@app.post("/api/debug/clear_cache")
def clear_engine_cache(user_id: str = Depends(get_user_id)):
    engine = get_engine(user_id)
    if engine:
        engine.prefetch_futures.clear()
        engine.latest_game_state_cache = None
        return {"status": "success", "message": "Cache cleared for this user"}
    return {"status": "error", "message": "Engine not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

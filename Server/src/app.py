from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import shutil
from typing import List, Dict, Any, Optional
import json
import os
import sys
import concurrent.futures
from fastapi.responses import HTMLResponse

# 把当前文件的上一级目录加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.presets import CANDIDATE_POOL
from src.core.game_engine import GameEngine
from datetime import datetime

# --- 动态列表管理器 ---
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prompts")
ROSTER_PATH = os.path.join(PROMPTS_DIR, "characters", "roster.json")

def get_current_roster():
    """动态获取当前角色档案库集"""
    # 1. 如果存在 roster.json，优先使用
    if os.path.exists(ROSTER_PATH):
        try:
            with open(ROSTER_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading roster.json: {e}")
            
    # 2. 如果不存在，从汇编好的 presets 中提取并生成一个基础版
    roster = {}
    for cid, profile in CANDIDATE_POOL.items():
        roster[cid] = {
            "name": profile.Name,
            "archetype": profile.Core_Archetype,
            "tags": profile.Tags,
            "description": profile.Background_Secret[:40] + "...",
            "file": f"{cid}.md"
        }
    
    # 将其写入磁盘，使之后的 MOD 能够直接覆盖它而不需要修改 Python 代码
    try:
        os.makedirs(os.path.dirname(ROSTER_PATH), exist_ok=True)
        with open(ROSTER_PATH, 'w', encoding='utf-8') as f:
            json.dump(roster, f, ensure_ascii=False, indent=4)
    except: pass
    
    return roster

try:
    from src.core.data_loader import load_all_events
    from src.core.event_script import EVENT_DATABASE
    EVENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "events")
    EVENT_DATABASE.update(load_all_events(EVENTS_DIR))
except Exception as e:
    print(f"Warning: Failed to load events data: {e}")

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Roommate Survival Game API")

@app.get("/api/game/candidates")
def get_candidates():
    """获取所有可选的室友角色基本信息 (动态加载)"""
    roster = get_current_roster()
    data = []
    for cid, info in roster.items():
        data.append({
            "id": cid,
            "name": info.get("name", "未知"),
            "avatar": info.get("avatar", ""),
            "archetype": info.get("archetype", "未知"),
            "tags": info.get("tags", []),
            "description": info.get("description", "")
        })
    return {"status": "success", "data": data}


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

# 全局监听缓存：用于给测试界面做上帝视角
LATEST_GAME_STATE_CACHE = {}

# 最大线程设为 3
PREFETCH_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=3)
PREFETCH_FUTURES = {} 

try:
    engine = GameEngine()
except Exception as e:
    print(f"Warning: Failed to initialize GameEngine fully, error: {e}")
    engine = None

# --- 请求体定义 ---
class StartGameRequest(BaseModel):
    roommates: List[str] = []
    custom_prompts: Optional[Dict[str, str]] = None

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

class ReflectionRequest(BaseModel):
    active_roommates: List[str]
    recent_events: str

class AgentChatRequest(BaseModel):
    character: str
    event_context: str
    player_action: str

# --- 路由与接口 ---

@app.post("/api/game/start")
def start_game(req: StartGameRequest):
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
        init_res = engine.play_main_turn(
            action_text="", selected_chars=selected_ids, current_evt_id="", is_transition=True,
            api_key="", base_url="", model="", tmp=0.7, top_p=1.0, max_t=350, pres_p=0.3, freq_p=0.5,
            hygiene=100, reputation=100,
            san=100, money=2000,
            gpa=4.0, arg_count=0, chapter=1, turn=0,
            affinity={sid: 50 for sid in selected_ids}, wechat_data_dict={},
            custom_prompts=req.custom_prompts
        )
        global LATEST_GAME_STATE_CACHE
        LATEST_GAME_STATE_CACHE = {"request": req.dict(), "response": init_res}
        return init_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/game/turn")
def perform_turn(req: GameTurnRequest):
    if not engine:
        raise HTTPException(status_code=500, detail="GameEngine not initialized.")
        
    try:
        wechat_dict = {}
        if req.wechat_data_list:
            for session in req.wechat_data_list:
                chat_name = session.get("chat_name")
                if chat_name:
                    wechat_dict[chat_name] = [[m.get("sender", ""), m.get("message", "")] for m in session.get("messages", [])]

        #  1. 拦截接管后台计算任务
        cache_key = f"{req.current_evt_id}_{req.turn}_{req.choice}"
        
        if cache_key in PREFETCH_FUTURES:
            print(f"🚀 [影子推演] 命中预计算队列: {req.choice}")
            print(f"⌛ 正在挂起主线程，接管后台剩余计算（如果后台已算完，将瞬间返回）...")
            future = PREFETCH_FUTURES.pop(cache_key)
            
            res = future.result() 
            print(f"✅ [影子推演] 完美衔接！")
            
            # 补写被省略的记忆
            if not res.get("is_end", False) and req.choice and "时间推移" not in req.choice:
                dialogue_lines = []
                seq = res.get("dialogue_sequence", [])
                if isinstance(seq, list):
                    for t in seq:
                        if isinstance(t, dict) and t.get("content"):
                            dialogue_lines.append(f"**[{t.get('speaker', '神秘人')}]** {t.get('content')}")
                engine.mm.save_interaction(user_input=req.choice, ai_response=" ".join(dialogue_lines), user_name="陆陈安然")
        else:
            print(f"⚠️ [影子推演未命中] 正常进行主线程计算: {req.choice}")
            res = engine.play_main_turn(
                action_text=req.choice, selected_chars=req.active_roommates, current_evt_id=req.current_evt_id,
                is_transition=req.is_transition, api_key="", base_url="", model="",
                tmp=0.7, top_p=1.0, max_t=350, pres_p=0.3, freq_p=0.5,
                san=req.san, money=req.money, gpa=req.gpa, arg_count=req.arg_count,
                hygiene=req.hygiene, reputation=req.reputation,
                chapter=req.chapter, turn=req.turn, affinity=req.affinity, wechat_data_dict=wechat_dict,
                is_prefetch=False, custom_prompts=req.custom_prompts
            )
        
        if engine.event_completion_count >= 3:
            print("🧠 [自动反思] 阈值已到，启动后台提炼...")
            active_roommates = req.active_roommates.copy()
            event_context = ", ".join(engine.recent_event_ids)
            current_chapter = req.chapter
    
            from src.core.agent_system import ReflectionSystem
            
            # 这里是同步函数，我们将其封装进线程池
            def run_reflection_task():
                try:
                    # 传入正确的初始化参数
                    rs = ReflectionSystem(engine.llm, PROMPTS_DIR)
                    # 调用正确的函数名
                    rs.trigger_night_reflection(current_chapter, event_context, active_roommates)
                except Exception as e:
                    print(f"后台反思失败: {e}")
    
            PREFETCH_POOL.submit(run_reflection_task)
    
            # 重置计数器
            engine.event_completion_count = 0
            engine.recent_event_ids = []
            res["reflection_triggered"] = True 
            res["reflection_logs"] = ["反思任务已提交至后台线程池..."]

        #  2. 触发下一回合的影子预测执行
        if not res.get("is_end", False) and res.get("next_options"):
            next_turn = res["turn"] 
            
            # 内存清理机制
            if len(PREFETCH_FUTURES) > 15: PREFETCH_FUTURES.clear()
                
            for opt_text in res["next_options"]:
                opt_choice = opt_text.strip()
                if not opt_choice or opt_choice == "继续剧情...": continue
                
                next_cache_key = f"{res['current_evt_id']}_{next_turn}_{opt_choice}"
                
                print(f"将分支加入预计算线程池: {opt_choice}")
                # 提交给线程池并保留“契约票据 (Future)”
                future = PREFETCH_POOL.submit(
                    engine.play_main_turn,
                    action_text=opt_choice, selected_chars=req.active_roommates, current_evt_id=res["current_evt_id"],
                    is_transition=False, api_key="", base_url="", model="",
                    tmp=0.7, top_p=1.0, max_t=350, pres_p=0.3, freq_p=0.5,
                    san=res["san"], money=res["money"], gpa=res["gpa"], hygiene=res["hygiene"], 
                    reputation=res["reputation"], arg_count=res["arg_count"],
                    chapter=res["chapter"], turn=res["turn"], affinity=res["affinity"].copy() if isinstance(res.get("affinity"), dict) else {},
                    wechat_data_dict=wechat_dict,
                    is_prefetch=True
                )
                PREFETCH_FUTURES[next_cache_key] = future

        global LATEST_GAME_STATE_CACHE
        LATEST_GAME_STATE_CACHE = {"request": req.dict(), "response": res}
        
        return res
    except Exception as e:
        print(f"Turn Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/game/monitor")
def monitor_game():
    # 引擎的计数状态
    engine_stats = {
        "event_completion_count": engine.event_completion_count if engine else 0,
        "recent_event_ids": engine.recent_event_ids if engine else []
    }
    return {
        "status": "success", 
        "data": LATEST_GAME_STATE_CACHE,
        "engine_stats": engine_stats
    }

@app.post("/api/game/save")
def save_game(req: SaveGameRequest):
    if req.slot_id not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="无效的槽位ID")
    file_path = os.path.join(SAVE_DIR, f"slot_{req.slot_id}.json")
    save_data = {
        "slot_id": req.slot_id, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chapter_info": f"第 {req.chapter} 章 - 第 {req.turn} 回合", "state": req.dict() 
    }
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        return {"status": "success", "slot_id": req.slot_id, "message": f"槽位 {req.slot_id} 保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存存档失败: {str(e)}")

@app.get("/api/game/saves_info")
def get_saves_info():
    info_list = []
    for i in range(1, 4):
        file_path = os.path.join(SAVE_DIR, f"slot_{i}.json")
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
def load_game(slot_id: int):
    if slot_id not in [1, 2, 3]: raise HTTPException(status_code=400, detail="无效的槽位ID")
    file_path = os.path.join(SAVE_DIR, f"slot_{slot_id}.json")
    if not os.path.exists(file_path): raise HTTPException(status_code=404, detail="该槽位为空")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
        return {"status": "success", "data": save_data["state"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取存档失败: {str(e)}")

@app.delete("/api/game/save/{slot_id}")
def delete_save_slot(slot_id: int):
    """强制抹除指定槽位的存档"""
    if slot_id not in [1, 2, 3]: 
        raise HTTPException(status_code=400, detail="无效的槽位ID")
    
    file_path = os.path.join(SAVE_DIR, f"slot_{slot_id}.json")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return {"status": "success", "message": f"槽位 {slot_id} 已被彻底清空"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")
    return {"status": "success", "message": "该槽位本就为空"}

@app.post("/api/game/reset")
def reset_game():
    try:
        if engine and hasattr(engine, 'mm'):
            engine.mm.clear_game_history()
        return {"status": "success", "message": "Backend memory cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# 系统设置接口
# ==========================================

@app.get("/api/system/settings")
def get_settings():
    """读取大模型的当前运行配置"""
    if engine and hasattr(engine, 'llm'):
        return {
            "status": "success",
            "data": {
                "api_key": engine.llm.api_key or "",
                "base_url": engine.llm.base_url or "",
                "model_name": engine.llm.model or "",
                "temperature": getattr(engine.llm, 'temperature', 0.7),
                "max_tokens": getattr(engine.llm, 'max_tokens', 800),
                "typewriter_speed": getattr(engine.llm, 'typewriter_speed', 30)
            }
        }
    return {"status": "error", "message": "Engine not ready"}

@app.post("/api/system/settings")
def update_settings(req: SettingsRequest):
    """更新大模型底层配置"""
    if getattr(engine, 'llm', None):
        if req.temperature is not None: engine.llm.temperature = req.temperature
        if req.max_tokens is not None: engine.llm.max_tokens = req.max_tokens
        if req.typewriter_speed is not None: engine.llm.typewriter_speed = req.typewriter_speed
        
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

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prompts")
EVENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "events")

@app.get("/api/admin/files")
def get_admin_files():
    """获取所有剧情配置文件列表"""
    md_files = []
    if os.path.exists(PROMPTS_DIR):
        for root, dirs, files in os.walk(PROMPTS_DIR):
            for file in files:
                if file.endswith((".md", ".json")):
                    # 统一路径分隔符，方便前端解析
                    md_files.append(os.path.relpath(os.path.join(root, file), PROMPTS_DIR).replace("\\", "/"))
    
    csv_files = [f for f in os.listdir(EVENTS_DIR) if f.endswith((".csv", ".json"))] if os.path.exists(EVENTS_DIR) else []
    return {"status": "success", "md": sorted(md_files), "csv": sorted(csv_files)}

@app.get("/api/admin/file")
def read_admin_file(type: str, name: str):
    """读取单个文件内容"""
    base_dir = PROMPTS_DIR if type == "md" else EVENTS_DIR
    file_path = os.path.join(base_dir, name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(file_path, "r", encoding="utf-8") as f:
        return {"status": "success", "content": f.read()}

@app.post("/api/admin/file")
def save_admin_file(req: AdminFileSaveReq):
    """保存单个文件内容"""
    base_dir = PROMPTS_DIR if req.type == "md" else EVENTS_DIR
    file_path = os.path.join(base_dir, req.name)
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
def rebuild_knowledge():
    """游戏内触发：重建向量知识库并重载剧本"""
    try:
        from src.core.build_knowledge import build_knowledge
        build_knowledge()
        if engine and hasattr(engine, 'director'): engine.director.reload_timeline()
        if engine and hasattr(engine, 'pm'): engine.pm.__init__() 
        return {"status": "success", "message": "知识库、剧本与提示词已热重载成功！"}
    except Exception as e:
        return {"status": "error", "message": f"重建失败: {str(e)}"}
    
@app.post("/api/game/reflect")
def trigger_reflection(req: ReflectionRequest):
    if not engine: 
        raise HTTPException(status_code=500, detail="Engine not initialized.")
    try:
        from src.core.agent_system import ReflectionSystem
        
        # 1. 修复初始化：需要传入 prompts_dir
        rs = ReflectionSystem(engine.llm, PROMPTS_DIR) 
        
        # 2. 修复函数名与参数：调用 trigger_night_reflection，并补全 chapter
        # 注意：这里假设从全局缓存或 req 中获取 chapter，暂设为 engine.director.current_chapter
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
async def agent_chat(req: AgentChatRequest):
    if not engine: raise HTTPException(status_code=500, detail="Engine not initialized.")
    try:
        from src.core.agent_system import NPCAgent
        from src.core.prompt_manager import PromptManager
        import csv
        
        pm = PromptManager()
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
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
def publish_current_mod(req: WorkshopPublishReq):
    """把当前服务端的 data/prompts 和 data/events 物理文件打包存入工坊仓库"""
    print(f"📦 [Workshop] Start packaging mod: {req.name} by {req.author}")
    pack_content = {"md": {}, "csv": {}}
    
    # 读取 MD 文件
    if os.path.exists(PROMPTS_DIR):
        for root, dirs, files in os.walk(PROMPTS_DIR):
            for file in files:
                if file.endswith((".md", ".json")):
                    rel_path = os.path.relpath(os.path.join(root, file), PROMPTS_DIR)
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        pack_content["md"][rel_path] = f.read()

    # 读取 CSV 文件
    if os.path.exists(EVENTS_DIR):
        for file in os.listdir(EVENTS_DIR):
            if file.endswith(".csv"):
                with open(os.path.join(EVENTS_DIR, file), 'r', encoding='utf-8-sig') as f:
                    pack_content["csv"][file] = f.read()

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
    
    print(f"✅ [Workshop] Mod package created: {item_id}")
    return {"status": "success", "id": item_id}

@app.get("/api/workshop/list")
def get_workshop_list():
    items = []
    if os.path.exists(WORKSHOP_DIR):
        for filename in os.listdir(WORKSHOP_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(WORKSHOP_DIR, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        items.append({
                            "id": data.get("id"),
                            "type": data.get("type"),
                            "name": data.get("name"),
                            "author": data.get("author"),
                            "description": data.get("description"),
                            "downloads": data.get("downloads", 0)
                        })
                except Exception as e:
                    print(f"Error reading workshop file {filename}: {e}")
    return {"status": "success", "data": items}

@app.post("/api/workshop/apply/{item_id}")
def apply_workshop_mod(item_id: str):
    """从工坊解包并重写当前服务端的物理配置文件"""
    print(f"🚀 [Workshop] Applying mod: {item_id}")
    file_path = os.path.join(WORKSHOP_DIR, f"{item_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Item not found")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        content = data.get("content", {})
        
        # 1. 应用 MD 与 JSON (由其 RP 决定)
        md_files = content.get("md", {})
        for rp, text in md_files.items():
            abs_p = os.path.join(PROMPTS_DIR, rp)
            os.makedirs(os.path.dirname(abs_p), exist_ok=True)
            with open(abs_p, 'w', encoding='utf-8') as f:
                f.write(text)
        
        # 2. 应用 CSV
        csv_files = content.get("csv", {})
        for fn, text in csv_files.items():
            abs_p = os.path.join(EVENTS_DIR, fn)
            with open(abs_p, 'w', encoding='utf-8') as f:
                f.write(text)

        # 3. 自动触发热重载
        try:
            from src.core.build_knowledge import build_knowledge
            build_knowledge()
            if engine:
                if hasattr(engine, 'director'): engine.director.reload_timeline()
                if hasattr(engine, 'pm'): engine.pm.__init__()
        except Exception as re_e:
            print(f"Mod Apply Rebuild Warning: {re_e}")
        
        print(f"✅ [Workshop] Mod applied successfully.")
        return {"status": "success", "message": f"模组 [{data.get('name')}] 已成功部署并完成实时热重载。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
def get_memories():
    """提取底层向量数据库中的所有记忆节点"""
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
def add_memory(req: MemoryAddReq):
    """强制注入记忆片段"""
    from src.models.schema import MemoryItem
    import uuid
    # 标注 type 为 intervention，区别于普通 observation
    mem = MemoryItem(id=str(uuid.uuid4()), type="intervention", content=f"【思想钢印】{req.content}")
    engine.mm.vector_store.add_memories([mem])
    return {"status": "success", "message": "思想钢印注入成功"}

@app.delete("/api/intervention/memory/{mem_id}")
def delete_memory(mem_id: str):
    """抹除指定记忆节点"""
    engine.mm.vector_store.collection.delete(ids=[mem_id])
    return {"status": "success"}

@app.get("/api/intervention/tools")
def get_tools():
    """获取所有可用的底层挂载工具"""
    if not engine: return {"status": "error"}
    # 反射提取 tool_manager 中的自定义工具函数
    methods = [func for func in dir(engine.tm) if callable(getattr(engine.tm, func)) and not func.startswith("__") and func not in ["execute", "get_tool_logs"]]
    return {"status": "success", "data": methods}

class ToolTriggerReq(BaseModel):
    tool_name: str
    args: dict

@app.post("/api/intervention/tool")
def trigger_tool(req: ToolTriggerReq):
    """强制越权调用系统工具"""
    res = engine.tm.execute(req.tool_name, req.args)
    # 将工具产生的影响（数值/文本）强制注入到当前的全局状态缓存中，从而影响游戏前端
    global LATEST_GAME_STATE_CACHE
    if "response" in LATEST_GAME_STATE_CACHE:
        LATEST_GAME_STATE_CACHE["response"]["display_text"] += res.get("display_text", "")
        if "san_delta" in res:
            LATEST_GAME_STATE_CACHE["response"]["san"] += res["san_delta"]
            LATEST_GAME_STATE_CACHE["response"]["san"] = max(0, min(100, LATEST_GAME_STATE_CACHE["response"]["san"]))
        if "money_delta" in res:
            LATEST_GAME_STATE_CACHE["response"]["money"] += res["money_delta"]
        if "gpa_delta" in res:
            LATEST_GAME_STATE_CACHE["response"]["gpa"] += res["gpa_delta"]
    return {"status": "success", "result": res}

class OverrideAffinityReq(BaseModel):
    char_name: str
    value: int

@app.post("/api/intervention/affinity")
def override_affinity(req: OverrideAffinityReq):
    """强制篡改当前会话的好感度缓存"""
    global LATEST_GAME_STATE_CACHE
    if "response" in LATEST_GAME_STATE_CACHE and "affinity" in LATEST_GAME_STATE_CACHE["response"]:
        LATEST_GAME_STATE_CACHE["response"]["affinity"][req.char_name] = req.value
    return {"status": "success"}

class StatsOverrideReq(BaseModel):
    san: int
    money: float
    gpa: float
    hygiene: int
    reputation: int

@app.post("/api/intervention/stats")
def override_stats(req: StatsOverrideReq):
    """强制篡改全局状态缓存中的主角数值"""
    global LATEST_GAME_STATE_CACHE
    if "response" in LATEST_GAME_STATE_CACHE:
        LATEST_GAME_STATE_CACHE["response"]["san"] = req.san
        LATEST_GAME_STATE_CACHE["response"]["money"] = req.money
        LATEST_GAME_STATE_CACHE["response"]["gpa"] = req.gpa
        LATEST_GAME_STATE_CACHE["response"]["hygiene"] = req.hygiene
        LATEST_GAME_STATE_CACHE["response"]["reputation"] = req.reputation
        return {"status": "success", "message": "数值已强制同步"}
    return {"status": "error", "message": "当前没有运行中的游戏实例"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
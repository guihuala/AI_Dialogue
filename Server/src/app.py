from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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

app = FastAPI(title="Roommate Survival Game API")

# 全局监听缓存：用于给测试界面做上帝视角
LATEST_GAME_STATE_CACHE = {}

# 最大线程设为 3，防止太多并发导致你的 API 被平台封禁/限流
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
    if not selected_ids:
        import random
        all_ids = list(CANDIDATE_POOL.keys())
        selected_ids = random.sample(all_ids, min(3, len(all_ids)))
        
    try:
        init_res = engine.play_main_turn(
            action_text="", selected_chars=selected_ids, current_evt_id="", is_transition=True,
            api_key="", base_url="", model="", tmp=0.7, top_p=1.0, max_t=350, pres_p=0.3, freq_p=0.5,
            san=100, money=2000, gpa=4.0, arg_count=0, chapter=1, turn=0,
            affinity={sid: 50 for sid in selected_ids}, wechat_data_dict={}
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

        # 🌟 1. 拦截接管后台计算任务
        cache_key = f"{req.current_evt_id}_{req.turn}_{req.choice}"
        
        if cache_key in PREFETCH_FUTURES:
            print(f"🚀 [影子推演] 命中预计算队列: {req.choice}")
            print(f"⌛ 正在挂起主线程，接管后台剩余计算（如果后台已算完，将瞬间返回）...")
            future = PREFETCH_FUTURES.pop(cache_key)
            
            # .result() 是魔法！如果算完了瞬间返回；如果没算完，就只等剩下的一点时间！
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
                chapter=req.chapter, turn=req.turn, affinity=req.affinity, wechat_data_dict=wechat_dict,
                is_prefetch=False
            )

        #  2. 触发下一回合的影子预测执行
        if not res.get("is_end", False) and res.get("next_options"):
            next_turn = res["turn"] 
            
            # 内存清理机制
            if len(PREFETCH_FUTURES) > 15: PREFETCH_FUTURES.clear()
                
            for opt_text in res["next_options"]:
                opt_choice = opt_text.strip()
                if not opt_choice or opt_choice == "继续剧情...": continue
                
                next_cache_key = f"{res['current_evt_id']}_{next_turn}_{opt_choice}"
                
                print(f"🔮 将分支加入预计算线程池: {opt_choice}")
                # 提交给线程池并保留“契约票据 (Future)”
                future = PREFETCH_POOL.submit(
                    engine.play_main_turn,
                    action_text=opt_choice, selected_chars=req.active_roommates, current_evt_id=res["current_evt_id"],
                    is_transition=False, api_key="", base_url="", model="",
                    tmp=0.7, top_p=1.0, max_t=350, pres_p=0.3, freq_p=0.5,
                    san=res["san"], money=res["money"], gpa=res["gpa"], arg_count=res["arg_count"],
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
    return {"status": "success", "data": LATEST_GAME_STATE_CACHE}

# ==========================================
# 以下部分原封不动保留
# ==========================================
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

@app.post("/api/game/reset")
def reset_game():
    try:
        if engine and hasattr(engine, 'mm'):
            engine.mm.clear_game_history()
        return {"status": "success", "message": "Backend memory cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# ⚙️ 系统设置接口 (获取与更新)
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
                "max_tokens": getattr(engine.llm, 'max_tokens', 800)
            }
        }
    return {"status": "error", "message": "Engine not ready"}

@app.post("/api/system/settings")
def update_settings(req: SettingsRequest):
    """更新大模型底层配置"""
    if getattr(engine, 'llm', None):
        if req.temperature is not None: engine.llm.temperature = req.temperature
        if req.max_tokens is not None: engine.llm.max_tokens = req.max_tokens
        
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
                if file.endswith(".md"):
                    # 统一路径分隔符，方便前端解析
                    md_files.append(os.path.relpath(os.path.join(root, file), PROMPTS_DIR).replace("\\", "/"))
    
    csv_files = [f for f in os.listdir(EVENTS_DIR) if f.endswith(".csv")] if os.path.exists(EVENTS_DIR) else []
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
    if not engine: raise HTTPException(status_code=500, detail="Engine not initialized.")
    try:
        from src.core.agent_system import ReflectionSystem
        rs = ReflectionSystem(engine.llm)
        logs = rs.trigger_reflection(req.active_roommates, req.recent_events)
        return {"status": "success", "logs": logs}
    except Exception as e:
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
        react_res = await agent.async_react(req.event_context, req.player_action)
        return {"status": "success", "reaction": react_res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import HTMLResponse
@app.get("/admin", response_class=HTMLResponse)
def serve_admin_ui():
    """ 将 Vue 前端页面直接发给浏览器"""
    ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin.html")
    if not os.path.exists(ui_path):
        return "<h1>⚠️ 找不到 admin.html，请确保将它放在 src 目录下！</h1>"
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
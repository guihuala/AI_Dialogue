from typing import Any, Callable, Dict, List, Optional
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


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
    stability_mode: Optional[str] = None
    turn_debug: Optional[bool] = None


class ReflectionRequest(BaseModel):
    active_roommates: List[str]
    recent_events: str


class AgentChatRequest(BaseModel):
    character: str
    event_context: str
    player_action: str


def build_system_router(
    *,
    get_user_id,
    get_engine: Callable[[str], Any],
    clamp: Callable[[Any, Any, Any], Any],
    temp_min: float,
    temp_max: float,
    tokens_min: int,
    tokens_max: int,
    prompts_dir: str,
    get_user_prompts_dir: Callable[[str], str],
):
    router = APIRouter()

    @router.get("/api/system/settings")
    def get_settings(user_id: str = get_user_id):
        """读取大模型的当前运行配置"""
        engine = get_engine(user_id)
        if engine and hasattr(engine, "llm"):
            return {
                "status": "success",
                "data": {
                    "api_key": engine.llm.api_key or "",
                    "base_url": engine.llm.base_url or "",
                    "model_name": engine.llm.model or "",
                    "temperature": clamp(float(getattr(engine.llm, "temperature", 0.7)), temp_min, temp_max),
                    "max_tokens": int(clamp(int(getattr(engine.llm, "max_tokens", 800)), tokens_min, tokens_max)),
                    "typewriter_speed": getattr(engine.llm, "typewriter_speed", 30),
                    "latency_mode": getattr(engine, "latency_mode", "balanced"),
                    "dialogue_mode": getattr(engine, "dialogue_mode", "single_dm"),
                    "stability_mode": getattr(engine, "stability_mode", "stable"),
                    "turn_debug": bool(getattr(engine, "profile_turns", False)),
                },
            }
        return {"status": "error", "message": "Engine not ready"}

    @router.post("/api/system/settings")
    def update_settings(req: SettingsRequest, user_id: str = get_user_id):
        """更新大模型底层配置"""
        engine = get_engine(user_id)
        if engine and hasattr(engine, "llm"):
            if req.temperature is not None:
                engine.llm.temperature = clamp(float(req.temperature), temp_min, temp_max)
            if req.max_tokens is not None:
                engine.llm.max_tokens = int(clamp(int(req.max_tokens), tokens_min, tokens_max))
            if req.typewriter_speed is not None:
                engine.llm.typewriter_speed = req.typewriter_speed
            if req.latency_mode is not None:
                mode = str(req.latency_mode).strip().lower()
                if mode not in ["balanced", "fast", "story"]:
                    raise HTTPException(status_code=400, detail="latency_mode must be one of: balanced, fast, story")
                engine.latency_mode = mode
            if req.dialogue_mode is not None:
                dmode = str(req.dialogue_mode).strip().lower()
                if dmode not in ["single_dm", "npc_dm", "hybrid", "tree_only"]:
                    raise HTTPException(status_code=400, detail="dialogue_mode must be one of: single_dm, npc_dm, hybrid, tree_only")
                engine.dialogue_mode = dmode
            if req.stability_mode is not None:
                smode = str(req.stability_mode).strip().lower()
                if smode not in ["stable", "balanced"]:
                    raise HTTPException(status_code=400, detail="stability_mode must be one of: stable, balanced")
                engine.stability_mode = smode
            if req.turn_debug is not None:
                engine.profile_turns = bool(req.turn_debug)

            current_api = req.api_key if req.api_key else engine.llm.api_key
            current_url = req.base_url if req.base_url else engine.llm.base_url
            current_model = req.model_name if req.model_name else engine.llm.model

            engine.llm.update_config(api_key=current_api, base_url=current_url, model=current_model)

        return {"status": "success", "message": "大模型配置已更新"}

    @router.post("/api/system/rebuild_knowledge")
    def rebuild_knowledge(user_id: str = get_user_id):
        """游戏内触发：重建向量知识库并重载剧本"""
        try:
            from src.core.build_knowledge import build_knowledge

            engine = get_engine(user_id)
            build_knowledge()
            if engine and hasattr(engine, "director"):
                engine.director.reload_timeline()
            if engine and hasattr(engine, "pm"):
                engine.pm = type(engine.pm)(user_id)
                if hasattr(engine, "player_name") and hasattr(engine.pm, "get_player_name"):
                    engine.player_name = engine.pm.get_player_name()
                if hasattr(engine, "tm") and hasattr(engine.tm, "set_player_name") and hasattr(engine, "player_name"):
                    engine.tm.set_player_name(engine.player_name)
            return {"status": "success", "message": "知识库、剧本与提示词已热重载成功！"}
        except Exception as e:
            return {"status": "error", "message": f"重建失败: {str(e)}"}

    @router.post("/api/game/reflect")
    def trigger_reflection(req: ReflectionRequest, user_id: str = get_user_id):
        engine = get_engine(user_id)
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized.")
        try:
            from src.core.agent_system import ReflectionSystem

            user_prompts_dir = get_user_prompts_dir(user_id)
            rs = ReflectionSystem(engine.llm, user_prompts_dir)

            current_chapter = getattr(engine.director, "current_chapter", 1)

            logs = rs.trigger_night_reflection(
                chapter=current_chapter,
                recent_history=req.recent_events,
                active_chars=req.active_roommates,
            )

            return {"status": "success", "logs": logs}
        except Exception as e:
            import traceback

            print(f"❌ 反思接口崩溃 Traceback:\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/agent/chat")
    async def agent_chat(req: AgentChatRequest, user_id: str = get_user_id):
        engine = get_engine(user_id)
        if not engine:
            raise HTTPException(status_code=500, detail="Engine not initialized.")
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
                with open(rel_csv_path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("评价者", "").strip() == req.character:
                            target = row.get("被评价者", "").strip()
                            surface = row.get("表面态度", "").strip()
                            inner = row.get("内心真实评价", "").strip()
                            rel_text += f"- 对待【{target}】：表面[{surface}]，内心觉得[{inner}]。\n"

            NPCAgent(req.character, profile_text, rel_text, engine.llm)
            return {"status": "success", "message": "Agent initialized"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

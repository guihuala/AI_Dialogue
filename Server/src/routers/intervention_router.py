from typing import Any, Callable
import uuid

from fastapi import APIRouter
from pydantic import BaseModel


class MemoryAddReq(BaseModel):
    content: str


class ToolTriggerReq(BaseModel):
    tool_name: str
    args: dict


class OverrideAffinityReq(BaseModel):
    char_name: str
    value: int


class StatsOverrideReq(BaseModel):
    san: int
    money: float
    gpa: float
    hygiene: int
    reputation: int


def build_intervention_router(
    *,
    get_user_id,
    get_engine: Callable[[str], Any],
):
    router = APIRouter()

    @router.get("/api/intervention/memory")
    def get_intervention_memories(user_id: str = get_user_id):
        """提取底层向量数据库中的所有记忆节点"""
        engine = get_engine(user_id)
        if not engine or not hasattr(engine, "mm"):
            return {"status": "error"}
        try:
            data = engine.mm.vector_store.collection.get()
            mems = []
            if data and data["ids"]:
                for i, mid in enumerate(data["ids"]):
                    meta = data["metadatas"][i] or {}
                    doc = data["documents"][i] if data.get("documents") else meta.get("content", "")
                    mems.append({"id": mid, "type": meta.get("type", "unknown"), "content": doc})
            return {"status": "success", "data": mems[::-1]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @router.post("/api/intervention/memory")
    def add_memory(req: MemoryAddReq, user_id: str = get_user_id):
        """强制注入记忆片段"""
        engine = get_engine(user_id)
        from src.models.schema import MemoryItem

        mem = MemoryItem(id=str(uuid.uuid4()), type="intervention", content=f"【思想钢印】{req.content}")
        engine.mm.vector_store.add_memories([mem])
        return {"status": "success", "message": "思想钢印注入成功"}

    @router.delete("/api/intervention/memory/{mem_id}")
    def delete_intervention_memory(mem_id: str, user_id: str = get_user_id):
        """抹除指定记忆节点"""
        engine = get_engine(user_id)
        engine.mm.vector_store.collection.delete(ids=[mem_id])
        return {"status": "success"}

    @router.get("/api/intervention/tools")
    def get_tools(user_id: str = get_user_id):
        """获取所有可用的底层挂载工具"""
        engine = get_engine(user_id)
        if not engine:
            return {"status": "error"}
        methods = [
            func
            for func in dir(engine.tm)
            if callable(getattr(engine.tm, func)) and not func.startswith("__") and func not in ["execute", "get_tool_logs"]
        ]
        return {"status": "success", "data": methods}

    @router.post("/api/intervention/tool")
    def trigger_tool(req: ToolTriggerReq, user_id: str = get_user_id):
        """强制越权调用系统工具"""
        engine = get_engine(user_id)
        res = engine.tm.execute(req.tool_name, req.args)
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

    @router.post("/api/intervention/affinity")
    def override_affinity(req: OverrideAffinityReq, user_id: str = get_user_id):
        """强制篡改当前会话的好感度缓存"""
        engine = get_engine(user_id)
        if engine.latest_game_state_cache and "response" in engine.latest_game_state_cache and "affinity" in engine.latest_game_state_cache["response"]:
            engine.latest_game_state_cache["response"]["affinity"][req.char_name] = req.value
        return {"status": "success"}

    @router.post("/api/intervention/stats")
    def override_stats(req: StatsOverrideReq, user_id: str = get_user_id):
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

    return router

from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import json
import os
import random

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


class StartGameRequest(BaseModel):
    roommates: List[str] = []
    mod_id: Optional[str] = "default"
    max_turns: Optional[int] = None
    custom_prompts: Optional[Dict[str, str]] = None
    is_prefetch: bool = False
    save_id: str = "slot_0"


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
    narrative_state: Optional[Dict[str, Any]] = None
    system_state: Optional[Dict[str, Any]] = None


def build_game_router(
    *,
    get_user_id,
    get_engine: Callable[[str], Any],
    get_current_roster: Callable[[str], Dict[str, Any]],
    get_user_saves_dir: Callable[[str], str],
    get_user_library_dir: Callable[[str], str],
    with_user_write_lock: Callable[[str], Any],
    append_audit_log: Callable[[str, str, str, str, Dict[str, Any]], None],
    apply_mod_content_atomic: Callable[[str, dict], None],
    validate_mod_content: Callable[[dict, Optional[dict]], Dict[str, Any]],
    package_mod: Callable[[str], Dict[str, Dict[str, str]]],
    read_user_state: Callable[[str], Dict[str, Any]],
    write_user_state: Callable[[str, Dict[str, Any]], None],
    create_snapshot: Callable[..., Dict[str, Any]],
    trim_snapshots: Callable[..., None],
    max_snapshots_keep: int,
    clamp: Callable[[Any, Any, Any], Any],
    temp_min: float,
    temp_max: float,
    tokens_min: int,
    tokens_max: int,
    prompts_dir: str,
    default_prompts_dir: str,
    default_events_dir: str,
    workshop_dir: str,
    prefetch_pool,
):
    router = APIRouter()

    def _now_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _load_fs_content(base_prompts_dir: str, base_events_dir: str) -> Dict[str, Dict[str, str]]:
        content: Dict[str, Dict[str, str]] = {"md": {}, "csv": {}}
        if os.path.exists(base_prompts_dir):
            for root, _, files in os.walk(base_prompts_dir):
                for file in files:
                    if file.endswith((".md", ".json")):
                        rel_path = os.path.relpath(os.path.join(root, file), base_prompts_dir)
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            content["md"][rel_path] = f.read()
        if os.path.exists(base_events_dir):
            for root, _, files in os.walk(base_events_dir):
                for file in files:
                    if file.endswith((".csv", ".json")):
                        rel_path = os.path.relpath(os.path.join(root, file), base_events_dir)
                        with open(os.path.join(root, file), "r", encoding="utf-8-sig") as f:
                            content["csv"][rel_path] = f.read()
        return content

    def _workshop_file_path(item_id: str) -> str:
        return os.path.join(workshop_dir, f"{item_id}.json")

    def _reload_engine_runtime(user_id: str) -> None:
        engine = get_engine(user_id)
        if not engine:
            return
        if hasattr(engine, "director"):
            engine.director.reload_timeline()
        if hasattr(engine, "skeleton_engine"):
            engine.skeleton_engine.reload()
        if hasattr(engine, "pm"):
            engine.pm = type(engine.pm)(user_id)
            if hasattr(engine, "player_name") and hasattr(engine.pm, "get_player_name"):
                engine.player_name = engine.pm.get_player_name()
            if hasattr(engine, "tm") and hasattr(engine.tm, "set_player_name") and hasattr(engine, "player_name"):
                engine.tm.set_player_name(engine.player_name)

    def _load_roster_for_mod(user_id: str, mod_id: Optional[str]) -> Dict[str, Any]:
        selected_mod_id = str(mod_id or "default").strip() or "default"
        if selected_mod_id == "default":
            return get_current_roster(user_id)

        file_path = os.path.join(get_user_library_dir(user_id), f"{selected_mod_id}.json")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="选择的模组不存在于本地库中")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        content = data.get("content", {})
        manifest = data.get("manifest", {})
        validate_mod_content(content, manifest if isinstance(manifest, dict) else None)

        md_files = content.get("md", {}) if isinstance(content, dict) else {}
        roster_text = md_files.get("characters/roster.json") or md_files.get("roster.json")
        if not roster_text:
            return get_current_roster(user_id)

        try:
            roster = json.loads(roster_text)
            if isinstance(roster, dict):
                return roster
        except Exception:
            pass
        return get_current_roster(user_id)

    def _activate_mod_for_new_game(user_id: str, mod_id: Optional[str]) -> None:
        selected_mod_id = str(mod_id or "default").strip() or "default"
        with with_user_write_lock(user_id):
            snapshot = create_snapshot(user_id, package_mod(user_id), reason=f"before_start:{selected_mod_id}")
            trim_snapshots(user_id, keep=max_snapshots_keep)

            if selected_mod_id == "default":
                content = _load_fs_content(default_prompts_dir, default_events_dir)
                active_source = "default"
                active_hash = "default-v1"
            else:
                file_path = os.path.join(get_user_library_dir(user_id), f"{selected_mod_id}.json")
                if not os.path.exists(file_path):
                    raise HTTPException(status_code=404, detail="选择的模组不存在于本地库中")
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 下载副本开局前自动与工坊源记录对齐，避免继续读取过期事件池。
                if str(data.get("source_type", "")) == "downloaded":
                    source_mod_id = str(data.get("source_mod_id", "") or "").strip()
                    if source_mod_id:
                        ws_path = _workshop_file_path(source_mod_id)
                        if os.path.exists(ws_path):
                            try:
                                with open(ws_path, "r", encoding="utf-8") as wf:
                                    ws_data = json.load(wf)
                                ws_content = ws_data.get("content", {})
                                ws_manifest = ws_data.get("manifest", {})
                                # 优先同步工坊最新内容；若上游 manifest 已过期/不一致，降级为仅校验内容结构，
                                # 避免下载副本长期卡在旧版本（例如 prompt 文本更新后 hash 未及时刷新）。
                                ws_manifest_to_use = ws_manifest if isinstance(ws_manifest, dict) else None
                                try:
                                    validate_mod_content(ws_content, ws_manifest_to_use)
                                except Exception:
                                    validate_mod_content(ws_content, None)
                                    ws_manifest_to_use = {}
                                data["content"] = ws_content
                                data["manifest"] = ws_manifest_to_use or {}
                                data["name"] = ws_data.get("name", data.get("name"))
                                data["description"] = ws_data.get("description", data.get("description"))
                                data["timestamp"] = _now_str()
                                with open(file_path, "w", encoding="utf-8") as f:
                                    json.dump(data, f, ensure_ascii=False, indent=2)
                            except Exception:
                                pass

                content = data.get("content", {})
                manifest = data.get("manifest", {})
                validate_mod_content(content, manifest if isinstance(manifest, dict) else None)
                active_source = "library"
                active_hash = manifest.get("mod_id", selected_mod_id) if isinstance(manifest, dict) else selected_mod_id

            apply_mod_content_atomic(user_id, content)

            st = read_user_state(user_id)
            st["active_mod_id"] = selected_mod_id
            st["active_source"] = active_source
            st["active_content_hash"] = active_hash
            st["last_good_snapshot_id"] = snapshot.get("id", "")
            st["updated_at"] = _now_str()
            write_user_state(user_id, st)

        _reload_engine_runtime(user_id)
        append_audit_log(user_id, "activate_mod_for_new_game", "ok", selected_mod_id, {"source": active_source})

    @router.get("/api/game/candidates")
    def get_candidates(
        mod_id: Optional[str] = Query(default="default"),
        user_id: str = get_user_id
    ):
        """获取所有可用角色（室友候选人）"""
        roster = _load_roster_for_mod(user_id, mod_id)
        candidates = []
        for cid, info in roster.items():
            if info.get("is_player"):
                continue

            candidates.append(
                {
                    "id": cid,
                    "name": info.get("name"),
                    "archetype": info.get("archetype"),
                    "tags": info.get("tags", []),
                    "description": info.get("description"),
                    "is_player": False,
                }
            )
        return {"status": "success", "data": candidates}

    @router.post("/api/game/start")
    def start_game(req: StartGameRequest, user_id: str = get_user_id):
        engine = get_engine(user_id)
        if not engine:
            raise HTTPException(status_code=500, detail="GameEngine not initialized.")

        try:
            _activate_mod_for_new_game(user_id, req.mod_id)
            engine = get_engine(user_id)
            engine.reset()

            selected_ids = list(req.roommates or [])
            roster = get_current_roster(user_id)
            all_ids = [cid for cid, info in roster.items() if not bool((info or {}).get("is_player", False))]

            # 过滤掉不属于当前模组 roster 的旧选择
            selected_ids = [sid for sid in selected_ids if sid in all_ids]

            # 若前端已明确选择，则严格尊重选择（不再自动补齐）
            if selected_ids:
                selected_ids = selected_ids[:3]
            else:
                selected_ids = random.sample(all_ids, min(3, len(all_ids)))

            if engine and hasattr(engine, "mm"):
                engine.mm.current_save_id = req.save_id
            if req.max_turns is not None and hasattr(engine, "max_game_turns"):
                try:
                    engine.max_game_turns = int(clamp(int(req.max_turns), 15, 30))
                except Exception:
                    engine.max_game_turns = int(clamp(int(getattr(engine, "max_game_turns", 20)), 15, 30))
            runtime_tmp = clamp(float(getattr(engine.llm, "temperature", 0.7)), temp_min, temp_max)
            runtime_max_t = int(clamp(int(getattr(engine.llm, "max_tokens", 800)), tokens_min, tokens_max))

            user_save_dir = get_user_saves_dir(user_id)
            os.makedirs(user_save_dir, exist_ok=True)

            init_res = engine.play_main_turn(
                action_text="",
                selected_chars=selected_ids,
                current_evt_id="",
                is_transition=True,
                api_key="",
                base_url="",
                model="",
                tmp=runtime_tmp,
                top_p=1.0,
                max_t=runtime_max_t,
                pres_p=0.3,
                freq_p=0.5,
                hygiene=100,
                reputation=100,
                san=100,
                money=2000,
                gpa=4.0,
                arg_count=0,
                chapter=1,
                turn=0,
                affinity={sid: 50 for sid in selected_ids},
                wechat_data_dict={},
                custom_prompts=req.custom_prompts,
            )
            engine.latest_game_state_cache = {"request": req.model_dump(), "response": init_res}
            return init_res
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/game/turn")
    def perform_turn(req: GameTurnRequest, user_id: str = get_user_id):
        engine = get_engine(user_id)
        if not engine:
            raise HTTPException(status_code=500, detail="GameEngine not initialized.")

        try:
            if engine and hasattr(engine, "mm"):
                engine.mm.current_save_id = req.save_id
            runtime_tmp = clamp(float(getattr(engine.llm, "temperature", 0.7)), temp_min, temp_max)
            runtime_max_t = int(clamp(int(getattr(engine.llm, "max_tokens", 800)), tokens_min, tokens_max))

            wechat_dict = {}
            if req.wechat_data_list:
                for session in req.wechat_data_list:
                    chat_name = session.get("chat_name")
                    if chat_name:
                        wechat_dict[chat_name] = [[m.get("sender", ""), m.get("message", "")] for m in session.get("messages", [])]

            res = engine.play_main_turn(
                action_text=req.choice,
                selected_chars=req.active_roommates,
                current_evt_id=req.current_evt_id,
                is_transition=req.is_transition,
                api_key="",
                base_url="",
                model="",
                tmp=runtime_tmp,
                top_p=1.0,
                max_t=runtime_max_t,
                pres_p=0.3,
                freq_p=0.5,
                hygiene=req.hygiene,
                reputation=req.reputation,
                san=req.san,
                money=req.money,
                gpa=req.gpa,
                arg_count=req.arg_count,
                chapter=req.chapter,
                turn=req.turn,
                affinity=req.affinity,
                wechat_data_dict=wechat_dict,
                is_prefetch=req.is_prefetch,
                custom_prompts=req.custom_prompts,
            )

            if engine.event_completion_count >= 3:
                print("🧠 [自动反思] 阈值已到，启动后台提炼...")
                active_roommates = req.active_roommates.copy()
                event_context = ", ".join(engine.recent_event_ids)
                current_chapter = req.chapter
                from src.core.agent_system import ReflectionSystem

                def run_reflection_task():
                    try:
                        rs = ReflectionSystem(engine.llm, prompts_dir)
                        rs.trigger_night_reflection(current_chapter, event_context, active_roommates)
                    except Exception as e:
                        print(f"后台反思失败: {e}")

                prefetch_pool.submit(run_reflection_task)
                engine.event_completion_count = 0
                engine.recent_event_ids = []
                res["reflection_triggered"] = True

            engine.latest_game_state_cache = {"request": req.model_dump(), "response": res}
            return res
        except Exception as e:
            print(f"Turn Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/game/prefetch")
    async def pre_generate_script(req: GameTurnRequest, user_id: str = get_user_id):
        """后台静默预取下一个事件的剧本"""
        try:
            engine = get_engine(user_id)
            runtime_tmp = clamp(float(getattr(engine.llm, "temperature", 0.7)), temp_min, temp_max) if engine and hasattr(engine, "llm") else 0.7
            runtime_max_t = int(clamp(int(getattr(engine.llm, "max_tokens", 800)), tokens_min, tokens_max)) if engine and hasattr(engine, "llm") else 800
            if engine and getattr(engine, "dialogue_mode", "single_dm") in ["single_dm", "npc_dm"]:
                return {"status": "success", "message": "Prefetch skipped in current dialogue mode"}
            req.is_prefetch = True

            prefetch_pool.submit(
                engine.play_main_turn,
                action_text=req.choice,
                selected_chars=req.active_roommates,
                current_evt_id=req.current_evt_id,
                is_transition=req.is_transition,
                api_key="",
                base_url="",
                model="",
                tmp=runtime_tmp,
                top_p=1.0,
                max_t=runtime_max_t,
                pres_p=0.3,
                freq_p=0.5,
                hygiene=req.hygiene,
                reputation=req.reputation,
                san=req.san,
                money=req.money,
                gpa=req.gpa,
                arg_count=req.arg_count,
                chapter=req.chapter,
                turn=req.turn,
                affinity=req.affinity,
                wechat_data_dict={},
                is_prefetch=True,
                custom_prompts=req.custom_prompts,
            )
            return {"status": "success", "message": "Prefetch task queued"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @router.get("/api/game/monitor")
    def monitor_game(user_id: str = get_user_id):
        try:
            engine = get_engine(user_id)
            latest_cache = {}
            if engine:
                try:
                    latest_cache = getattr(engine, "latest_game_state_cache", {}) or {}
                except Exception:
                    latest_cache = {}
            engine_stats = {
                "event_completion_count": int(getattr(engine, "event_completion_count", 0) or 0) if engine else 0,
                "recent_event_ids": list(getattr(engine, "recent_event_ids", []) or []) if engine else [],
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
                "data": latest_cache,
                "engine_stats": engine_stats,
                "prefetch_stats": prefetch_stats,
            }
        except Exception:
            return {
                "status": "success",
                "data": {},
                "engine_stats": {"event_completion_count": 0, "recent_event_ids": []},
                "prefetch_stats": {},
            }

    @router.post("/api/game/save")
    def save_game(req: SaveGameRequest, user_id: str = get_user_id):
        if req.slot_id not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="无效的槽位ID")

        user_save_dir = get_user_saves_dir(user_id)
        os.makedirs(user_save_dir, exist_ok=True)
        file_path = os.path.join(user_save_dir, f"slot_{req.slot_id}.json")

        save_data = {
            "slot_id": req.slot_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "chapter_info": f"第 {req.chapter} 章 - 第 {req.turn} 回合",
            "state": req.model_dump(),
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
            return {"status": "success", "slot_id": req.slot_id, "message": f"槽位 {req.slot_id} 保存成功"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存存档失败: {str(e)}")

    @router.get("/api/game/saves_info")
    def get_saves_info(user_id: str = get_user_id):
        user_save_dir = get_user_saves_dir(user_id)
        os.makedirs(user_save_dir, exist_ok=True)
        info_list = []
        for i in range(1, 4):
            file_path = os.path.join(user_save_dir, f"slot_{i}.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        info_list.append(
                            {
                                "slot_id": i,
                                "is_empty": False,
                                "timestamp": data.get("timestamp"),
                                "chapter_info": data.get("chapter_info"),
                            }
                        )
                except Exception:
                    info_list.append({"slot_id": i, "is_empty": True, "chapter_info": "存档损坏"})
            else:
                info_list.append({"slot_id": i, "is_empty": True, "chapter_info": "空槽位", "timestamp": ""})
        return {"status": "success", "slots": info_list}

    @router.get("/api/game/load/{slot_id}")
    def load_game(slot_id: int, user_id: str = get_user_id):
        if slot_id not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="无效的槽位ID")
        user_save_dir = get_user_saves_dir(user_id)
        file_path = os.path.join(user_save_dir, f"slot_{slot_id}.json")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="该槽位为空")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                save_data = json.load(f)

            engine = get_engine(user_id)
            if engine and hasattr(engine, "mm"):
                engine.mm.current_save_id = f"slot_{slot_id}"

            state = save_data.get("state", {})
            if engine and hasattr(engine, "narrative_state_mgr") and isinstance(state, dict):
                try:
                    engine.narrative_state_mgr.load(state.get("narrative_state"))
                except Exception:
                    pass
            if engine and hasattr(engine, "system_state_mgr") and isinstance(state, dict):
                try:
                    engine.system_state_mgr.load(state.get("system_state"))
                except Exception:
                    pass
            roster = get_current_roster(user_id)
            player_name = getattr(engine, "player_name", "") or "当前主角"
            for _, info in roster.items():
                if isinstance(info, dict) and bool(info.get("is_player", False)):
                    candidate = str(info.get("name", "")).strip()
                    if candidate:
                        player_name = candidate
                        break
            if isinstance(state, dict):
                state["player_name"] = state.get("player_name") or player_name

            return {"status": "success", "data": state}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取存档失败: {str(e)}")

    @router.delete("/api/game/save/{slot_id}")
    def delete_save_slot(slot_id: int, user_id: str = get_user_id):
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

    @router.post("/api/game/reset")
    def reset_game(user_id: str = get_user_id):
        try:
            engine = get_engine(user_id)
            if engine and hasattr(engine, "mm"):
                engine.mm.clear_game_history()
            return {"status": "success", "message": "Backend memory cleared"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @router.get("/api/game/memories")
    def get_memories(save_id: str = "slot_0", char_name: Optional[str] = None, type: Optional[str] = None, user_id: str = get_user_id):
        """获取指定存档下的记忆流数据"""
        engine = get_engine(user_id)
        if not engine or not hasattr(engine, "mm"):
            raise HTTPException(status_code=500, detail="Memory module offline")

        try:
            where = {"save_id": save_id}
            if type:
                where["type"] = type

            data = engine.mm.vector_store.collection.get(where=where)

            results = []
            if data and data["ids"]:
                for i in range(len(data["ids"])):
                    meta = data["metadatas"][i]
                    doc = data["documents"][i]
                    if char_name and char_name not in doc:
                        continue

                    results.append({"id": data["ids"][i], "content": doc, "metadata": meta})

            return {"status": "success", "data": results}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/api/game/memories/{memory_id}")
    def delete_memory(memory_id: str, user_id: str = get_user_id):
        """删除指定的记忆片段"""
        engine = get_engine(user_id)
        if not engine or not hasattr(engine, "mm"):
            raise HTTPException(status_code=500, detail="Memory module offline")

        try:
            engine.mm.vector_store.delete_memory(memory_id)
            return {"status": "success", "message": f"Memory {memory_id} deleted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

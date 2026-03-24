from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import json
import os
import random
import re

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


class AgentChooseRequest(BaseModel):
    options: List[str]
    game_state: Dict[str, Any] = {}
    system_state: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []


class AgentReportRequest(BaseModel):
    history: List[Dict[str, Any]] = []
    final_state: Dict[str, Any] = {}


class AgentCriticRequest(BaseModel):
    report: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []
    final_state: Dict[str, Any] = {}


class AgentRevisionProposeRequest(BaseModel):
    target_mod_id: Optional[str] = None
    report: Dict[str, Any] = {}
    critic: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []
    final_state: Dict[str, Any] = {}


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

    def _revisions_root(user_id: str) -> str:
        return os.path.join(os.path.dirname(get_user_library_dir(user_id)), "revisions")

    def _revisions_queue_dir(user_id: str) -> str:
        return os.path.join(_revisions_root(user_id), "queue")

    def _revisions_runs_path(user_id: str) -> str:
        return os.path.join(_revisions_root(user_id), "run_reports.jsonl")

    def _can_edit_mod_for_revision(user_id: str, mod_id: str) -> tuple[bool, str]:
        target = str(mod_id or "").strip() or "default"
        if target == "default":
            return False, "默认模组只读，请先另存到本地模组库后再迭代"
        file_path = os.path.join(get_user_library_dir(user_id), f"{target}.json")
        if not os.path.exists(file_path):
            return False, "目标模组不存在或无权限"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            owner = str(data.get("owner_user_id", "") or "").strip()
            if owner and owner != str(user_id):
                return False, "你无权修订该模组"
        except Exception:
            return False, "目标模组读取失败"
        return True, ""

    def _append_run_report(user_id: str, row: Dict[str, Any]) -> None:
        path = _revisions_runs_path(user_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        line = json.dumps(row, ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _load_recent_run_reports(user_id: str, *, target_mod_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        path = _revisions_runs_path(user_id)
        if not os.path.exists(path):
            return []
        rows: List[Dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-200:]
            for ln in reversed(lines):
                ln = str(ln or "").strip()
                if not ln:
                    continue
                try:
                    item = json.loads(ln)
                except Exception:
                    continue
                if not isinstance(item, dict):
                    continue
                if str(item.get("target_mod_id", "") or "").strip() != str(target_mod_id or "").strip():
                    continue
                rows.append(item)
                if len(rows) >= max(1, int(limit)):
                    break
        except Exception:
            return []
        return rows

    def _normalize_text_for_fingerprint(text: str) -> str:
        s = str(text or "").lower().strip()
        s = re.sub(r"\s+", " ", s)
        return s[:800]

    def _proposal_fingerprint(item: Dict[str, Any]) -> str:
        if not isinstance(item, dict):
            return ""
        files: List[str] = []
        changes = item.get("changes", []) if isinstance(item.get("changes", []), list) else []
        for ch in changes:
            if not isinstance(ch, dict):
                continue
            f = str(ch.get("file", "") or "").strip()
            if f:
                files.append(f)
        files = sorted(list(set(files)))[:10]
        summary = _normalize_text_for_fingerprint(str(item.get("summary", "") or ""))
        validator = item.get("validator", {}) if isinstance(item.get("validator", {}), dict) else {}
        issues = validator.get("common_issues", []) if isinstance(validator.get("common_issues", []), list) else []
        issues_text = "|".join(
            sorted([_normalize_text_for_fingerprint(str(x or "")) for x in issues if str(x or "").strip()])[:6]
        )
        return f"{'|'.join(files)}##{summary}##{issues_text}"

    def _load_recent_revisions_for_mod(user_id: str, *, target_mod_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for bucket in ("queue", "applied", "rejected"):
            d = os.path.join(_revisions_root(user_id), bucket)
            if not os.path.exists(d):
                continue
            for fn in os.listdir(d):
                if not fn.endswith(".json"):
                    continue
                path = os.path.join(d, fn)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        item = json.load(f)
                except Exception:
                    continue
                if not isinstance(item, dict):
                    continue
                if str(item.get("target_mod_id", "") or "").strip() != str(target_mod_id or "").strip():
                    continue
                item["_bucket"] = bucket
                rows.append(item)
        rows.sort(key=lambda x: str(x.get("created_at", "") or ""), reverse=True)
        return rows[: max(1, int(limit))]

    def _load_mod_content_for_revision(user_id: str, mod_id: str) -> Dict[str, Dict[str, str]]:
        target = str(mod_id or "").strip() or "default"
        if target == "default":
            return {"md": {}, "csv": {}}
        file_path = os.path.join(get_user_library_dir(user_id), f"{target}.json")
        if not os.path.exists(file_path):
            return {"md": {}, "csv": {}}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            content = data.get("content", {})
            return {
                "md": dict(content.get("md", {}) or {}) if isinstance(content, dict) else {},
                "csv": dict(content.get("csv", {}) or {}) if isinstance(content, dict) else {},
            }
        except Exception:
            return {"md": {}, "csv": {}}

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
        if not isinstance(roster, dict) or not roster:
            roster = get_current_roster(user_id)
        candidates = []
        for cid, info in roster.items():
            item = info if isinstance(info, dict) else {}
            if bool(item.get("is_player", False)):
                continue

            name = str(
                item.get("name")
                or item.get("Name")
                or item.get("display_name")
                or item.get("角色名")
                or cid
            ).strip() or str(cid)

            raw_tags = item.get("tags", [])
            if isinstance(raw_tags, str):
                tags = [x.strip() for x in raw_tags.split(",") if x.strip()]
            elif isinstance(raw_tags, list):
                tags = [str(x).strip() for x in raw_tags if str(x).strip()]
            else:
                tags = []

            archetype = str(item.get("archetype") or item.get("Archetype") or item.get("role") or "").strip()
            description = str(item.get("description") or item.get("desc") or "").strip()
            avatar = str(item.get("avatar") or item.get("image") or item.get("portrait") or "").strip()

            candidates.append(
                {
                    "id": cid,
                    "name": name,
                    "archetype": archetype,
                    "tags": tags,
                    "description": description,
                    "avatar": avatar,
                    "is_player": False,
                }
            )
        if not candidates:
            # 兜底：回退默认 roster，避免前端选人界面空白。
            fallback = get_current_roster(user_id)
            for cid, info in fallback.items():
                item = info if isinstance(info, dict) else {}
                if bool(item.get("is_player", False)):
                    continue
                candidates.append(
                    {
                        "id": cid,
                        "name": str(item.get("name") or cid),
                        "archetype": str(item.get("archetype") or ""),
                        "tags": item.get("tags", []) if isinstance(item.get("tags", []), list) else [],
                        "description": str(item.get("description") or ""),
                        "avatar": str(item.get("avatar") or ""),
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

    @router.post("/api/game/agent/choose")
    def agent_choose(req: AgentChooseRequest, user_id: str = get_user_id):
        options = [str(x or "").strip() for x in list(req.options or []) if str(x or "").strip()]
        if not options:
            return {"status": "error", "detail": "no_options"}

        # 先给一个本地兜底（无模型时也可用）
        fallback_idx = 0
        lowered = [s.lower() for s in options]
        for i, text in enumerate(lowered):
            if ("中立" in options[i]) or ("考虑" in options[i]) or ("先" in options[i]):
                fallback_idx = i
                break

        engine = get_engine(user_id)
        llm = getattr(engine, "llm", None) if engine else None
        if llm is None:
            return {
                "status": "success",
                "choice": options[fallback_idx],
                "choice_index": fallback_idx,
                "reason": "llm_unavailable_fallback",
            }

        system_prompt = (
            "你是文字游戏调试代理，只负责在给定选项中选择一个。\n"
            "目标：让剧情可推进、避免频繁卡死。\n"
            "返回 JSON：{\"choice_index\": number, \"reason\": string}\n"
            "规则：\n"
            "1) 必须从 0..N-1 中选一个有效下标。\n"
            "2) 优先选择具体可执行且信息量更高的选项。\n"
            "3) 避免总是同一态度；尽量保持多样性。\n"
            "4) reason 一句话即可。"
        )
        payload = {
            "options": options,
            "game_state": req.game_state or {},
            "system_state": req.system_state or {},
            "recent_history": (req.history or [])[-8:],
        }
        raw = llm.generate_response(
            system_prompt=system_prompt,
            user_input=json.dumps(payload, ensure_ascii=False),
            context="",
            temperature=0.3,
            max_tokens=120,
        )
        idx = fallback_idx
        reason = "fallback"
        try:
            parsed = json.loads(str(raw or "{}"))
            if isinstance(parsed, dict):
                idx = int(parsed.get("choice_index", fallback_idx))
                reason = str(parsed.get("reason", "model_choice") or "model_choice")
        except Exception:
            idx = fallback_idx
            reason = "parse_fallback"
        if idx < 0 or idx >= len(options):
            idx = fallback_idx
            reason = "range_fallback"
        return {
            "status": "success",
            "choice": options[idx],
            "choice_index": idx,
            "reason": reason,
        }

    @router.post("/api/game/agent/report")
    def agent_report(req: AgentReportRequest, user_id: str = get_user_id):
        history = list(req.history or [])
        final_state = req.final_state or {}
        target_mod_id = str((final_state or {}).get("target_mod_id", "") or "").strip()
        if not target_mod_id:
            st = read_user_state(user_id)
            target_mod_id = str(st.get("active_mod_id", "default") or "default")
        engine = get_engine(user_id)
        llm = getattr(engine, "llm", None) if engine else None
        if llm is None:
            _append_run_report(
                user_id,
                {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "target_mod_id": target_mod_id,
                    "turn_count": len(history),
                    "summary": "llm_unavailable_fallback",
                    "issues": ["llm_unavailable"],
                    "score": 0,
                },
            )
            return {
                "status": "success",
                "report": {
                    "summary": "调试回放完成（无模型总结，使用简版统计）。",
                    "turn_count": len(history),
                    "highlights": [],
                    "issues": ["未连接 LLM，总结为本地降级版。"],
                },
            }

        system_prompt = (
            "你是游戏测试报告助手。请根据对局历史与最终状态生成简短调试报告。\n"
            "只返回 JSON：{\"summary\":string,\"turn_count\":number,\"highlights\":string[],\"issues\":string[],\"suggestions\":string[]}\n"
            "要求：\n"
            "- summary 1-2 句\n"
            "- highlights 2-5 条\n"
            "- issues 0-5 条\n"
            "- suggestions 1-5 条"
        )
        payload = {
            "history_tail": history[-30:],
            "turn_count": len(history),
            "final_state": final_state,
        }
        raw = llm.generate_response(
            system_prompt=system_prompt,
            user_input=json.dumps(payload, ensure_ascii=False),
            context="",
            temperature=0.3,
            max_tokens=420,
        )
        try:
            parsed = json.loads(str(raw or "{}"))
            if isinstance(parsed, dict):
                parsed["turn_count"] = int(parsed.get("turn_count", len(history)) or len(history))
                _append_run_report(
                    user_id,
                    {
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "target_mod_id": target_mod_id,
                        "turn_count": len(history),
                        "summary": str(parsed.get("summary", "") or "")[:300],
                        "issues": list(parsed.get("issues", []) if isinstance(parsed.get("issues", []), list) else [])[:8],
                        "score": int((parsed.get("score", 0) or 0)) if str(parsed.get("score", "")).strip() else 0,
                    },
                )
                return {"status": "success", "report": parsed}
        except Exception:
            pass
        _append_run_report(
            user_id,
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "target_mod_id": target_mod_id,
                "turn_count": len(history),
                "summary": "report_parse_failed",
                "issues": ["report_parse_failed"],
                "score": 0,
            },
        )
        return {
            "status": "success",
            "report": {
                "summary": "对局已结束，报告解析失败，返回降级摘要。",
                "turn_count": len(history),
                "highlights": [],
                "issues": ["report_parse_failed"],
                "suggestions": ["检查模型 JSON 输出稳定性"],
            },
        }

    @router.post("/api/game/agent/critic")
    def agent_critic(req: AgentCriticRequest, user_id: str = get_user_id):
        report = req.report if isinstance(req.report, dict) else {}
        history = list(req.history or [])
        final_state = req.final_state or {}

        engine = get_engine(user_id)
        llm = getattr(engine, "llm", None) if engine else None
        if llm is None:
            return {
                "status": "success",
                "critic": {
                    "overall_score": 60,
                    "dimensions": [
                        {"name": "可推进性", "score": 60},
                        {"name": "叙事连贯", "score": 60},
                        {"name": "选择反馈", "score": 55},
                    ],
                    "strengths": [],
                    "weaknesses": ["未连接 LLM，使用降级评审。"],
                    "suggestions": ["先确认 LLM 可用后再启用自迭代评审。"],
                },
            }

        system_prompt = (
            "你是文字游戏测试评审AI。给定一份对局报告和最终状态，请做结构化评审。\n"
            "只返回 JSON：\n"
            "{\"overall_score\":0-100,\"dimensions\":[{\"name\":string,\"score\":0-100}],"
            "\"strengths\":string[],\"weaknesses\":string[],\"suggestions\":string[]}\n"
            "要求：\n"
            "1) dimensions 至少包含：可推进性、叙事连贯、选择反馈、角色表现。\n"
            "2) suggestions 必须可执行，且尽量指向系统/skill/事件配置改动。\n"
            "3) 输出精炼，不要附加解释文本。"
        )
        payload = {
            "report": report,
            "history_tail": history[-30:],
            "final_state": final_state,
        }
        raw = llm.generate_response(
            system_prompt=system_prompt,
            user_input=json.dumps(payload, ensure_ascii=False),
            context="",
            temperature=0.25,
            max_tokens=420,
        )
        try:
            parsed = json.loads(str(raw or "{}"))
            if isinstance(parsed, dict):
                parsed["overall_score"] = max(0, min(100, int(parsed.get("overall_score", 60) or 60)))
                dims = parsed.get("dimensions")
                if not isinstance(dims, list):
                    parsed["dimensions"] = []
                return {"status": "success", "critic": parsed}
        except Exception:
            pass
        return {
            "status": "success",
            "critic": {
                "overall_score": 58,
                "dimensions": [],
                "strengths": [],
                "weaknesses": ["critic_parse_failed"],
                "suggestions": ["报告评审解析失败，建议检查 critic 输出稳定性。"],
            },
        }

    @router.post("/api/game/agent/revision/propose")
    def agent_revision_propose(req: AgentRevisionProposeRequest, user_id: str = get_user_id):
        st = read_user_state(user_id)
        target_mod_id = str(req.target_mod_id or st.get("active_mod_id") or "").strip() or "default"
        ok, reason = _can_edit_mod_for_revision(user_id, target_mod_id)
        if not ok:
            raise HTTPException(status_code=403, detail=reason)

        engine = get_engine(user_id)
        llm = getattr(engine, "llm", None) if engine else None
        if llm is None:
            raise HTTPException(status_code=503, detail="LLM 不可用，无法生成修订提案")

        target_content = _load_mod_content_for_revision(user_id, target_mod_id)
        editable_files = []
        editable_files.extend([f"prompts/{k}" for k in list((target_content.get("md", {}) or {}).keys())])
        editable_files.extend([f"events/{k}" for k in list((target_content.get("csv", {}) or {}).keys())])
        editable_files = sorted(list({str(x).strip() for x in editable_files if str(x).strip()}))[:60]

        system_prompt = (
            "你是模组修订提案助手。请基于报告与评审，输出可审计的结构化提案。\n"
            "只返回 JSON，格式：\n"
            "{"
            "\"summary\":string,"
            "\"risk_level\":\"low|medium|high\","
            "\"changes\":[{\"file\":string,\"op\":\"update\",\"reason\":string,\"content_after\":string,\"patch_text\":string}],"
            "\"memory_candidates\":[{\"content\":string,\"importance\":1-10,\"tags\":[string]}]"
            "}\n"
            "要求：\n"
            "1) changes 仅允许 prompts/events 相关文本文件。\n"
            "2) 优先提供 content_after（完整新内容）；patch_text 仅作为备注。\n"
            "3) memory_candidates 用于长期记忆候选，内容要简短具体。"
        )
        payload = {
            "target_mod_id": target_mod_id,
            "report": req.report or {},
            "critic": req.critic or {},
            "history_tail": (req.history or [])[-20:],
            "final_state": req.final_state or {},
            "editable_files": editable_files,
        }
        raw = llm.generate_response(
            system_prompt=system_prompt,
            user_input=json.dumps(payload, ensure_ascii=False),
            context="",
            temperature=0.25,
            max_tokens=700,
        )
        try:
            parsed = json.loads(str(raw or "{}"))
        except Exception:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}

        changes = parsed.get("changes") if isinstance(parsed.get("changes"), list) else []
        filtered_changes = []
        allowed_prefixes = ("prompts/", "events/")
        for ch in changes:
            if not isinstance(ch, dict):
                continue
            file_name = str(ch.get("file", "") or "").strip()
            if not file_name.startswith(allowed_prefixes):
                continue
            filtered_changes.append(
                {
                    "file": file_name,
                    "op": "update",
                    "reason": str(ch.get("reason", "") or "").strip(),
                    "content_after": str(ch.get("content_after", "") or ""),
                    "patch_text": str(ch.get("patch_text", "") or "").strip()[:4000],
                }
            )

        mem = parsed.get("memory_candidates") if isinstance(parsed.get("memory_candidates"), list) else []
        memory_candidates = []
        for item in mem:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", "") or "").strip()
            if not content:
                continue
            importance = int(item.get("importance", 6) or 6)
            importance = max(1, min(10, importance))
            tags = item.get("tags") if isinstance(item.get("tags"), list) else []
            tags = [str(t).strip() for t in tags if str(t).strip()][:8]
            memory_candidates.append({"content": content[:300], "importance": importance, "tags": tags})

        recent_runs = _load_recent_run_reports(user_id, target_mod_id=target_mod_id, limit=8)
        run_count = len(recent_runs)
        issue_freq: Dict[str, int] = {}
        for r in recent_runs:
            issues = r.get("issues", []) if isinstance(r.get("issues", []), list) else []
            for it in issues:
                k = str(it or "").strip()
                if not k:
                    continue
                issue_freq[k] = int(issue_freq.get(k, 0) or 0) + 1
        common_issues = [k for k, _ in sorted(issue_freq.items(), key=lambda kv: kv[1], reverse=True)[:5]]

        proposal_id = f"rev-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(random.randint(1000, 9999))}"
        structured_count = sum(1 for x in filtered_changes if str(x.get("content_after", "")).strip())
        total_changes = len(filtered_changes)
        structured_ratio = (float(structured_count) / float(total_changes)) if total_changes > 0 else 0.0
        critic_score = 0
        try:
            critic_score = int((req.critic or {}).get("overall_score", 0) or 0)
        except Exception:
            critic_score = 0
        critic_score = max(0, min(100, critic_score))
        quality_score = int(round(critic_score * 0.6 + structured_ratio * 100.0 * 0.4))
        priority = "high" if quality_score >= 75 else ("medium" if quality_score >= 50 else "low")
        schema_ok = total_changes > 0
        policy_ok = True
        blocked_rules = []
        if total_changes > 8:
            policy_ok = False
            blocked_rules.append("too_many_changes")
        if total_changes > 0 and structured_ratio < 0.5:
            blocked_rules.append("low_structured_ratio")
        if run_count < 2:
            blocked_rules.append("insufficient_run_samples")
        duplicate_proposal = False
        duplicate_with = ""
        merge_suggestion = False
        merge_with = ""
        current_fp = _proposal_fingerprint(
            {
                "summary": parsed.get("summary", ""),
                "changes": filtered_changes,
                "validator": {"common_issues": common_issues},
            }
        )
        current_files = {
            str(x.get("file", "") or "").strip()
            for x in filtered_changes
            if isinstance(x, dict) and str(x.get("file", "") or "").strip()
        }
        for prev in _load_recent_revisions_for_mod(user_id, target_mod_id=target_mod_id, limit=20):
            prev_id = str(prev.get("proposal_id", "") or "").strip()
            if not prev_id:
                continue
            prev_fp = _proposal_fingerprint(prev)
            if current_fp and prev_fp == current_fp:
                duplicate_proposal = True
                duplicate_with = prev_id
                if "duplicate_proposal" not in blocked_rules:
                    blocked_rules.append("duplicate_proposal")
                break
            prev_changes = prev.get("changes", []) if isinstance(prev.get("changes", []), list) else []
            prev_files = {
                str(x.get("file", "") or "").strip()
                for x in prev_changes
                if isinstance(x, dict) and str(x.get("file", "") or "").strip()
            }
            if not merge_suggestion and len(current_files & prev_files) >= 2:
                merge_suggestion = True
                merge_with = prev_id
        proposal = {
            "proposal_id": proposal_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "scope": "mod_revision",
            "status": "pending",
            "target_mod_id": target_mod_id,
            "summary": str(parsed.get("summary", "") or "").strip() or "AI 生成修订提案",
            "risk_level": str(parsed.get("risk_level", "medium") or "medium"),
            "changes": filtered_changes[:8],
            "memory_candidates": memory_candidates[:10],
            "validator": {
                "schema_ok": schema_ok,
                "policy_ok": policy_ok,
                "blocked_rules": blocked_rules,
                "structured_count": structured_count,
                "total_changes": total_changes,
                "structured_ratio": round(structured_ratio, 4),
                "run_sample_count": run_count,
                "common_issues": common_issues,
                "duplicate_proposal": duplicate_proposal,
                "duplicate_with": duplicate_with,
                "merge_suggestion": merge_suggestion,
                "merge_with": merge_with,
            },
            "quality_score": quality_score,
            "priority": priority,
            "source_run": {
                "user_id": str(user_id),
                "turn_count": len(req.history or []),
            },
        }

        with with_user_write_lock(user_id):
            qdir = _revisions_queue_dir(user_id)
            os.makedirs(qdir, exist_ok=True)
            with open(os.path.join(qdir, f"{proposal_id}.json"), "w", encoding="utf-8") as f:
                json.dump(proposal, f, ensure_ascii=False, indent=2)
        append_audit_log(user_id, "agent_revision_propose", "ok", target_mod_id, {"proposal_id": proposal_id})
        return {"status": "success", "proposal": proposal}

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

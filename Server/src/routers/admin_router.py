from typing import Any, Callable, Dict, List
from datetime import datetime
import json
import os
import shutil
import threading
import time

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from src.core.config import DATA_ROOT


class AdminFileSaveReq(BaseModel):
    type: str
    name: str
    content: str

class AdminPresetFileSaveReq(BaseModel):
    target: str = "default"
    mod_id: str = ""
    type: str
    name: str
    content: str


class GenerateSkillPromptReq(BaseModel):
    concept: str


class AdminLoginReq(BaseModel):
    password: str


class EventSkeletonValidateReq(BaseModel):
    name: str = "event_skeletons.generated.json"
    content: str = ""
    rules: Dict[str, Any] = {}


class EventSkeletonPromoteReq(BaseModel):
    source_name: str = "event_skeletons.generated.json"
    target_name: str = "event_skeletons.json"
    content: str = ""
    allow_warnings: bool = True


class EventSkeletonRulesSaveReq(BaseModel):
    name: str = "event_skeleton_rules.json"
    rules: Dict[str, Any]


class RevisionDecisionReq(BaseModel):
    note: str = ""


class RevisionApplyMemoryReq(BaseModel):
    limit: int = 10


def build_admin_router(
    *,
    get_user_id,
    get_engine: Callable[[str], Any],
    get_user_prompts_dir: Callable[[str], str],
    get_user_events_dir: Callable[[str], str],
    get_user_library_dir: Callable[[str], str],
    default_prompts_dir: str,
    default_events_dir: str,
    with_user_write_lock: Callable[[str], Any],
    append_audit_log: Callable[[str, str, str, str, Dict[str, Any]], None],
    normalize_roster_single_player: Callable[[Dict[str, Any]], Dict[str, Any]],
    read_user_state: Callable[[str], Dict[str, Any]],
    write_user_state: Callable[[str, Dict[str, Any]], None],
    build_manifest: Callable[..., Dict[str, Any]],
    workshop_dir: str,
    admin_auth,
    require_admin,
    require_openclaw_bot=None,
):
    router = APIRouter()
    accounts_by_id_dir = os.path.join(DATA_ROOT, "accounts", "by_id")
    accounts_sessions_dir = os.path.join(DATA_ROOT, "accounts", "sessions")
    openclaw_rpm_limit = max(1, int(os.getenv("OPENCLAW_RPM_LIMIT", "60") or 60))
    _openclaw_rate_lock = threading.Lock()
    _openclaw_rate_hits: Dict[str, List[float]] = {}

    def _library_file_path(user_id: str, item_id: str) -> str:
        return os.path.join(get_user_library_dir(user_id), f"{item_id}.json")

    def _workshop_file_path(item_id: str) -> str:
        return os.path.join(workshop_dir, f"{item_id}.json")

    def _revisions_root(user_id: str) -> str:
        return os.path.join(DATA_ROOT, "users", str(user_id), "revisions")

    def _revisions_dir(user_id: str, status: str) -> str:
        return os.path.join(_revisions_root(user_id), status)

    def _revision_path(user_id: str, status: str, proposal_id: str) -> str:
        return os.path.join(_revisions_dir(user_id, status), f"{proposal_id}.json")

    def _load_revision(user_id: str, proposal_id: str):
        for st in ["queue", "applied", "rejected"]:
            p = _revision_path(user_id, st, proposal_id)
            if os.path.exists(p):
                return st, p, _read_json(p)
        return "", "", {}

    def _save_revision(user_id: str, status: str, proposal_id: str, data: Dict[str, Any]) -> str:
        p = _revision_path(user_id, status, proposal_id)
        _write_json(p, data)
        return p

    def _move_revision(user_id: str, from_status: str, to_status: str, proposal_id: str, data: Dict[str, Any]) -> None:
        src = _revision_path(user_id, from_status, proposal_id)
        dst = _save_revision(user_id, to_status, proposal_id, data)
        if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
            try:
                os.remove(src)
            except Exception:
                pass

    def _load_library_mod(user_id: str, mod_id: str) -> Dict[str, Any]:
        path = _library_file_path(user_id, mod_id)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="target mod not found in library")
        return _read_json(path)

    def _save_library_mod(user_id: str, mod_id: str, data: Dict[str, Any]) -> None:
        path = _library_file_path(user_id, mod_id)
        _write_json(path, data)

    def _read_json(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}

    def _write_json(path: str, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _safe_join(base_dir: str, rel_path: str) -> str:
        normalized = os.path.normpath(str(rel_path or "")).replace("\\", "/")
        if normalized.startswith("../") or normalized == ".." or os.path.isabs(normalized):
            raise HTTPException(status_code=400, detail="非法文件路径")
        full_path = os.path.abspath(os.path.join(base_dir, normalized))
        base_abs = os.path.abspath(base_dir)
        if not full_path.startswith(base_abs):
            raise HTTPException(status_code=400, detail="非法文件路径")
        return full_path

    def _editor_target(user_id: str) -> Dict[str, str]:
        st = read_user_state(user_id)
        return {
            "source": str(st.get("editor_source", "default") or "default"),
            "mod_id": str(st.get("editor_mod_id", "default") or "default"),
        }

    def _load_editor_content(user_id: str) -> Dict[str, Dict[str, str]]:
        target = _editor_target(user_id)
        if target["source"] == "library" and target["mod_id"] != "default":
            file_path = _library_file_path(user_id, target["mod_id"])
            if os.path.exists(file_path):
                data = _read_json(file_path)
                content = data.get("content", {})
                if isinstance(content, dict):
                    return {
                        "md": dict(content.get("md", {}) or {}),
                        "csv": dict(content.get("csv", {}) or {}),
                    }
        return {"md": {}, "csv": {}}

    def _sync_linked_workshop_if_needed(user_id: str, library_data: Dict[str, Any]) -> None:
        workshop_id = str(library_data.get("linked_workshop_id", "") or "").strip()
        if not workshop_id:
            return
        workshop_path = _workshop_file_path(workshop_id)
        if not os.path.exists(workshop_path):
            return
        workshop_data = _read_json(workshop_path)
        if str(workshop_data.get("owner_user_id", "")) != str(user_id):
            raise HTTPException(status_code=403, detail="无权更新该公开模组")
        content = library_data.get("content", {})
        workshop_data["name"] = library_data.get("name", workshop_data.get("name"))
        workshop_data["description"] = library_data.get("description", workshop_data.get("description"))
        workshop_data["content"] = content
        workshop_data["manifest"] = build_manifest(
            mod_id=workshop_id,
            name=workshop_data.get("name", workshop_id),
            author=workshop_data.get("author", library_data.get("author", "")),
            source="workshop",
            content=content,
        )
        workshop_data["updated_at"] = library_data.get("timestamp")
        _write_json(workshop_path, workshop_data)

    def _read_event_file_content(user_id: str, file_name: str) -> str:
        editor_content = _load_editor_content(user_id)
        csv_content = editor_content.get("csv", {}) if isinstance(editor_content, dict) else {}
        if isinstance(csv_content, dict) and file_name in csv_content:
            return str(csv_content.get(file_name) or "")
        file_path = os.path.join(default_events_dir, file_name)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _default_skeleton_rules() -> Dict[str, Any]:
        return {
            "key_min_options": 3,
            "warn_on_empty_title": True,
            "warn_on_legacy_flags": True,
            "warn_on_migration_notes": True,
            "require_reviewed_for_pass": False,
            "allowed_types": ["daily", "key"],
        }

    def _require_ops_actor(admin_session: Dict[str, Any], x_openclaw_token: str = Header(None)) -> Dict[str, Any]:
        if isinstance(admin_session, dict):
            return admin_session
        if require_openclaw_bot is not None:
            return admin_auth.require_openclaw_bot(x_openclaw_token)
        raise HTTPException(status_code=401, detail="需要管理员或 OpenClaw 运营凭证")

    def _enforce_openclaw_rate_limit(action: str) -> None:
        now = time.time()
        window = 60.0
        key = str(action or "default")
        with _openclaw_rate_lock:
            rows = _openclaw_rate_hits.get(key, [])
            rows = [ts for ts in rows if (now - ts) <= window]
            if len(rows) >= openclaw_rpm_limit:
                raise HTTPException(status_code=429, detail=f"openclaw rate limited: {openclaw_rpm_limit}/min")
            rows.append(now)
            _openclaw_rate_hits[key] = rows

    def _normalize_skeleton_rules(raw: Dict[str, Any]) -> Dict[str, Any]:
        base = _default_skeleton_rules()
        if not isinstance(raw, dict):
            return base
        out = dict(base)
        out["key_min_options"] = max(1, int(raw.get("key_min_options", base["key_min_options"]) or base["key_min_options"]))
        out["warn_on_empty_title"] = bool(raw.get("warn_on_empty_title", base["warn_on_empty_title"]))
        out["warn_on_legacy_flags"] = bool(raw.get("warn_on_legacy_flags", base["warn_on_legacy_flags"]))
        out["warn_on_migration_notes"] = bool(raw.get("warn_on_migration_notes", base["warn_on_migration_notes"]))
        out["require_reviewed_for_pass"] = bool(raw.get("require_reviewed_for_pass", base["require_reviewed_for_pass"]))
        allowed_types = raw.get("allowed_types", base["allowed_types"])
        if not isinstance(allowed_types, list) or not allowed_types:
            allowed_types = base["allowed_types"]
        out["allowed_types"] = [str(x).strip().lower() for x in allowed_types if str(x).strip()]
        if not out["allowed_types"]:
            out["allowed_types"] = base["allowed_types"]
        return out

    def _load_skeleton_rules(user_id: str, file_name: str = "event_skeleton_rules.json") -> Dict[str, Any]:
        raw = _read_event_file_content(user_id, file_name)
        if not raw:
            return _default_skeleton_rules()
        try:
            data = json.loads(raw)
            return _normalize_skeleton_rules(data if isinstance(data, dict) else {})
        except Exception:
            return _default_skeleton_rules()

    def _write_event_file_content(user_id: str, file_name: str, content: str) -> None:
        target = _editor_target(user_id)
        if target["source"] != "library" or target["mod_id"] == "default":
            raise HTTPException(status_code=400, detail="默认模组不可直接修改，请先另存到模组库")
        library_path = _library_file_path(user_id, target["mod_id"])
        if not os.path.exists(library_path):
            raise HTTPException(status_code=404, detail="当前编辑模组不存在")
        library_data = _read_json(library_path)
        payload_content = library_data.get("content", {})
        md_files = dict(payload_content.get("md", {}) or {})
        csv_files = dict(payload_content.get("csv", {}) or {})
        csv_files[file_name] = content
        library_data["content"] = {"md": md_files, "csv": csv_files}
        library_data["manifest"] = build_manifest(
            mod_id=str(library_data.get("id", target["mod_id"])),
            name=str(library_data.get("name", target["mod_id"])),
            author=str(library_data.get("author", f"User_{user_id[:4]}")),
            source="library",
            content=library_data["content"],
        )
        library_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _write_json(library_path, library_data)
        _sync_linked_workshop_if_needed(user_id, library_data)

    def _validate_event_skeleton_payload(payload: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        cfg = _normalize_skeleton_rules(rules)
        events = payload.get("events", []) if isinstance(payload, dict) else []
        if not isinstance(events, list):
            return {
                "ok": False,
                "summary": {"total_events": 0, "pending_review": 0, "error_count": 1, "warning_count": 0},
                "issues": [{"level": "error", "code": "schema.events_not_list", "message": "events 字段必须是数组"}],
                "checklist": [],
            }

        issues: List[Dict[str, Any]] = []
        checklist: List[Dict[str, Any]] = []
        pending_review = 0

        for idx, evt in enumerate(events):
            event_path = f"events[{idx}]"
            if not isinstance(evt, dict):
                issues.append(
                    {
                        "level": "error",
                        "code": "event.not_object",
                        "message": "事件项必须是对象",
                        "path": event_path,
                    }
                )
                continue

            evt_id = str(evt.get("id", "")).strip()
            title = str(evt.get("title", "")).strip()
            evt_type = str(evt.get("type", "")).strip().lower()
            triggers = evt.get("triggers", {})
            options = evt.get("options", [])
            meta = evt.get("meta", {}) if isinstance(evt.get("meta", {}), dict) else {}
            migration_notes = meta.get("migration_notes", [])
            reviewed = bool(meta.get("reviewed", False))
            item_warnings: List[str] = []
            item_errors: List[str] = []

            if not evt_id:
                item_errors.append("缺少 id")
            if evt_type not in set(cfg.get("allowed_types", ["daily", "key"])):
                item_errors.append(f"type 只能是 {', '.join(cfg.get('allowed_types', ['daily', 'key']))}")
            if not title and bool(cfg.get("warn_on_empty_title", True)):
                item_warnings.append("标题为空")
            if not isinstance(triggers, dict):
                item_errors.append("triggers 必须是对象")
            if evt_type == "key":
                if not isinstance(options, list):
                    item_errors.append("key 事件 options 必须是数组")
                elif len(options) < int(cfg.get("key_min_options", 3)):
                    item_warnings.append(f"key 事件 options 建议至少 {int(cfg.get('key_min_options', 3))} 个")

            if bool(cfg.get("warn_on_legacy_flags", True)) and isinstance(triggers, dict):
                flags = triggers.get("flags_all_true", [])
                if isinstance(flags, list) and any(str(x).startswith("legacy:") for x in flags):
                    item_warnings.append("包含 legacy flags 条件，建议人工改为正式触发字段")

            if bool(cfg.get("warn_on_migration_notes", True)) and isinstance(migration_notes, list) and migration_notes:
                item_warnings.append(f"含迁移备注 {len(migration_notes)} 条")
            if bool(cfg.get("require_reviewed_for_pass", False)) and not reviewed:
                item_errors.append("事件尚未标记 reviewed=true")

            needs_review = bool(item_warnings) or not reviewed
            if needs_review:
                pending_review += 1
                checklist.append(
                    {
                        "id": evt_id or event_path,
                        "title": title or evt_id or event_path,
                        "reviewed": reviewed,
                        "warnings": item_warnings,
                        "errors": item_errors,
                    }
                )

            for msg in item_errors:
                issues.append(
                    {
                        "level": "error",
                        "code": "event.invalid",
                        "message": msg,
                        "path": f"{event_path}.{evt_id or 'unknown'}",
                        "event_id": evt_id or "",
                    }
                )
            for msg in item_warnings:
                issues.append(
                    {
                        "level": "warning",
                        "code": "event.review",
                        "message": msg,
                        "path": f"{event_path}.{evt_id or 'unknown'}",
                        "event_id": evt_id or "",
                    }
                )

        error_count = len([x for x in issues if x.get("level") == "error"])
        warning_count = len([x for x in issues if x.get("level") == "warning"])
        return {
            "ok": error_count == 0,
            "rules": cfg,
            "summary": {
                "total_events": len(events),
                "pending_review": pending_review,
                "error_count": error_count,
                "warning_count": warning_count,
            },
            "issues": issues,
            "checklist": checklist,
        }

    @router.post("/api/admin/login")
    def admin_login(req: AdminLoginReq):
        session = admin_auth.login(req.password)
        return {"status": "success", "data": session}

    @router.get("/api/admin/session")
    def admin_session(admin_session: Dict[str, Any] = require_admin):
        return {"status": "success", "data": admin_session}

    @router.post("/api/admin/logout")
    def admin_logout(admin_session: Dict[str, Any] = require_admin):
        token = str(admin_session.get("token", "")).strip()
        admin_auth.revoke(token)
        return {"status": "success"}

    @router.get("/api/admin/users")
    def list_admin_users(
        q: str = "",
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 50,
        admin_session: Dict[str, Any] = require_admin,
    ):
        _ = admin_session
        rows = []
        if os.path.exists(accounts_by_id_dir):
            for file_name in os.listdir(accounts_by_id_dir):
                if not file_name.endswith(".json"):
                    continue
                file_path = os.path.join(accounts_by_id_dir, file_name)
                try:
                    account = _read_json(file_path)
                except Exception:
                    continue
                account_id = str(account.get("account_id", "") or "")
                username = str(account.get("username", "") or "")
                created_at = str(account.get("created_at", "") or "")
                updated_at = str(account.get("updated_at", "") or "")
                linked_visitor_ids = list(account.get("linked_visitor_ids", []) or [])
                rows.append(
                    {
                        "account_id": account_id,
                        "username": username,
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "linked_visitor_count": len(linked_visitor_ids),
                    }
                )

        query = str(q or "").strip().lower()
        if query:
            rows = [
                row
                for row in rows
                if query in str(row.get("username", "")).lower()
                or query in str(row.get("account_id", "")).lower()
            ]

        if sort_by not in {"updated_at", "created_at", "username"}:
            sort_by = "updated_at"
        reverse = str(sort_order or "desc").lower() != "asc"
        rows.sort(key=lambda row: str(row.get(sort_by, "")), reverse=reverse)

        safe_page_size = max(1, min(int(page_size or 50), 200))
        safe_page = max(1, int(page or 1))
        total = len(rows)
        total_pages = max(1, (total + safe_page_size - 1) // safe_page_size)
        if safe_page > total_pages:
            safe_page = total_pages
        start = (safe_page - 1) * safe_page_size
        end = start + safe_page_size
        page_rows = rows[start:end]
        return {
            "status": "success",
            "data": page_rows,
            "pagination": {
                "page": safe_page,
                "page_size": safe_page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": safe_page < total_pages,
                "has_prev": safe_page > 1,
            },
        }

    @router.get("/api/admin/users/stats")
    def admin_user_stats(admin_session: Dict[str, Any] = require_admin):
        _ = admin_session
        total_accounts = 0
        total_linked_visitors = 0
        if os.path.exists(accounts_by_id_dir):
            for file_name in os.listdir(accounts_by_id_dir):
                if not file_name.endswith(".json"):
                    continue
                file_path = os.path.join(accounts_by_id_dir, file_name)
                try:
                    account = _read_json(file_path)
                except Exception:
                    continue
                if account.get("account_id"):
                    total_accounts += 1
                    total_linked_visitors += len(list(account.get("linked_visitor_ids", []) or []))

        active_sessions = 0
        now = datetime.now()
        if os.path.exists(accounts_sessions_dir):
            for file_name in os.listdir(accounts_sessions_dir):
                if not file_name.endswith(".json"):
                    continue
                file_path = os.path.join(accounts_sessions_dir, file_name)
                try:
                    session = _read_json(file_path)
                    expires_at = datetime.fromisoformat(str(session.get("expires_at", "") or ""))
                except Exception:
                    continue
                if expires_at > now:
                    active_sessions += 1

        public_mods = 0
        unique_owners = set()
        if os.path.exists(workshop_dir):
            for file_name in os.listdir(workshop_dir):
                if not file_name.endswith(".json"):
                    continue
                file_path = os.path.join(workshop_dir, file_name)
                try:
                    data = _read_json(file_path)
                except Exception:
                    continue
                owner_user_id = str(data.get("owner_user_id", "") or "")
                visibility = str(data.get("visibility", "public") or "public")
                if visibility == "public":
                    public_mods += 1
                if owner_user_id:
                    unique_owners.add(owner_user_id)

        return {
            "status": "success",
            "data": {
                "total_accounts": total_accounts,
                "active_sessions": active_sessions,
                "total_linked_visitors": total_linked_visitors,
                "public_mods": public_mods,
                "workshop_owner_accounts": len(unique_owners),
            },
        }

    @router.get("/api/admin/files")
    def get_admin_files(user_id: str = get_user_id):
        """获取所有剧情配置文件列表"""
        editor_content = _load_editor_content(user_id)
        dirs_to_scan = [default_prompts_dir]
        md_files_set = set()
        for d in dirs_to_scan:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for file in files:
                        if file.endswith((".md", ".json", ".csv")):
                            rel_path = os.path.relpath(os.path.join(root, file), d).replace("\\", "/")
                            md_files_set.add(rel_path)
        for rel_path in (editor_content.get("md", {}) or {}).keys():
            md_files_set.add(str(rel_path).replace("\\", "/"))
        md_files = list(md_files_set)

        event_dirs = [default_events_dir]
        csv_files_set = set()
        for d in event_dirs:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for file in files:
                        if file.endswith((".csv", ".json")):
                            rel_path = os.path.relpath(os.path.join(root, file), d).replace("\\", "/")
                            csv_files_set.add(rel_path)
        for rel_path in (editor_content.get("csv", {}) or {}).keys():
            csv_files_set.add(str(rel_path).replace("\\", "/"))
        csv_files = list(csv_files_set)

        return {"status": "success", "md": sorted(md_files), "csv": sorted(csv_files)}

    @router.get("/api/admin/preset/mods")
    def list_admin_preset_mods(admin_session: Dict[str, Any] = require_admin):
        _ = admin_session
        rows: List[Dict[str, Any]] = []
        if not os.path.exists(workshop_dir):
            return {"status": "success", "data": rows}
        for file_name in sorted(os.listdir(workshop_dir)):
            if not file_name.endswith(".json"):
                continue
            file_path = os.path.join(workshop_dir, file_name)
            try:
                data = _read_json(file_path)
            except Exception:
                continue
            source_type = str(data.get("source_type", "") or "")
            if source_type not in {"original", "official"}:
                continue
            rows.append(
                {
                    "id": str(data.get("id", file_name.replace(".json", "")) or file_name.replace(".json", "")),
                    "name": str(data.get("name", "") or ""),
                    "description": str(data.get("description", "") or ""),
                    "source_type": source_type,
                    "updated_at": str(data.get("updated_at", "") or ""),
                }
            )
        return {"status": "success", "data": rows}

    @router.get("/api/admin/preset/files")
    def get_admin_preset_files(
        target: str = "default",
        mod_id: str = "",
        admin_session: Dict[str, Any] = require_admin,
    ):
        _ = admin_session
        safe_target = str(target or "default").strip().lower()
        if safe_target == "default":
            md_files_set = set()
            if os.path.exists(default_prompts_dir):
                for root, _, files in os.walk(default_prompts_dir):
                    for file in files:
                        if file.endswith((".md", ".json", ".csv")):
                            rel_path = os.path.relpath(os.path.join(root, file), default_prompts_dir).replace("\\", "/")
                            md_files_set.add(rel_path)
            csv_files_set = set()
            if os.path.exists(default_events_dir):
                for root, _, files in os.walk(default_events_dir):
                    for file in files:
                        if file.endswith((".csv", ".json")):
                            rel_path = os.path.relpath(os.path.join(root, file), default_events_dir).replace("\\", "/")
                            csv_files_set.add(rel_path)
            return {"status": "success", "md": sorted(list(md_files_set)), "csv": sorted(list(csv_files_set))}
        if safe_target != "preset":
            raise HTTPException(status_code=400, detail="target 必须是 default 或 preset")
        safe_mod_id = str(mod_id or "").strip()
        if not safe_mod_id:
            raise HTTPException(status_code=400, detail="缺少 mod_id")
        preset_path = _workshop_file_path(safe_mod_id)
        if not os.path.exists(preset_path):
            raise HTTPException(status_code=404, detail="预设模组不存在")
        preset_data = _read_json(preset_path)
        content = preset_data.get("content", {})
        md_files = sorted(list((content.get("md", {}) or {}).keys()))
        csv_files = sorted(list((content.get("csv", {}) or {}).keys()))
        return {"status": "success", "md": md_files, "csv": csv_files}

    @router.get("/api/admin/preset/file")
    def read_admin_preset_file(
        target: str = "default",
        mod_id: str = "",
        type: str = "md",
        name: str = "",
        admin_session: Dict[str, Any] = require_admin,
    ):
        _ = admin_session
        safe_type = "md" if str(type or "md").strip().lower() == "md" else "csv"
        safe_name = str(name or "").strip()
        if not safe_name:
            raise HTTPException(status_code=400, detail="缺少 name")
        safe_target = str(target or "default").strip().lower()
        if safe_target == "default":
            base = default_prompts_dir if safe_type == "md" else default_events_dir
            file_path = _safe_join(base, safe_name)
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
            with open(file_path, "r", encoding="utf-8") as f:
                return {"status": "success", "content": f.read()}
        if safe_target != "preset":
            raise HTTPException(status_code=400, detail="target 必须是 default 或 preset")
        safe_mod_id = str(mod_id or "").strip()
        if not safe_mod_id:
            raise HTTPException(status_code=400, detail="缺少 mod_id")
        preset_path = _workshop_file_path(safe_mod_id)
        if not os.path.exists(preset_path):
            raise HTTPException(status_code=404, detail="预设模组不存在")
        preset_data = _read_json(preset_path)
        content = preset_data.get("content", {})
        bucket = content.get("md", {}) if safe_type == "md" else content.get("csv", {})
        if safe_name not in bucket:
            raise HTTPException(status_code=404, detail="File not found")
        return {"status": "success", "content": str(bucket.get(safe_name) or "")}

    @router.post("/api/admin/preset/file")
    def save_admin_preset_file(
        req: AdminPresetFileSaveReq,
        admin_session: Dict[str, Any] = require_admin,
    ):
        _ = admin_session
        safe_target = str(req.target or "default").strip().lower()
        safe_type = "md" if str(req.type or "md").strip().lower() == "md" else "csv"
        safe_name = str(req.name or "").strip()
        if not safe_name:
            raise HTTPException(status_code=400, detail="缺少 name")
        content_to_write = req.content
        if safe_type == "md" and safe_name.endswith("roster.json"):
            parsed = json.loads(req.content)
            parsed = normalize_roster_single_player(parsed)
            content_to_write = json.dumps(parsed, ensure_ascii=False, indent=4)
        if safe_target == "default":
            base = default_prompts_dir if safe_type == "md" else default_events_dir
            file_path = _safe_join(base, safe_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content_to_write)
            return {"status": "success", "message": f"default:{safe_name} 保存成功"}
        if safe_target != "preset":
            raise HTTPException(status_code=400, detail="target 必须是 default 或 preset")
        safe_mod_id = str(req.mod_id or "").strip()
        if not safe_mod_id:
            raise HTTPException(status_code=400, detail="缺少 mod_id")
        preset_path = _workshop_file_path(safe_mod_id)
        if not os.path.exists(preset_path):
            raise HTTPException(status_code=404, detail="预设模组不存在")
        preset_data = _read_json(preset_path)
        mod_content = preset_data.get("content", {})
        md_files = dict(mod_content.get("md", {}) or {})
        csv_files = dict(mod_content.get("csv", {}) or {})
        if safe_type == "md":
            md_files[safe_name] = content_to_write
        else:
            csv_files[safe_name] = content_to_write
        preset_data["content"] = {"md": md_files, "csv": csv_files}
        preset_data["manifest"] = build_manifest(
            mod_id=safe_mod_id,
            name=str(preset_data.get("name", safe_mod_id)),
            author=str(preset_data.get("author", "official")),
            source="workshop",
            content=preset_data["content"],
        )
        preset_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _write_json(preset_path, preset_data)
        return {"status": "success", "message": f"preset:{safe_mod_id}:{safe_name} 保存成功"}

    @router.get("/api/admin/file")
    def read_admin_file(type: str, name: str, user_id: str = get_user_id):
        """读取单个文件内容"""
        editor_content = _load_editor_content(user_id)
        content_group = "md" if type == "md" else "csv"
        if name in editor_content.get(content_group, {}):
            return {"status": "success", "content": editor_content[content_group][name]}

        default_base = default_prompts_dir if type == "md" else default_events_dir
        file_path = os.path.join(default_base, name)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        with open(file_path, "r", encoding="utf-8") as f:
            return {"status": "success", "content": f.read()}

    @router.post("/api/admin/file")
    def save_admin_file(req: AdminFileSaveReq, user_id: str = get_user_id):
        """保存单个文件内容到当前选中的本地模组；默认模组只读。"""
        try:
            with with_user_write_lock(user_id):
                target = _editor_target(user_id)
                if target["source"] != "library" or target["mod_id"] == "default":
                    raise HTTPException(status_code=400, detail="默认模组不可直接修改，请先另存到模组库")
                library_path = _library_file_path(user_id, target["mod_id"])
                if not os.path.exists(library_path):
                    raise HTTPException(status_code=404, detail="当前编辑模组不存在")
                library_data = _read_json(library_path)
                content = library_data.get("content", {})
                md_files = dict(content.get("md", {}) or {})
                csv_files = dict(content.get("csv", {}) or {})
                content_to_write = req.content
                if req.type == "md" and req.name.endswith("roster.json"):
                    parsed = json.loads(req.content)
                    parsed = normalize_roster_single_player(parsed)
                    content_to_write = json.dumps(parsed, ensure_ascii=False, indent=4)
                if req.type == "md":
                    md_files[req.name] = content_to_write
                else:
                    csv_files[req.name] = content_to_write
                library_data["content"] = {"md": md_files, "csv": csv_files}
                library_data["manifest"] = build_manifest(
                    mod_id=str(library_data.get("id", target["mod_id"])),
                    name=str(library_data.get("name", target["mod_id"])),
                    author=str(library_data.get("author", f"User_{user_id[:4]}")),
                    source="library",
                    content=library_data["content"],
                )
                library_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _write_json(library_path, library_data)
                _sync_linked_workshop_if_needed(user_id, library_data)

                if req.type == "md" and req.name.endswith("roster.json"):
                    engine = get_engine(user_id)
                    if engine:
                        if hasattr(engine, "pm"):
                            engine.pm = type(engine.pm)(user_id)
                        if hasattr(engine, "player_name"):
                            engine.player_name = engine.pm.get_player_name() if hasattr(engine.pm, "get_player_name") else engine.player_name
                        if hasattr(engine, "tm") and hasattr(engine.tm, "set_player_name") and hasattr(engine, "player_name"):
                            engine.tm.set_player_name(engine.player_name)
            append_audit_log(user_id, "save_admin_file", "ok", f"{req.type}:{req.name}", {})
            return {"status": "success", "message": f"{req.name} 保存成功"}
        except HTTPException as e:
            append_audit_log(user_id, "save_admin_file", "error", f"{req.type}:{req.name}", {"error": str(e.detail)})
            raise
        except Exception as e:
            append_audit_log(user_id, "save_admin_file", "error", f"{req.type}:{req.name}", {"error": str(e)})
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/admin/upload_portrait")
    async def upload_portrait(file: UploadFile = File(...)):
        """上传角色立绘图片"""
        portraits_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "WebClient",
            "public",
            "assets",
            "portraits",
        )
        if not os.path.exists(portraits_dir):
            os.makedirs(portraits_dir, exist_ok=True)

        if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            raise HTTPException(status_code=400, detail="Only images are allowed")

        file_path = os.path.join(portraits_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"status": "success", "url": f"/assets/portraits/{file.filename}"}

    @router.post("/api/admin/generate_skill_prompt")
    def generate_skill_prompt(req: GenerateSkillPromptReq, user_id: str = get_user_id):
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
                {"role": "user", "content": user_prompt},
            ]
            completion = engine.llm.client.chat.completions.create(
                model=engine.llm.model,
                messages=messages,
                temperature=0.8,
                max_tokens=1500,
            )
            content = completion.choices[0].message.content
            return {"status": "success", "prompt": content}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)}")

    @router.post("/api/admin/event_skeletons/validate")
    def validate_event_skeletons(req: EventSkeletonValidateReq, user_id: str = get_user_id):
        raw = str(req.content or "").strip()
        if not raw:
            raw = _read_event_file_content(user_id, req.name)
        if not raw:
            raise HTTPException(status_code=404, detail=f"未找到骨架文件: {req.name}")
        try:
            payload = json.loads(raw)
        except Exception:
            raise HTTPException(status_code=400, detail="骨架文件不是合法 JSON")
        use_rules = req.rules if isinstance(req.rules, dict) and req.rules else _load_skeleton_rules(user_id)
        result = _validate_event_skeleton_payload(payload if isinstance(payload, dict) else {}, use_rules)
        return {"status": "success", "data": result}

    @router.post("/api/admin/event_skeletons/promote")
    def promote_event_skeletons(req: EventSkeletonPromoteReq, user_id: str = get_user_id):
        source_name = str(req.source_name or "event_skeletons.generated.json").strip() or "event_skeletons.generated.json"
        target_name = str(req.target_name or "event_skeletons.json").strip() or "event_skeletons.json"
        raw = str(req.content or "").strip()
        if not raw:
            raw = _read_event_file_content(user_id, source_name)
        if not raw:
            raise HTTPException(status_code=404, detail=f"未找到骨架草稿文件: {source_name}")
        try:
            payload = json.loads(raw)
        except Exception:
            raise HTTPException(status_code=400, detail="骨架草稿不是合法 JSON")

        validate = _validate_event_skeleton_payload(payload if isinstance(payload, dict) else {}, _load_skeleton_rules(user_id))
        summary = validate.get("summary", {})
        errors = int(summary.get("error_count", 0) or 0)
        warnings = int(summary.get("warning_count", 0) or 0)
        if errors > 0:
            raise HTTPException(status_code=400, detail=f"校验失败：存在 {errors} 个错误，无法发布正式骨架")
        if warnings > 0 and not bool(req.allow_warnings):
            raise HTTPException(status_code=400, detail=f"校验存在 {warnings} 个警告，未允许带警告发布")

        now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{target_name}.bak.{now_tag}"
        target_prev = _read_event_file_content(user_id, target_name)

        with with_user_write_lock(user_id):
            if target_prev.strip():
                _write_event_file_content(user_id, backup_name, target_prev)
            _write_event_file_content(user_id, target_name, json.dumps(payload, ensure_ascii=False, indent=2))

        append_audit_log(
            user_id,
            "promote_event_skeletons",
            "ok",
            f"{source_name}->{target_name}",
            {"errors": errors, "warnings": warnings, "backup": backup_name if target_prev.strip() else ""},
        )
        return {
            "status": "success",
            "data": {
                "source_name": source_name,
                "target_name": target_name,
                "backup_name": backup_name if target_prev.strip() else "",
                "summary": summary,
                "message": "骨架正式发布成功",
            },
        }

    @router.get("/api/admin/event_skeletons/rules")
    def get_event_skeleton_rules(name: str = "event_skeleton_rules.json", user_id: str = get_user_id):
        rules = _load_skeleton_rules(user_id, file_name=name)
        return {"status": "success", "data": {"name": name, "rules": rules}}

    @router.post("/api/admin/event_skeletons/rules")
    def save_event_skeleton_rules(req: EventSkeletonRulesSaveReq, user_id: str = get_user_id):
        normalized = _normalize_skeleton_rules(req.rules if isinstance(req.rules, dict) else {})
        with with_user_write_lock(user_id):
            _write_event_file_content(user_id, req.name, json.dumps(normalized, ensure_ascii=False, indent=2))
        append_audit_log(
            user_id,
            "save_event_skeleton_rules",
            "ok",
            req.name,
            {"rules_keys": list(normalized.keys())},
        )
        return {"status": "success", "data": {"name": req.name, "rules": normalized}}

    @router.get("/api/admin/skills/snapshot")
    def export_skill_snapshot(
        download: bool = False,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        engine = get_engine(user_id)
        pm = getattr(engine, "pm", None) if engine else None

        enabled_skills: List[str] = []
        all_skills: List[str] = []
        phone_system_enabled = True
        if pm is not None:
            try:
                enabled_skills = list(pm.get_enabled_skills()) if hasattr(pm, "get_enabled_skills") else []
            except Exception:
                enabled_skills = []
            try:
                all_skills = sorted(list(getattr(pm, "skills", {}).keys()))
            except Exception:
                all_skills = []
            try:
                phone_system_enabled = bool(pm.is_phone_system_enabled()) if hasattr(pm, "is_phone_system_enabled") else True
            except Exception:
                phone_system_enabled = True

        target = _editor_target(user_id)
        state = read_user_state(user_id)
        snapshot = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "user_id": str(user_id),
            "editor_target": target,
            "active_mod_id": str(state.get("mod_id", "") or ""),
            "phone_system_enabled": phone_system_enabled,
            "enabled_skills": enabled_skills,
            "all_skills": all_skills,
            "skill_count": len(enabled_skills),
        }
        if download:
            body = json.dumps(snapshot, ensure_ascii=False, indent=2)
            return Response(
                content=body,
                media_type="application/json; charset=utf-8",
                headers={"Content-Disposition": "attachment; filename=skill_snapshot.json"},
            )
        return {"status": "success", "data": snapshot}

    @router.get("/api/admin/skills/catalog")
    def get_skill_catalog(
        active_only: bool = False,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        engine = get_engine(user_id)
        pm = getattr(engine, "pm", None) if engine else None
        items: List[Dict[str, Any]] = []
        if pm is not None and hasattr(pm, "get_user_skill_catalog"):
            try:
                rows = pm.get_user_skill_catalog({}) or []
                for row in rows:
                    item = {
                        "id": str(row.get("id", "")),
                        "name": str(row.get("name", "")),
                        "description": str(row.get("description", "")),
                        "file_path": str(row.get("file_path", "")),
                        "enabled": bool(row.get("enabled", True)),
                        "when": str(row.get("when", "always")),
                        "target": str(row.get("target", "")),
                        "priority": int(row.get("priority", 100) or 100),
                        "tags": row.get("tags") if isinstance(row.get("tags"), list) else [],
                        "active": bool(row.get("active", True)),
                    }
                    if active_only and not item["active"]:
                        continue
                    items.append(item)
            except Exception:
                items = []
        return {"status": "success", "data": {"count": len(items), "items": items}}

    @router.get("/api/admin/revisions")
    def list_revisions(
        status: str = "queue",
        limit: int = 50,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        s = str(status or "queue").strip()
        if s not in {"queue", "applied", "rejected"}:
            s = "queue"
        d = _revisions_dir(user_id, s)
        if not os.path.exists(d):
            return {"status": "success", "data": {"items": [], "count": 0}}
        rows: List[Dict[str, Any]] = []
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(d, fn)
            try:
                row = _read_json(path)
            except Exception:
                continue
            rows.append(
                {
                    "proposal_id": str(row.get("proposal_id", "") or "").strip() or fn[:-5],
                    "created_at": str(row.get("created_at", "")),
                    "status": str(row.get("status", s)),
                    "target_mod_id": str(row.get("target_mod_id", "")),
                    "summary": str(row.get("summary", "")),
                    "risk_level": str(row.get("risk_level", "medium")),
                    "changes_count": len(row.get("changes", []) if isinstance(row.get("changes", []), list) else []),
                    "memory_candidates_count": len(row.get("memory_candidates", []) if isinstance(row.get("memory_candidates", []), list) else []),
                    "quality_score": int(row.get("quality_score", 0) or 0),
                    "priority": str(row.get("priority", "medium") or "medium"),
                    "validator": row.get("validator", {}) if isinstance(row.get("validator", {}), dict) else {},
                }
            )
        rows.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        lim = max(1, min(int(limit or 50), 200))
        return {"status": "success", "data": {"items": rows[:lim], "count": len(rows)}}

    @router.get("/api/openclaw/session")
    def openclaw_session(openclaw_session: Dict[str, Any] = require_openclaw_bot):
        if not isinstance(openclaw_session, dict):
            raise HTTPException(status_code=401, detail="OpenClaw token 无效")
        return {"status": "success", "data": openclaw_session}

    @router.get("/api/openclaw/revisions")
    def list_revisions_for_openclaw(
        status: str = "queue",
        limit: int = 50,
        openclaw_session: Dict[str, Any] = require_openclaw_bot,
        user_id: str = get_user_id,
    ):
        _ = openclaw_session
        _enforce_openclaw_rate_limit("list_revisions")
        s = str(status or "queue").strip()
        if s not in {"queue", "applied", "rejected"}:
            s = "queue"
        d = _revisions_dir(user_id, s)
        if not os.path.exists(d):
            return {"status": "success", "data": {"items": [], "count": 0}}
        rows: List[Dict[str, Any]] = []
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(d, fn)
            try:
                row = _read_json(path)
            except Exception:
                continue
            rows.append(
                {
                    "proposal_id": str(row.get("proposal_id", "") or "").strip() or fn[:-5],
                    "created_at": str(row.get("created_at", "")),
                    "status": str(row.get("status", s)),
                    "target_mod_id": str(row.get("target_mod_id", "")),
                    "summary": str(row.get("summary", "")),
                    "risk_level": str(row.get("risk_level", "medium")),
                    "changes_count": len(row.get("changes", []) if isinstance(row.get("changes", []), list) else []),
                    "memory_candidates_count": len(row.get("memory_candidates", []) if isinstance(row.get("memory_candidates", []), list) else []),
                    "quality_score": int(row.get("quality_score", 0) or 0),
                    "priority": str(row.get("priority", "medium") or "medium"),
                    "validator": row.get("validator", {}) if isinstance(row.get("validator", {}), dict) else {},
                }
            )
        rows.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        lim = max(1, min(int(limit or 50), 200))
        return {"status": "success", "data": {"items": rows[:lim], "count": len(rows)}}

    @router.get("/api/openclaw/revisions/{proposal_id}")
    def get_revision_detail_for_openclaw(
        proposal_id: str,
        openclaw_session: Dict[str, Any] = require_openclaw_bot,
        user_id: str = get_user_id,
    ):
        _ = openclaw_session
        _enforce_openclaw_rate_limit("get_revision_detail")
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        return {"status": "success", "data": data, "bucket": st}

    @router.get("/api/admin/revisions/{proposal_id}")
    def get_revision_detail(
        proposal_id: str,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        return {"status": "success", "data": data, "bucket": st}

    @router.post("/api/admin/revisions/{proposal_id}/approve")
    def approve_revision(
        proposal_id: str,
        req: RevisionDecisionReq,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        data["status"] = "approved"
        data["approved_at"] = datetime.now().isoformat(timespec="seconds")
        data["approved_note"] = str(req.note or "")
        _move_revision(user_id, st, "applied", proposal_id, data)
        append_audit_log(user_id, "agent_revision_approve", "ok", proposal_id, {"note": req.note or ""})
        return {"status": "success", "data": {"proposal_id": proposal_id, "status": "approved"}}

    @router.post("/api/admin/revisions/{proposal_id}/reject")
    def reject_revision(
        proposal_id: str,
        req: RevisionDecisionReq,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        data["status"] = "rejected"
        data["rejected_at"] = datetime.now().isoformat(timespec="seconds")
        data["rejected_note"] = str(req.note or "")
        _move_revision(user_id, st, "rejected", proposal_id, data)
        append_audit_log(user_id, "agent_revision_reject", "ok", proposal_id, {"note": req.note or ""})
        return {"status": "success", "data": {"proposal_id": proposal_id, "status": "rejected"}}

    @router.post("/api/openclaw/revisions/{proposal_id}/approve")
    def approve_revision_for_openclaw(
        proposal_id: str,
        req: RevisionDecisionReq,
        x_request_id: str = Header(None),
        openclaw_session: Dict[str, Any] = require_openclaw_bot,
        user_id: str = get_user_id,
    ):
        _ = openclaw_session
        _enforce_openclaw_rate_limit("approve_revision")
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        data["status"] = "approved"
        data["approved_at"] = datetime.now().isoformat(timespec="seconds")
        data["approved_note"] = str(req.note or "")
        data["approved_by"] = "openclaw_bot"
        data["request_id"] = str(x_request_id or "").strip()
        _move_revision(user_id, st, "applied", proposal_id, data)
        append_audit_log(
            user_id,
            "openclaw_revision_approve",
            "ok",
            proposal_id,
            {
                "note": req.note or "",
                "actor_type": "bot",
                "actor_id": "openclaw_bot",
                "request_id": str(x_request_id or "").strip(),
            },
        )
        return {"status": "success", "data": {"proposal_id": proposal_id, "status": "approved"}}

    @router.post("/api/openclaw/revisions/{proposal_id}/reject")
    def reject_revision_for_openclaw(
        proposal_id: str,
        req: RevisionDecisionReq,
        x_request_id: str = Header(None),
        openclaw_session: Dict[str, Any] = require_openclaw_bot,
        user_id: str = get_user_id,
    ):
        _ = openclaw_session
        _enforce_openclaw_rate_limit("reject_revision")
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        data["status"] = "rejected"
        data["rejected_at"] = datetime.now().isoformat(timespec="seconds")
        data["rejected_note"] = str(req.note or "")
        data["rejected_by"] = "openclaw_bot"
        data["request_id"] = str(x_request_id or "").strip()
        _move_revision(user_id, st, "rejected", proposal_id, data)
        append_audit_log(
            user_id,
            "openclaw_revision_reject",
            "ok",
            proposal_id,
            {
                "note": req.note or "",
                "actor_type": "bot",
                "actor_id": "openclaw_bot",
                "request_id": str(x_request_id or "").strip(),
            },
        )
        return {"status": "success", "data": {"proposal_id": proposal_id, "status": "rejected"}}

    @router.post("/api/admin/revisions/{proposal_id}/apply_memory")
    def apply_revision_memory(
        proposal_id: str,
        req: RevisionApplyMemoryReq,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        if str(data.get("status", "")).lower() not in {"approved", "applied"}:
            raise HTTPException(status_code=400, detail="proposal must be approved before apply_memory")

        engine = get_engine(user_id)
        if not engine or not hasattr(engine, "mm") or not hasattr(engine.mm, "vector_store"):
            raise HTTPException(status_code=503, detail="memory engine unavailable")

        target_mod_id = str(data.get("target_mod_id", "") or "").strip()
        if not target_mod_id:
            raise HTTPException(status_code=400, detail="target_mod_id missing")

        from src.models.schema import MemoryItem  # lazy import
        import uuid

        candidates = data.get("memory_candidates", [])
        if not isinstance(candidates, list):
            candidates = []
        lim = max(1, min(int(req.limit or 10), 50))
        payload = []
        for item in candidates[:lim]:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", "") or "").strip()
            if not content:
                continue
            importance = int(item.get("importance", 6) or 6)
            importance = max(1, min(10, importance))
            payload.append(
                MemoryItem(
                    id=str(uuid.uuid4()),
                    type="mod_long_term",
                    content=content,
                    summary=content[:120],
                    importance=importance,
                    related_entities=[target_mod_id],
                )
            )
        if payload:
            engine.mm.vector_store.add_memories(payload, save_id=f"mod:{target_mod_id}")
        data["memory_applied_at"] = datetime.now().isoformat(timespec="seconds")
        data["memory_applied_count"] = len(payload)
        _save_revision(user_id, st, proposal_id, data)
        append_audit_log(
            user_id,
            "agent_revision_apply_memory",
            "ok",
            proposal_id,
            {"count": len(payload), "target_mod_id": target_mod_id},
        )
        return {"status": "success", "data": {"proposal_id": proposal_id, "applied_count": len(payload)}}

    @router.post("/api/admin/revisions/{proposal_id}/apply_to_draft")
    def apply_revision_to_draft(
        proposal_id: str,
        req: RevisionDecisionReq,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        if str(data.get("status", "")).lower() not in {"approved", "applied"}:
            raise HTTPException(status_code=400, detail="proposal must be approved before apply_to_draft")
        validator = data.get("validator", {}) if isinstance(data.get("validator", {}), dict) else {}
        blocked_rules = validator.get("blocked_rules", []) if isinstance(validator.get("blocked_rules", []), list) else []
        quality_score = int(data.get("quality_score", 0) or 0)
        run_samples = int(validator.get("run_sample_count", 0) or 0)
        allow_override = "force_apply" in str(req.note or "").lower()
        if (quality_score < 50 or run_samples < 2 or "insufficient_run_samples" in blocked_rules) and not allow_override:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"proposal blocked by quality gate: quality={quality_score}, samples={run_samples}. "
                    "如需强制应用，请在备注中包含 force_apply。"
                ),
            )

        target_mod_id = str(data.get("target_mod_id", "") or "").strip()
        if not target_mod_id or target_mod_id == "default":
            raise HTTPException(status_code=400, detail="invalid target_mod_id")

        mod_data = _load_library_mod(user_id, target_mod_id)
        content = mod_data.get("content", {}) if isinstance(mod_data.get("content", {}), dict) else {}
        md_files = dict(content.get("md", {}) or {})
        csv_files = dict(content.get("csv", {}) or {})

        changes = data.get("changes", [])
        if not isinstance(changes, list) or not changes:
            raise HTTPException(status_code=400, detail="no changes to apply")

        backup_rows: List[Dict[str, Any]] = []
        applied = 0
        skipped_legacy = 0
        for item in changes:
            if not isinstance(item, dict):
                continue
            file_name = str(item.get("file", "") or "").strip()
            op = str(item.get("op", "update") or "update").strip().lower()
            content_after = str(item.get("content_after", "") or "").strip()
            if op != "update":
                continue
            if not file_name.startswith(("prompts/", "events/")):
                continue

            if file_name.startswith("prompts/"):
                rel = file_name[len("prompts/"):].strip()
                if not rel:
                    continue
                old_val = str(md_files.get(rel, "") or "")
                backup_rows.append({"file": file_name, "old_content": old_val})
                if content_after:
                    md_files[rel] = content_after
                else:
                    skipped_legacy += 1
                    continue
                applied += 1
            elif file_name.startswith("events/"):
                rel = file_name[len("events/"):].strip()
                if not rel:
                    continue
                old_val = str(csv_files.get(rel, "") or "")
                backup_rows.append({"file": file_name, "old_content": old_val})
                if content_after:
                    csv_files[rel] = content_after
                else:
                    skipped_legacy += 1
                    continue
                applied += 1

        if applied <= 0:
            raise HTTPException(status_code=400, detail="no applicable changes")

        mod_data["content"] = {"md": md_files, "csv": csv_files}
        mod_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mod_data["manifest"] = build_manifest(
            mod_id=str(mod_data.get("id", target_mod_id)),
            name=str(mod_data.get("name", target_mod_id)),
            author=str(mod_data.get("author", f"User_{str(user_id)[:4]}")),
            source="library",
            content=mod_data["content"],
        )
        _save_library_mod(user_id, target_mod_id, mod_data)

        data["draft_applied_at"] = datetime.now().isoformat(timespec="seconds")
        data["draft_applied_note"] = str(req.note or "")
        data["draft_applied_count"] = applied
        data["draft_backup"] = {
            "target_mod_id": target_mod_id,
            "files": backup_rows[:50],
        }
        _save_revision(user_id, st, proposal_id, data)
        append_audit_log(
            user_id,
            "agent_revision_apply_to_draft",
            "ok",
            proposal_id,
            {"target_mod_id": target_mod_id, "applied": applied},
        )
        return {
            "status": "success",
            "data": {
                "proposal_id": proposal_id,
                "applied": applied,
                "skipped_without_content_after": skipped_legacy,
                "target_mod_id": target_mod_id,
            },
        }

    @router.post("/api/admin/revisions/{proposal_id}/rollback")
    def rollback_revision_apply(
        proposal_id: str,
        req: RevisionDecisionReq,
        admin_session: Dict[str, Any] = require_admin,
        user_id: str = get_user_id,
    ):
        _ = admin_session
        st, _, data = _load_revision(user_id, proposal_id)
        if not st:
            raise HTTPException(status_code=404, detail="proposal not found")
        backup = data.get("draft_backup", {}) if isinstance(data.get("draft_backup", {}), dict) else {}
        target_mod_id = str(backup.get("target_mod_id", "") or "").strip()
        files = backup.get("files", []) if isinstance(backup.get("files", []), list) else []
        if not target_mod_id or not files:
            raise HTTPException(status_code=400, detail="no draft backup to rollback")

        mod_data = _load_library_mod(user_id, target_mod_id)
        content = mod_data.get("content", {}) if isinstance(mod_data.get("content", {}), dict) else {}
        md_files = dict(content.get("md", {}) or {})
        csv_files = dict(content.get("csv", {}) or {})

        restored = 0
        for item in files:
            if not isinstance(item, dict):
                continue
            file_name = str(item.get("file", "") or "").strip()
            old_content = str(item.get("old_content", "") or "")
            if file_name.startswith("prompts/"):
                rel = file_name[len("prompts/"):].strip()
                if not rel:
                    continue
                md_files[rel] = old_content
                restored += 1
            elif file_name.startswith("events/"):
                rel = file_name[len("events/"):].strip()
                if not rel:
                    continue
                csv_files[rel] = old_content
                restored += 1

        if restored <= 0:
            raise HTTPException(status_code=400, detail="rollback restored 0 files")

        mod_data["content"] = {"md": md_files, "csv": csv_files}
        mod_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mod_data["manifest"] = build_manifest(
            mod_id=str(mod_data.get("id", target_mod_id)),
            name=str(mod_data.get("name", target_mod_id)),
            author=str(mod_data.get("author", f"User_{str(user_id)[:4]}")),
            source="library",
            content=mod_data["content"],
        )
        _save_library_mod(user_id, target_mod_id, mod_data)

        data["rollback_at"] = datetime.now().isoformat(timespec="seconds")
        data["rollback_note"] = str(req.note or "")
        data["rollback_count"] = restored
        _save_revision(user_id, st, proposal_id, data)
        append_audit_log(
            user_id,
            "agent_revision_rollback",
            "ok",
            proposal_id,
            {"target_mod_id": target_mod_id, "restored": restored},
        )
        return {"status": "success", "data": {"proposal_id": proposal_id, "restored": restored, "target_mod_id": target_mod_id}}

    return router

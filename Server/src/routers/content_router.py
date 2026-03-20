from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import json
import os
import shutil

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class LibrarySaveReq(BaseModel):
    name: str
    description: str


class StorageCleanupReq(BaseModel):
    dry_run: bool = True
    keep_recent_library: int = 100
    keep_recent_snapshots: int = 20


class WorkshopPublishReq(BaseModel):
    name: str
    author: str
    description: str


class WorkshopUpdateReq(BaseModel):
    name: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None


def build_content_router(
    *,
    get_user_id,
    get_engine: Callable[[str], Any],
    get_user_library_dir: Callable[[str], str],
    get_user_data_root: Callable[[str], str],
    with_user_write_lock: Callable[[str], Any],
    append_audit_log: Callable[[str, str, str, str, Dict[str, Any]], None],
    package_mod: Callable[[str], Dict[str, Dict[str, str]]],
    build_validation_report: Callable[[dict, Optional[dict]], Dict[str, Any]],
    validate_mod_content: Callable[[dict, Optional[dict]], Dict[str, Any]],
    apply_mod_content_atomic: Callable[[str, dict], None],
    read_user_state: Callable[[str], Dict[str, Any]],
    write_user_state: Callable[[str, Dict[str, Any]], None],
    get_storage_quota_data: Callable[[str], Dict[str, Any]],
    cleanup_user_storage: Callable[..., Dict[str, Any]],
    list_snapshots: Callable[[str], List[Dict[str, Any]]],
    load_snapshot: Callable[[str, str], Dict[str, Any]],
    create_snapshot: Callable[..., Dict[str, Any]],
    trim_snapshots: Callable[..., None],
    build_manifest: Callable[..., Dict[str, Any]],
    max_library_items: int,
    max_library_total_bytes: int,
    max_snapshots_keep: int,
    workshop_dir: str,
    require_admin=None,
):
    router = APIRouter()

    def _now_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _library_file_path(user_id: str, item_id: str) -> str:
        return os.path.join(get_user_library_dir(user_id), f"{item_id}.json")

    def _workshop_file_path(item_id: str) -> str:
        return os.path.join(workshop_dir, f"{item_id}.json")

    def _read_json(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}

    def _write_json(path: str, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _summarize_content(content: Dict[str, Any]) -> Dict[str, Any]:
        md_files = content.get("md", {}) if isinstance(content, dict) else {}
        csv_files = content.get("csv", {}) if isinstance(content, dict) else {}
        roster_text = md_files.get("characters/roster.json") or md_files.get("roster.json")
        character_count = 0
        if roster_text:
            try:
                roster = json.loads(roster_text)
                if isinstance(roster, dict):
                    character_count = len([k for k in roster.keys() if str(k).strip()])
            except Exception:
                character_count = 0
        skill_count = len([p for p in md_files.keys() if str(p).startswith("skills/")])
        world_count = len([p for p in md_files.keys() if str(p).startswith("world/") or str(p) == "main_system.md"])
        return {
            "md_files": len(md_files),
            "csv_files": len(csv_files),
            "character_count": character_count,
            "skill_count": skill_count,
            "world_count": world_count,
        }

    def _normalize_library_record(record: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        data = dict(record or {})
        item_id = str(data.get("id", "") or "").strip()
        content = data.get("content", {}) if isinstance(data.get("content"), dict) else {"md": {}, "csv": {}}
        data["visibility"] = str(data.get("visibility", "private") or "private")
        data["version"] = max(1, int(data.get("version", 1) or 1))
        data["source_type"] = str(data.get("source_type", "original") or "original")
        data["source_mod_id"] = str(data.get("source_mod_id", "") or "")
        data["parent_workshop_id"] = str(data.get("parent_workshop_id", data.get("origin_workshop_id", "")) or "")
        data["linked_workshop_id"] = str(data.get("linked_workshop_id", "") or "")
        data["origin_workshop_id"] = str(data.get("origin_workshop_id", data["parent_workshop_id"]) or "")
        data["owner_user_id"] = str(data.get("owner_user_id", user_id) or user_id)
        data["published_at"] = str(data.get("published_at", "") or "")
        data["updated_at"] = str(data.get("updated_at", data.get("timestamp", _now_str())) or _now_str())
        data["timestamp"] = str(data.get("timestamp", data["updated_at"]) or data["updated_at"])
        data["summary"] = _summarize_content(content)
        return data

    def _normalize_workshop_record(record: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(record or {})
        content = data.get("content", {}) if isinstance(data.get("content"), dict) else {"md": {}, "csv": {}}
        data["version"] = max(1, int(data.get("version", 1) or 1))
        data["visibility"] = "public"
        data["source_type"] = str(data.get("source_type", "original") or "original")
        data["source_mod_id"] = str(data.get("source_mod_id", "") or "")
        data["parent_workshop_id"] = str(data.get("parent_workshop_id", data.get("source_mod_id", "")) or "")
        data["published_at"] = str(data.get("published_at", data.get("timestamp", _now_str())) or _now_str())
        data["updated_at"] = str(data.get("updated_at", data.get("published_at", _now_str())) or _now_str())
        data["summary"] = _summarize_content(content)
        return data

    def _build_library_record(
        *,
        item_id: str,
        user_id: str,
        name: str,
        description: str,
        content: Dict[str, Any],
        linked_workshop_id: str = "",
        origin_workshop_id: str = "",
        visibility: str = "private",
        version: int = 1,
        source_type: str = "original",
        source_mod_id: str = "",
        parent_workshop_id: str = "",
        published_at: str = "",
    ) -> Dict[str, Any]:
        author = f"User_{user_id[:4]}"
        manifest = build_manifest(
            mod_id=item_id,
            name=name,
            author=author,
            source="library",
            content=content,
        )
        return {
            "id": item_id,
            "name": name,
            "author": author,
            "description": description,
            "content": content,
            "manifest": manifest,
            "linked_workshop_id": linked_workshop_id,
            "origin_workshop_id": origin_workshop_id,
            "visibility": visibility,
            "version": max(1, int(version or 1)),
            "source_type": source_type,
            "source_mod_id": source_mod_id,
            "parent_workshop_id": parent_workshop_id or origin_workshop_id,
            "owner_user_id": user_id,
            "published_at": published_at,
            "timestamp": _now_str(),
            "updated_at": _now_str(),
            "summary": _summarize_content(content),
        }

    def _build_workshop_record(
        *,
        item_id: str,
        linked_library_id: str,
        owner_user_id: str,
        name: str,
        author: str,
        description: str,
        content: Dict[str, Any],
        existing_downloads: int = 0,
        existing_timestamp: Optional[str] = None,
        version: int = 1,
        source_type: str = "original",
        source_mod_id: str = "",
        parent_workshop_id: str = "",
        published_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        manifest = build_manifest(
            mod_id=item_id,
            name=name,
            author=author,
            source="workshop",
            content=content,
        )
        return {
            "id": item_id,
            "type": "prompt_pack",
            "name": name,
            "author": author,
            "description": description,
            "content": content,
            "manifest": manifest,
            "downloads": existing_downloads,
            "timestamp": existing_timestamp or _now_str(),
            "updated_at": _now_str(),
            "published_at": published_at or existing_timestamp or _now_str(),
            "owner_user_id": owner_user_id,
            "linked_library_id": linked_library_id,
            "version": max(1, int(version or 1)),
            "visibility": "public",
            "source_type": source_type,
            "source_mod_id": source_mod_id,
            "parent_workshop_id": parent_workshop_id or source_mod_id,
            "summary": _summarize_content(content),
        }

    @router.post("/api/library/save_current")
    def save_to_library(req: LibrarySaveReq, user_id: str = get_user_id):
        """将当前活动配置另存为库中的一个模组包"""
        try:
            with with_user_write_lock(user_id):
                quota = get_storage_quota_data(user_id)
                if quota["usage"]["library_items"] >= max_library_items:
                    raise HTTPException(status_code=400, detail="library 模组数量已达上限，请先清理")
                if quota["usage"]["library_bytes"] >= max_library_total_bytes:
                    raise HTTPException(status_code=400, detail="library 存储已达上限，请先清理")

                content = package_mod(user_id)
                import uuid

                item_id = str(uuid.uuid4())[:8]
                data = _build_library_record(
                    item_id=item_id,
                    user_id=user_id,
                    name=req.name,
                    description=req.description,
                    content=content,
                    visibility="private",
                    version=1,
                    source_type="original",
                )
                _write_json(_library_file_path(user_id, item_id), data)
            append_audit_log(user_id, "save_to_library", "ok", req.name, {"mod_id": item_id})
            return {"status": "success", "id": item_id}
        except HTTPException as e:
            append_audit_log(user_id, "save_to_library", "error", req.name, {"error": str(e.detail)})
            raise
        except Exception as e:
            append_audit_log(user_id, "save_to_library", "error", req.name, {"error": str(e)})
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/library/list")
    def list_library(user_id: str = get_user_id):
        """列出当前用户库中所有的模组包"""
        lib_dir = get_user_library_dir(user_id)
        items = []
        if os.path.exists(lib_dir):
            for fn in os.listdir(lib_dir):
                if fn.endswith(".json"):
                    try:
                        with open(os.path.join(lib_dir, fn), "r", encoding="utf-8") as f:
                            d = _normalize_library_record(json.load(f), user_id)
                            items.append(
                                {
                                    "id": d.get("id"),
                                    "name": d.get("name"),
                                    "description": d.get("description"),
                                    "author": d.get("author"),
                                    "timestamp": d.get("timestamp"),
                                    "source": d.get("manifest", {}).get("source", "library"),
                                    "base_version": d.get("manifest", {}).get("base_version", "default-v1"),
                                    "linked_workshop_id": d.get("linked_workshop_id", ""),
                                    "origin_workshop_id": d.get("origin_workshop_id", ""),
                                    "visibility": d.get("visibility", "private"),
                                    "version": d.get("version", 1),
                                    "source_type": d.get("source_type", "original"),
                                    "source_mod_id": d.get("source_mod_id", ""),
                                    "parent_workshop_id": d.get("parent_workshop_id", ""),
                                    "published_at": d.get("published_at", ""),
                                    "updated_at": d.get("updated_at", d.get("timestamp", "")),
                                    "summary": d.get("summary", {}),
                                }
                            )
                    except Exception:
                        pass
        return {"status": "success", "data": sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)}

    @router.post("/api/library/apply/{item_id}")
    def apply_from_library(item_id: str, user_id: str = get_user_id):
        raise HTTPException(status_code=400, detail="模组不能在局外直接应用，请在开始新游戏时选择")

    @router.post("/api/library/validate/{item_id}")
    def validate_library_item(item_id: str, user_id: str = get_user_id):
        lib_dir = get_user_library_dir(user_id)
        file_path = os.path.join(lib_dir, f"{item_id}.json")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Mod not found in library")
        with open(file_path, "r", encoding="utf-8") as f:
            data = _normalize_library_record(json.load(f), user_id)
        content = data.get("content", {})
        manifest = data.get("manifest", {})
        report = build_validation_report(content, manifest if isinstance(manifest, dict) else None)
        return {"status": "success" if report.get("ok") else "error", "report": report}

    @router.delete("/api/library/{item_id}")
    def delete_from_library(item_id: str, user_id: str = get_user_id):
        file_path = _library_file_path(user_id, item_id)
        with with_user_write_lock(user_id):
            if os.path.exists(file_path):
                linked_workshop_id = ""
                try:
                    linked_workshop_id = str(_normalize_library_record(_read_json(file_path), user_id).get("linked_workshop_id", "")).strip()
                except Exception:
                    linked_workshop_id = ""
                os.remove(file_path)
                if linked_workshop_id:
                    workshop_path = _workshop_file_path(linked_workshop_id)
                    if os.path.exists(workshop_path):
                        try:
                            workshop_data = _read_json(workshop_path)
                            if str(workshop_data.get("owner_user_id", "")) == str(user_id):
                                os.remove(workshop_path)
                        except Exception:
                            pass
        append_audit_log(user_id, "delete_library_mod", "ok", item_id, {})
        return {"status": "success"}

    @router.get("/api/user/state")
    def get_user_state(user_id: str = get_user_id):
        st = read_user_state(user_id)
        if "editor_mod_id" not in st:
            st["editor_mod_id"] = "default"
        if "editor_source" not in st:
            st["editor_source"] = "default"
        return {"status": "success", "data": st}

    @router.post("/api/library/edit/{item_id}")
    def select_library_item_for_edit(item_id: str, user_id: str = get_user_id):
        file_path = _library_file_path(user_id, item_id)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Mod not found in library")
        with with_user_write_lock(user_id):
            st = read_user_state(user_id)
            st["editor_mod_id"] = item_id
            st["editor_source"] = "library"
            st["updated_at"] = _now_str()
            write_user_state(user_id, st)
        append_audit_log(user_id, "select_editor_library_mod", "ok", item_id, {})
        return {"status": "success", "editor_mod_id": item_id, "editor_source": "library"}

    @router.post("/api/editor/default")
    def select_default_for_edit(user_id: str = get_user_id):
        with with_user_write_lock(user_id):
            st = read_user_state(user_id)
            st["editor_mod_id"] = "default"
            st["editor_source"] = "default"
            st["updated_at"] = _now_str()
            write_user_state(user_id, st)
        append_audit_log(user_id, "select_editor_default", "ok", "default", {})
        return {"status": "success", "editor_mod_id": "default", "editor_source": "default"}

    @router.get("/api/storage/quota")
    def get_storage_quota(user_id: str = get_user_id):
        return {"status": "success", "data": get_storage_quota_data(user_id)}

    @router.post("/api/storage/cleanup")
    def cleanup_storage(req: StorageCleanupReq, admin_session: Dict[str, Any] = require_admin, user_id: str = get_user_id):
        keep_lib = max(1, min(int(req.keep_recent_library), max_library_items))
        keep_snap = max(1, min(int(req.keep_recent_snapshots), max_snapshots_keep))
        try:
            with with_user_write_lock(user_id):
                report = cleanup_user_storage(
                    user_id=user_id,
                    keep_recent_library=keep_lib,
                    keep_recent_snapshots=keep_snap,
                    dry_run=bool(req.dry_run),
                )
            append_audit_log(
                user_id,
                "cleanup_storage",
                "ok",
                "dry_run" if req.dry_run else "execute",
                {
                    "removed_library": len(report.get("removed", {}).get("library", [])),
                    "removed_snapshots": len(report.get("removed", {}).get("snapshots", [])),
                },
            )
            return {"status": "success", "data": report}
        except Exception as e:
            append_audit_log(user_id, "cleanup_storage", "error", str(e), {})
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/user/audit")
    def get_user_audit(limit: int = 30, user_id: str = get_user_id):
        user_root = get_user_data_root(user_id)
        log_path = os.path.join(user_root, "audit.log")
        if not os.path.exists(log_path):
            return {"status": "success", "data": []}
        lines = []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            rows = []
            for line in lines[-max(1, min(limit, 200)):]:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
            return {"status": "success", "data": rows[::-1]}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    @router.get("/api/user/snapshots")
    def get_user_snapshots(user_id: str = get_user_id):
        return {"status": "success", "data": list_snapshots(user_id)}

    @router.post("/api/user/rollback/{snapshot_id}")
    def rollback_user_snapshot(snapshot_id: str, user_id: str = get_user_id):
        try:
            with with_user_write_lock(user_id):
                snap = load_snapshot(user_id, snapshot_id)
                content = snap.get("content", {})
                apply_mod_content_atomic(user_id, content)

                st = read_user_state(user_id)
                st["active_mod_id"] = "snapshot"
                st["active_source"] = "snapshot"
                st["active_content_hash"] = snapshot_id
                st["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                write_user_state(user_id, st)

            engine = get_engine(user_id)
            if engine:
                if hasattr(engine, "director"):
                    engine.director.reload_timeline()
                if hasattr(engine, "pm"):
                    engine.pm = type(engine.pm)(user_id)
                    if hasattr(engine, "player_name") and hasattr(engine.pm, "get_player_name"):
                        engine.player_name = engine.pm.get_player_name()
                    if hasattr(engine, "tm") and hasattr(engine.tm, "set_player_name") and hasattr(engine, "player_name"):
                        engine.tm.set_player_name(engine.player_name)
            append_audit_log(user_id, "rollback_snapshot", "ok", snapshot_id, {})
            return {"status": "success", "message": f"已回滚到快照 {snapshot_id}"}
        except FileNotFoundError:
            append_audit_log(user_id, "rollback_snapshot", "error", snapshot_id, {"error": "not found"})
            raise HTTPException(status_code=404, detail="Snapshot not found")

    @router.post("/api/workshop/validate_current")
    def validate_current_mod_for_publish(user_id: str = get_user_id):
        """发布前校验当前编辑目标，仅允许发布库中的自定义模组。"""
        st = read_user_state(user_id)
        editor_source = str(st.get("editor_source", "default"))
        editor_mod_id = str(st.get("editor_mod_id", "default"))
        if editor_source != "library" or not editor_mod_id or editor_mod_id == "default":
            raise HTTPException(status_code=400, detail="默认模组不可直接公开，请先另存到本地模组库再编辑")
        file_path = _library_file_path(user_id, editor_mod_id)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="当前编辑模组不存在")
        content = _read_json(file_path).get("content", {})
        report = build_validation_report(content, None)
        return {"status": "success" if report.get("ok") else "error", "report": report}

    def _publish_current_mod(req: WorkshopPublishReq, user_id: str, mode: str):
        """mode=create|update|fork"""
        print(f"📦 [Workshop] User {user_id} publishing mod: {req.name} mode={mode}")
        try:
            with with_user_write_lock(user_id):
                st = read_user_state(user_id)
                editor_source = str(st.get("editor_source", "default"))
                editor_mod_id = str(st.get("editor_mod_id", "default"))
                if editor_source != "library" or not editor_mod_id or editor_mod_id == "default":
                    raise HTTPException(status_code=400, detail="默认模组不可直接公开，请先另存到本地模组库再编辑")
                editor_library_path = _library_file_path(user_id, editor_mod_id)
                if not os.path.exists(editor_library_path):
                    raise HTTPException(status_code=404, detail="当前编辑模组不存在")
                current_library_item = _normalize_library_record(_read_json(editor_library_path), user_id)
                pack_content = current_library_item.get("content", {})
                pre_report = build_validation_report(pack_content, None)
                if not pre_report.get("ok"):
                    raise HTTPException(status_code=400, detail="发布校验失败: " + "; ".join(pre_report.get("errors", [])))
                current_library_id = editor_mod_id
                current_source_type = str(current_library_item.get("source_type", "original") or "original")
                current_linked_workshop_id = str(current_library_item.get("linked_workshop_id", "") or "")

                if mode == "update":
                    if not current_linked_workshop_id or str(current_library_item.get("visibility", "")) != "public":
                        raise HTTPException(status_code=400, detail="当前模组还没有公开版本，不能执行更新")
                elif mode == "fork":
                    if current_source_type != "downloaded":
                        raise HTTPException(status_code=400, detail="只有下载副本才能发布为派生作品")
                elif mode == "create":
                    if current_linked_workshop_id and str(current_library_item.get("visibility", "")) == "public":
                        raise HTTPException(status_code=400, detail="当前模组已有公开版本，请使用更新公开版本")

                import uuid

                library_item = None
                library_id = current_library_id
                if library_id:
                    library_path = _library_file_path(user_id, library_id)
                    if os.path.exists(library_path):
                        library_item = _normalize_library_record(_read_json(library_path), user_id)
                    else:
                        library_id = ""

                if not library_id:
                    library_id = str(uuid.uuid4())[:8]

                linked_workshop_id = str((library_item or {}).get("linked_workshop_id", "")).strip()
                if mode == "update":
                    workshop_id = linked_workshop_id or str(uuid.uuid4())[:8]
                else:
                    workshop_id = str(uuid.uuid4())[:8]
                workshop_path = _workshop_file_path(workshop_id)
                existing_workshop = _normalize_workshop_record(_read_json(workshop_path)) if os.path.exists(workshop_path) else {}
                if existing_workshop and str(existing_workshop.get("owner_user_id", "")) not in ("", str(user_id)):
                    raise HTTPException(status_code=403, detail="无权更新该公开模组")

                source_type = str(current_library_item.get("source_type", "original") or "original")
                source_mod_id = str(current_library_item.get("source_mod_id", "") or "")
                parent_workshop_id = str(current_library_item.get("parent_workshop_id", "") or "")
                if mode == "fork":
                    source_type = "forked"
                    source_mod_id = source_mod_id or current_library_item.get("origin_workshop_id", "")
                    parent_workshop_id = parent_workshop_id or source_mod_id
                elif mode == "create":
                    source_type = "original"
                    source_mod_id = ""
                    parent_workshop_id = ""
                next_version = int(existing_workshop.get("version", 0) or 0) + 1 if mode == "update" and existing_workshop else 1
                published_at = existing_workshop.get("published_at") if mode == "update" and existing_workshop else _now_str()

                workshop_record = _build_workshop_record(
                    item_id=workshop_id,
                    linked_library_id=library_id,
                    owner_user_id=user_id,
                    name=req.name,
                    author=req.author,
                    description=req.description,
                    content=pack_content,
                    existing_downloads=int(existing_workshop.get("downloads", 0) or 0),
                    existing_timestamp=existing_workshop.get("timestamp"),
                    version=next_version,
                    source_type=source_type,
                    source_mod_id=source_mod_id,
                    parent_workshop_id=parent_workshop_id,
                    published_at=published_at,
                )
                validate_mod_content(pack_content, workshop_record.get("manifest"))

                library_record = _build_library_record(
                    item_id=library_id,
                    user_id=user_id,
                    name=req.name,
                    description=req.description,
                    content=pack_content,
                    linked_workshop_id=workshop_id,
                    visibility="public",
                    version=next_version,
                    source_type=source_type,
                    source_mod_id=source_mod_id,
                    parent_workshop_id=parent_workshop_id,
                    published_at=published_at or _now_str(),
                )

                _write_json(_library_file_path(user_id, library_id), library_record)
                _write_json(workshop_path, workshop_record)

                st["active_mod_id"] = library_id
                st["active_source"] = "library"
                st["active_content_hash"] = library_record.get("manifest", {}).get("mod_id", library_id)
                st["updated_at"] = _now_str()
                write_user_state(user_id, st)

            append_audit_log(user_id, f"publish_workshop_mod_{mode}", "ok", req.name, {"mod_id": workshop_id, "library_id": library_id})
            return {"status": "success", "id": workshop_id, "library_id": library_id, "workshop_id": workshop_id, "mode": mode}
        except HTTPException as e:
            append_audit_log(user_id, f"publish_workshop_mod_{mode}", "error", req.name, {"error": str(e.detail)})
            raise

    @router.post("/api/workshop/publish_current")
    def publish_current_mod(req: WorkshopPublishReq, user_id: str = get_user_id):
        return _publish_current_mod(req, user_id, "create")

    @router.post("/api/workshop/publish_create")
    def publish_create_mod(req: WorkshopPublishReq, user_id: str = get_user_id):
        return _publish_current_mod(req, user_id, "create")

    @router.post("/api/workshop/publish_update")
    def publish_update_mod(req: WorkshopPublishReq, user_id: str = get_user_id):
        return _publish_current_mod(req, user_id, "update")

    @router.post("/api/workshop/publish_fork")
    def publish_fork_mod(req: WorkshopPublishReq, user_id: str = get_user_id):
        return _publish_current_mod(req, user_id, "fork")

    @router.get("/api/workshop/list")
    def get_workshop_list(user_id: str = get_user_id):
        """列出工坊中所有已发布的模组"""
        items = []
        if os.path.exists(workshop_dir):
            for filename in sorted(os.listdir(workshop_dir), reverse=True):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(workshop_dir, filename), "r", encoding="utf-8") as f:
                            data = _normalize_workshop_record(json.load(f))
                            items.append(
                                {
                                    "id": data.get("id"),
                                    "type": data.get("type", "prompt_pack"),
                                    "name": data.get("name"),
                                    "author": data.get("author"),
                                    "description": data.get("description"),
                                    "downloads": data.get("downloads", 0),
                                    "timestamp": data.get("timestamp"),
                                    "updated_at": data.get("updated_at", ""),
                                    "published_at": data.get("published_at", ""),
                                    "summary": data.get("summary", {}),
                                    "version": data.get("version", 1),
                                    "source_type": data.get("source_type", "original"),
                                    "source_mod_id": data.get("source_mod_id", ""),
                                    "parent_workshop_id": data.get("parent_workshop_id", ""),
                                    "owner_user_id": data.get("owner_user_id", ""),
                                    "linked_library_id": data.get("linked_library_id", ""),
                                    "is_owned_by_current_user": str(data.get("owner_user_id", "")) == str(user_id),
                                }
                            )
                    except Exception as e:
                        print(f"[Workshop] Error reading {filename}: {e}")
        return {"status": "success", "data": items}

    def _download_workshop_mod(item_id: str, user_id: str):
        workshop_path = _workshop_file_path(item_id)
        if not os.path.exists(workshop_path):
            raise HTTPException(status_code=404, detail="Item not found")

        ws_data = _normalize_workshop_record(_read_json(workshop_path))
        content = ws_data.get("content", {})
        manifest = ws_data.get("manifest", {})
        validate_mod_content(content, manifest if isinstance(manifest, dict) else None)

        with with_user_write_lock(user_id):
            owner_user_id = str(ws_data.get("owner_user_id", ""))
            linked_library_id = str(ws_data.get("linked_library_id", "")).strip()
            if owner_user_id == str(user_id) and linked_library_id:
                owned_library_path = _library_file_path(user_id, linked_library_id)
                if os.path.exists(owned_library_path):
                    return linked_library_id

            quota = get_storage_quota_data(user_id)
            if quota["usage"]["library_items"] >= max_library_items:
                raise HTTPException(status_code=400, detail="library 模组数量已达上限，请先清理")
            if quota["usage"]["library_bytes"] >= max_library_total_bytes:
                raise HTTPException(status_code=400, detail="library 存储已达上限，请先清理")

            import uuid

            library_id = str(uuid.uuid4())[:8]
            library_source_type = "downloaded"
            source_mod_id = str(ws_data.get("id", item_id) or item_id)
            library_record = _build_library_record(
                item_id=library_id,
                user_id=user_id,
                name=ws_data.get("name") or item_id,
                description=ws_data.get("description") or "",
                content=content,
                origin_workshop_id=item_id,
                visibility="private",
                version=1,
                source_type=library_source_type,
                source_mod_id=source_mod_id,
                parent_workshop_id=source_mod_id,
            )
            _write_json(_library_file_path(user_id, library_id), library_record)

        try:
            if str(ws_data.get("owner_user_id", "")) != str(user_id):
                ws_data["downloads"] = ws_data.get("downloads", 0) + 1
                _write_json(workshop_path, ws_data)
        except Exception:
            pass
        return library_id

    @router.post("/api/workshop/download/{item_id}")
    def download_workshop_mod(item_id: str, user_id: str = get_user_id):
        """将工坊模组下载到个人模组库"""
        library_id = _download_workshop_mod(item_id, user_id)
        append_audit_log(user_id, "download_workshop_mod", "ok", item_id, {})
        return {"status": "success", "message": "模组已成功添加到您的收藏库", "library_id": library_id}

    @router.post("/api/workshop/apply/{item_id}")
    def apply_workshop_mod(item_id: str, user_id: str = get_user_id):
        raise HTTPException(status_code=400, detail="模组不能在局外直接应用，请在开始新游戏时选择")

    @router.delete("/api/workshop/{item_id}")
    def delete_workshop_item(item_id: str, admin_session: Dict[str, Any] = require_admin):
        """从工坊仓库彻底删除指定的模组包文件"""
        file_path = os.path.join(workshop_dir, f"{item_id}.json")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return {"status": "success"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=404, detail="Not found")

    @router.patch("/api/workshop/{item_id}")
    def update_workshop_item(item_id: str, req: WorkshopUpdateReq, admin_session: Dict[str, Any] = require_admin):
        """更新工坊条目的基础元数据"""
        file_path = os.path.join(workshop_dir, f"{item_id}.json")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Item not found")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if req.name is not None:
                data["name"] = req.name
            if req.author is not None:
                data["author"] = req.author
            if req.description is not None:
                data["description"] = req.description

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

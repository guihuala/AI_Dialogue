from typing import Any, Callable, Dict, List, Optional
import json
import os
import shutil

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.services.mod_service import (
    build_mod_index_entry,
    build_library_list_item,
    build_library_record as build_library_record_meta,
    build_workshop_list_item,
    list_library_records,
    list_workshop_records,
    load_library_record,
    load_workshop_record,
    normalize_library_record,
    normalize_workshop_record,
    prepare_publish_bundle,
    persist_publish_bundle,
    query_mod_list,
    read_record_json,
    resolve_download_target,
    now_str,
    summarize_content,
    sync_library_record_with_upstream,
    write_record_json,
)


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
    require_account=None,
):
    router = APIRouter()

    def _library_file_path(user_id: str, item_id: str) -> str:
        return os.path.join(get_user_library_dir(user_id), f"{item_id}.json")

    def _workshop_file_path(item_id: str) -> str:
        return os.path.join(workshop_dir, f"{item_id}.json")

    def _read_json(path: str) -> Dict[str, Any]:
        return read_record_json(path)

    def _write_json(path: str, data: Dict[str, Any]) -> None:
        write_record_json(path, data)

    def _load_workshop_record(item_id: str) -> Dict[str, Any]:
        path = _workshop_file_path(item_id)
        if not os.path.exists(path):
            return {}
        return normalize_workshop_record(_read_json(path))

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
        return build_library_record_meta(
            item_id=item_id,
            user_id=user_id,
            name=name,
            description=description,
            content=content,
            build_manifest=build_manifest,
            linked_workshop_id=linked_workshop_id,
            origin_workshop_id=origin_workshop_id,
            visibility=visibility,
            version=version,
            source_type=source_type,
            source_mod_id=source_mod_id,
            parent_workshop_id=parent_workshop_id,
            published_at=published_at,
        )

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
    def list_library(
        q: str = "",
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        source_type: str = "",
        visibility: str = "",
        page: int = 1,
        page_size: int = 50,
        user_id: str = get_user_id,
    ):
        """列出当前用户库中所有的模组包"""
        lib_dir = get_user_library_dir(user_id)
        items = []
        for d in list_library_records(lib_dir, user_id):
            upstream = None
            if d.get("source_type") == "downloaded" and d.get("source_mod_id"):
                upstream = _load_workshop_record(str(d.get("source_mod_id")))
            item = build_library_list_item(d, upstream)
            item["index"] = build_mod_index_entry(d, "library")
            items.append(item)
        queried = query_mod_list(
            items,
            q=q,
            sort_by=sort_by,
            sort_order=sort_order,
            source_type=source_type,
            visibility=visibility,
            page=page,
            page_size=page_size,
        )
        return {"status": "success", "data": queried["items"], "pagination": queried["pagination"]}

    @router.post("/api/library/apply/{item_id}")
    def apply_from_library(item_id: str, user_id: str = get_user_id):
        raise HTTPException(status_code=400, detail="模组不能在局外直接应用，请在开始新游戏时选择")

    @router.post("/api/library/validate/{item_id}")
    def validate_library_item(item_id: str, user_id: str = get_user_id):
        lib_dir = get_user_library_dir(user_id)
        file_path = os.path.join(lib_dir, f"{item_id}.json")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Mod not found in library")
        data = load_library_record(file_path, user_id)
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
                    linked_workshop_id = str(normalize_library_record(_read_json(file_path), user_id).get("linked_workshop_id", "")).strip()
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

    @router.post("/api/library/sync/{item_id}")
    def sync_library_item(item_id: str, user_id: str = get_user_id):
        file_path = _library_file_path(user_id, item_id)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Mod not found in library")
        try:
            with with_user_write_lock(user_id):
                library_data = normalize_library_record(_read_json(file_path), user_id)
                if str(library_data.get("source_type", "")) != "downloaded":
                    raise HTTPException(status_code=400, detail="只有下载副本才能同步原作更新")
                source_mod_id = str(library_data.get("source_mod_id", "") or "").strip()
                if not source_mod_id:
                    raise HTTPException(status_code=400, detail="当前副本缺少来源作品信息")
                upstream = _load_workshop_record(source_mod_id)
                if not upstream:
                    raise HTTPException(status_code=404, detail="来源公共模组不存在")

                local_version = int(library_data.get("version", 1) or 1)
                upstream_version = int(upstream.get("version", 1) or 1)
                if upstream_version <= local_version:
                    return {
                        "status": "success",
                        "message": "当前已经是最新版本",
                        "version": local_version,
                        "upstream_version": upstream_version,
                    }

                library_data = sync_library_record_with_upstream(
                    library_data,
                    upstream,
                    build_manifest=build_manifest,
                    item_id=item_id,
                    user_id=user_id,
                )
                _write_json(file_path, library_data)

            append_audit_log(user_id, "sync_library_mod", "ok", item_id, {"from_version": local_version, "to_version": upstream_version})
            return {
                "status": "success",
                "message": f"已同步到 v{upstream_version}",
                "version": upstream_version,
                "upstream_version": upstream_version,
            }
        except HTTPException as e:
            append_audit_log(user_id, "sync_library_mod", "error", item_id, {"error": str(e.detail)})
            raise

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
            st["updated_at"] = now_str()
            write_user_state(user_id, st)
        append_audit_log(user_id, "select_editor_library_mod", "ok", item_id, {})
        return {"status": "success", "editor_mod_id": item_id, "editor_source": "library"}

    @router.post("/api/editor/default")
    def select_default_for_edit(user_id: str = get_user_id):
        with with_user_write_lock(user_id):
            st = read_user_state(user_id)
            st["editor_mod_id"] = "default"
            st["editor_source"] = "default"
            st["updated_at"] = now_str()
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
                st["updated_at"] = now_str()
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
                current_library_item = normalize_library_record(_read_json(editor_library_path), user_id)
                pack_content = current_library_item.get("content", {})
                pre_report = build_validation_report(pack_content, None)
                if not pre_report.get("ok"):
                    raise HTTPException(status_code=400, detail="发布校验失败: " + "; ".join(pre_report.get("errors", [])))
                current_library_id = editor_mod_id

                library_item = None
                library_id = current_library_id
                if library_id:
                    library_path = _library_file_path(user_id, library_id)
                    if os.path.exists(library_path):
                        library_item = normalize_library_record(_read_json(library_path), user_id)
                    else:
                        library_id = ""

                if not library_id:
                    import uuid
                    library_id = str(uuid.uuid4())[:8]

                linked_workshop_id = str((library_item or {}).get("linked_workshop_id", "") or "").strip()
                workshop_path = _workshop_file_path(linked_workshop_id) if mode == "update" and linked_workshop_id else ""
                existing_workshop = normalize_workshop_record(_read_json(workshop_path)) if os.path.exists(workshop_path) else {}
                if existing_workshop and str(existing_workshop.get("owner_user_id", "")) not in ("", str(user_id)):
                    raise HTTPException(status_code=403, detail="无权更新该公开模组")
                publish_bundle = prepare_publish_bundle(
                    current_library_item=current_library_item,
                    library_item=library_item,
                    existing_workshop=existing_workshop,
                    mode=mode,
                    user_id=user_id,
                    name=req.name,
                    author=req.author,
                    description=req.description,
                    build_manifest=build_manifest,
                    make_id=lambda: str(uuid.uuid4())[:8],
                    library_id=library_id,
                )
                workshop_id = publish_bundle["workshop_id"]
                workshop_path = _workshop_file_path(workshop_id)
                workshop_record = publish_bundle["workshop_record"]
                validate_mod_content(pack_content, workshop_record.get("manifest"))
                library_record = publish_bundle["library_record"]
                persist_publish_bundle(
                    library_path=_library_file_path(user_id, library_id),
                    workshop_path=workshop_path,
                    library_record=library_record,
                    workshop_record=workshop_record,
                    user_state=st,
                    write_record=_write_json,
                    write_state=lambda updated: write_user_state(user_id, updated),
                    library_id=library_id,
                )

            append_audit_log(user_id, f"publish_workshop_mod_{mode}", "ok", req.name, {"mod_id": workshop_id, "library_id": library_id})
            return {"status": "success", "id": workshop_id, "library_id": library_id, "workshop_id": workshop_id, "mode": mode}
        except HTTPException as e:
            append_audit_log(user_id, f"publish_workshop_mod_{mode}", "error", req.name, {"error": str(e.detail)})
            raise

    @router.post("/api/workshop/publish_current")
    def publish_current_mod(req: WorkshopPublishReq, account_session: Dict[str, Any] = require_account, user_id: str = get_user_id):
        return _publish_current_mod(req, user_id, "create")

    @router.post("/api/workshop/publish_create")
    def publish_create_mod(req: WorkshopPublishReq, account_session: Dict[str, Any] = require_account, user_id: str = get_user_id):
        return _publish_current_mod(req, user_id, "create")

    @router.post("/api/workshop/publish_update")
    def publish_update_mod(req: WorkshopPublishReq, account_session: Dict[str, Any] = require_account, user_id: str = get_user_id):
        return _publish_current_mod(req, user_id, "update")

    @router.post("/api/workshop/publish_fork")
    def publish_fork_mod(req: WorkshopPublishReq, account_session: Dict[str, Any] = require_account, user_id: str = get_user_id):
        return _publish_current_mod(req, user_id, "fork")

    def _query_workshop_items(
        *,
        user_id: str,
        q: str = "",
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        source_type: str = "",
        focus_tag: str = "",
        owned_only: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        items = []
        for data in list_workshop_records(workshop_dir):
            item = build_workshop_list_item(data, user_id)
            item["index"] = build_mod_index_entry(data, "workshop")
            items.append(item)
        queried = query_mod_list(
            items,
            q=q,
            sort_by=sort_by,
            sort_order=sort_order,
            source_type=source_type,
            focus_tag=focus_tag,
            owned_only=owned_only,
            page=page,
            page_size=page_size,
        )
        return {"status": "success", "data": queried["items"], "pagination": queried["pagination"]}

    @router.get("/api/workshop/list")
    def get_workshop_list(
        q: str = "",
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        source_type: str = "",
        focus_tag: str = "",
        owned_only: bool = False,
        page: int = 1,
        page_size: int = 50,
        user_id: str = get_user_id,
    ):
        """列出工坊中所有已发布的模组"""
        return _query_workshop_items(
            user_id=user_id,
            q=q,
            sort_by=sort_by,
            sort_order=sort_order,
            source_type=source_type,
            focus_tag=focus_tag,
            owned_only=owned_only,
            page=page,
            page_size=page_size,
        )

    @router.get("/api/workshop/mine")
    def get_my_workshop_list(
        q: str = "",
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        source_type: str = "",
        focus_tag: str = "",
        page: int = 1,
        page_size: int = 50,
        account_session: Dict[str, Any] = require_account,
    ):
        account = account_session.get("account", {}) if isinstance(account_session, dict) else {}
        user_id = str(account.get("account_id", "") or "")
        return _query_workshop_items(
            user_id=user_id,
            q=q,
            sort_by=sort_by,
            sort_order=sort_order,
            source_type=source_type,
            focus_tag=focus_tag,
            owned_only=True,
            page=page,
            page_size=page_size,
        )

    def _download_workshop_mod(item_id: str, user_id: str):
        workshop_path = _workshop_file_path(item_id)
        if not os.path.exists(workshop_path):
            raise HTTPException(status_code=404, detail="Item not found")

        ws_data = normalize_workshop_record(_read_json(workshop_path))
        content = ws_data.get("content", {})
        manifest = ws_data.get("manifest", {})
        manifest_for_use = manifest if isinstance(manifest, dict) else None
        try:
            validate_mod_content(content, manifest_for_use)
        except Exception:
            # 兼容历史/手工编辑导致的 manifest 漂移：优先信任内容本体并即时修复 manifest。
            validate_mod_content(content, None)
            ws_data["manifest"] = build_manifest(
                mod_id=str(ws_data.get("id", item_id) or item_id),
                name=str(ws_data.get("name", item_id) or item_id),
                author=str(ws_data.get("author", "") or ""),
                source="workshop",
                content=content,
            )
            try:
                _write_json(workshop_path, ws_data)
            except Exception:
                pass

        with with_user_write_lock(user_id):
            # 若本地已存在同源下载副本，直接覆盖同步，避免“下载后仍用旧事件池”。
            lib_dir = get_user_library_dir(user_id)
            source_mod_id = str(ws_data.get("id", "") or "")
            existing_download_id = ""
            if os.path.exists(lib_dir):
                for file_name in os.listdir(lib_dir):
                    if not file_name.endswith(".json"):
                        continue
                    file_path = os.path.join(lib_dir, file_name)
                    try:
                        row = normalize_library_record(_read_json(file_path), user_id)
                    except Exception:
                        continue
                    if str(row.get("source_type", "")) != "downloaded":
                        continue
                    if str(row.get("source_mod_id", "") or "").strip() != source_mod_id:
                        continue
                    existing_download_id = str(row.get("id", file_name.replace(".json", "")) or file_name.replace(".json", ""))
                    break
            if existing_download_id:
                target_path = _library_file_path(user_id, existing_download_id)
                old_row = normalize_library_record(_read_json(target_path), user_id)
                synced_row = _build_library_record(
                    item_id=existing_download_id,
                    user_id=user_id,
                    name=str(ws_data.get("name", existing_download_id) or existing_download_id),
                    description=str(ws_data.get("description", "") or ""),
                    content=ws_data.get("content", {}),
                    linked_workshop_id=str(old_row.get("linked_workshop_id", "") or ""),
                    origin_workshop_id=str(old_row.get("origin_workshop_id", source_mod_id) or source_mod_id),
                    visibility=str(old_row.get("visibility", "private") or "private"),
                    version=int(max(int(old_row.get("version", 1) or 1), int(ws_data.get("version", 1) or 1))),
                    source_type="downloaded",
                    source_mod_id=source_mod_id,
                    parent_workshop_id=str(old_row.get("parent_workshop_id", source_mod_id) or source_mod_id),
                    published_at=str(old_row.get("published_at", "") or ""),
                )
                _write_json(target_path, synced_row)
                return existing_download_id

            def _library_exists(candidate_id: str) -> bool:
                return os.path.exists(_library_file_path(user_id, candidate_id))

            import uuid

            target = resolve_download_target(
                workshop_record=ws_data,
                user_id=user_id,
                library_exists=_library_exists,
                make_library_id=lambda: str(uuid.uuid4())[:8],
                build_manifest=build_manifest,
            )
            if target["reuse_existing"]:
                return str(target["library_id"])

            quota = get_storage_quota_data(user_id)
            if quota["usage"]["library_items"] >= max_library_items:
                raise HTTPException(status_code=400, detail="library 模组数量已达上限，请先清理")
            if quota["usage"]["library_bytes"] >= max_library_total_bytes:
                raise HTTPException(status_code=400, detail="library 存储已达上限，请先清理")

            library_id = str(target["library_id"])
            library_record = target["library_record"]
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

            if isinstance(data.get("content"), dict):
                data["manifest"] = build_manifest(
                    mod_id=str(data.get("id", item_id) or item_id),
                    name=str(data.get("name", item_id) or item_id),
                    author=str(data.get("author", "") or ""),
                    source="workshop",
                    content=data.get("content", {}),
                )

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

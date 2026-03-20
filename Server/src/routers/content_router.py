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
                manifest = build_manifest(
                    mod_id=item_id,
                    name=req.name,
                    author=f"User_{user_id[:4]}",
                    source="library",
                    content=content,
                )
                data = {
                    "id": item_id,
                    "name": req.name,
                    "author": f"User_{user_id[:4]}",
                    "description": req.description,
                    "content": content,
                    "manifest": manifest,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                lib_dir = get_user_library_dir(user_id)
                file_path = os.path.join(lib_dir, f"{item_id}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
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
                            d = json.load(f)
                            items.append(
                                {
                                    "id": d.get("id"),
                                    "name": d.get("name"),
                                    "description": d.get("description"),
                                    "timestamp": d.get("timestamp"),
                                    "source": d.get("manifest", {}).get("source", "library"),
                                    "base_version": d.get("manifest", {}).get("base_version", "default-v1"),
                                }
                            )
                    except Exception:
                        pass
        return {"status": "success", "data": sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)}

    @router.post("/api/library/apply/{item_id}")
    def apply_from_library(item_id: str, user_id: str = get_user_id):
        """从个人库中选择一个模组包并应用到当前活动环境"""
        lib_dir = get_user_library_dir(user_id)
        file_path = os.path.join(lib_dir, f"{item_id}.json")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Mod not found in library")

        try:
            with with_user_write_lock(user_id):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                content = data.get("content", {})
                manifest = data.get("manifest", {})
                validate_mod_content(content, manifest if isinstance(manifest, dict) else None)

                snapshot = create_snapshot(user_id, package_mod(user_id), reason=f"before_apply:{item_id}")
                trim_snapshots(user_id, keep=max_snapshots_keep)

                apply_mod_content_atomic(user_id, content)

                st = read_user_state(user_id)
                st["active_mod_id"] = item_id
                st["active_source"] = manifest.get("source", "library") if isinstance(manifest, dict) else "library"
                st["active_content_hash"] = manifest.get("mod_id", item_id)
                st["last_good_snapshot_id"] = snapshot.get("id", "")
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

            append_audit_log(user_id, "apply_library_mod", "ok", item_id, {"name": data.get("name")})
            return {"status": "success", "message": f"模组 [{data.get('name')}] 已成功应用"}
        except HTTPException as e:
            append_audit_log(user_id, "apply_library_mod", "error", item_id, {"error": str(e.detail)})
            raise
        except Exception as e:
            append_audit_log(user_id, "apply_library_mod", "error", item_id, {"error": str(e)})
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/library/validate/{item_id}")
    def validate_library_item(item_id: str, user_id: str = get_user_id):
        lib_dir = get_user_library_dir(user_id)
        file_path = os.path.join(lib_dir, f"{item_id}.json")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Mod not found in library")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        content = data.get("content", {})
        manifest = data.get("manifest", {})
        report = build_validation_report(content, manifest if isinstance(manifest, dict) else None)
        return {"status": "success" if report.get("ok") else "error", "report": report}

    @router.delete("/api/library/{item_id}")
    def delete_from_library(item_id: str, user_id: str = get_user_id):
        lib_dir = get_user_library_dir(user_id)
        file_path = os.path.join(lib_dir, f"{item_id}.json")
        with with_user_write_lock(user_id):
            if os.path.exists(file_path):
                os.remove(file_path)
        append_audit_log(user_id, "delete_library_mod", "ok", item_id, {})
        return {"status": "success"}

    @router.get("/api/user/state")
    def get_user_state(user_id: str = get_user_id):
        return {"status": "success", "data": read_user_state(user_id)}

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
        """发布前校验当前 active 内容，返回错误/警告清单。"""
        content = package_mod(user_id)
        report = build_validation_report(content, None)
        return {"status": "success" if report.get("ok") else "error", "report": report}

    @router.post("/api/workshop/publish_current")
    def publish_current_mod(req: WorkshopPublishReq, user_id: str = get_user_id):
        """将该玩家当前的活动模组打包并在工坊发布"""
        print(f"📦 [Workshop] User {user_id} publishing mod: {req.name}")
        try:
            with with_user_write_lock(user_id):
                pack_content = package_mod(user_id)
                pre_report = build_validation_report(pack_content, None)
                if not pre_report.get("ok"):
                    raise HTTPException(status_code=400, detail="发布校验失败: " + "; ".join(pre_report.get("errors", [])))

                import uuid

                item_id = str(uuid.uuid4())[:8]
                manifest = build_manifest(
                    mod_id=item_id,
                    name=req.name,
                    author=req.author,
                    source="workshop",
                    content=pack_content,
                )
                validate_mod_content(pack_content, manifest)
                data = {
                    "id": item_id,
                    "type": "prompt_pack",
                    "name": req.name,
                    "author": req.author,
                    "description": req.description,
                    "content": pack_content,
                    "manifest": manifest,
                    "downloads": 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                file_path = os.path.join(workshop_dir, f"{item_id}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            append_audit_log(user_id, "publish_workshop_mod", "ok", req.name, {"mod_id": item_id})
            return {"status": "success", "id": item_id}
        except HTTPException as e:
            append_audit_log(user_id, "publish_workshop_mod", "error", req.name, {"error": str(e.detail)})
            raise

    @router.get("/api/workshop/list")
    def get_workshop_list():
        """列出工坊中所有已发布的模组"""
        items = []
        if os.path.exists(workshop_dir):
            for filename in sorted(os.listdir(workshop_dir), reverse=True):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(workshop_dir, filename), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            items.append(
                                {
                                    "id": data.get("id"),
                                    "type": data.get("type", "prompt_pack"),
                                    "name": data.get("name"),
                                    "author": data.get("author"),
                                    "description": data.get("description"),
                                    "downloads": data.get("downloads", 0),
                                    "timestamp": data.get("timestamp"),
                                }
                            )
                    except Exception as e:
                        print(f"[Workshop] Error reading {filename}: {e}")
        return {"status": "success", "data": items}

    def _download_workshop_mod(item_id: str, user_id: str):
        workshop_path = os.path.join(workshop_dir, f"{item_id}.json")
        if not os.path.exists(workshop_path):
            raise HTTPException(status_code=404, detail="Item not found")

        with open(workshop_path, "r", encoding="utf-8") as f:
            ws_data = json.load(f)
        content = ws_data.get("content", {})
        manifest = ws_data.get("manifest", {})
        validate_mod_content(content, manifest if isinstance(manifest, dict) else None)

        with with_user_write_lock(user_id):
            quota = get_storage_quota_data(user_id)
            if quota["usage"]["library_items"] >= max_library_items:
                raise HTTPException(status_code=400, detail="library 模组数量已达上限，请先清理")
            if quota["usage"]["library_bytes"] >= max_library_total_bytes:
                raise HTTPException(status_code=400, detail="library 存储已达上限，请先清理")

            lib_dir = get_user_library_dir(user_id)
            lib_path = os.path.join(lib_dir, f"{item_id}.json")
            shutil.copy2(workshop_path, lib_path)

        try:
            with open(workshop_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["downloads"] = data.get("downloads", 0) + 1
            with open(workshop_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @router.post("/api/workshop/download/{item_id}")
    def download_workshop_mod(item_id: str, user_id: str = get_user_id):
        """将工坊模组下载到个人模组库"""
        _download_workshop_mod(item_id, user_id)
        append_audit_log(user_id, "download_workshop_mod", "ok", item_id, {})
        return {"status": "success", "message": "模组已成功添加到您的收藏库"}

    @router.post("/api/workshop/apply/{item_id}")
    def apply_workshop_mod(item_id: str, user_id: str = get_user_id):
        """从工坊直接应用 (内部包含下载到库的步骤)"""
        _download_workshop_mod(item_id, user_id)
        return apply_from_library(item_id, user_id)

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

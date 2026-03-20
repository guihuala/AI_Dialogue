import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.config import (
    get_user_data_root,
    get_user_events_dir,
    get_user_library_dir,
    get_user_prompts_dir,
    get_user_saves_dir,
)


USER_WRITE_LOCKS: Dict[str, threading.Lock] = {}
MAX_LIBRARY_ITEMS = 200
MAX_LIBRARY_TOTAL_BYTES = 300 * 1024 * 1024
MAX_SNAPSHOTS_KEEP = 20


def get_user_lock(user_id: str) -> threading.Lock:
    if user_id not in USER_WRITE_LOCKS:
        USER_WRITE_LOCKS[user_id] = threading.Lock()
    return USER_WRITE_LOCKS[user_id]


@contextmanager
def with_user_write_lock(user_id: str):
    lock = get_user_lock(user_id)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


def append_audit_log(user_id: str, action: str, status: str, detail: str = "", extra: Optional[Dict[str, Any]] = None):
    try:
        user_root = get_user_data_root(user_id)
        os.makedirs(user_root, exist_ok=True)
        log_path = os.path.join(user_root, "audit.log")
        payload = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "status": status,
            "detail": detail,
            "extra": extra or {},
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def calc_dir_size(path: str) -> int:
    total = 0
    if not os.path.exists(path):
        return total
    for root, _, files in os.walk(path):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                total += os.path.getsize(fp)
            except Exception:
                continue
    return total


def get_storage_quota_data(user_id: str) -> Dict[str, Any]:
    lib_dir = get_user_library_dir(user_id)
    snapshots_dir = os.path.join(get_user_data_root(user_id), "snapshots")
    saves_dir = get_user_saves_dir(user_id)
    prompts_dir = get_user_prompts_dir(user_id)
    events_dir = get_user_events_dir(user_id)

    library_items = 0
    if os.path.exists(lib_dir):
        library_items = len([f for f in os.listdir(lib_dir) if f.endswith(".json")])

    library_bytes = calc_dir_size(lib_dir)
    snapshots_bytes = calc_dir_size(snapshots_dir)
    saves_bytes = calc_dir_size(saves_dir)
    active_bytes = calc_dir_size(prompts_dir) + calc_dir_size(events_dir)

    warnings = []
    if library_items > int(MAX_LIBRARY_ITEMS * 0.9):
        warnings.append("library item 数量接近上限")
    if library_bytes > int(MAX_LIBRARY_TOTAL_BYTES * 0.9):
        warnings.append("library 存储接近上限")

    return {
        "limits": {
            "library_items": MAX_LIBRARY_ITEMS,
            "library_total_bytes": MAX_LIBRARY_TOTAL_BYTES,
            "snapshots_keep": MAX_SNAPSHOTS_KEEP,
        },
        "usage": {
            "library_items": library_items,
            "library_bytes": library_bytes,
            "snapshots_bytes": snapshots_bytes,
            "saves_bytes": saves_bytes,
            "active_bytes": active_bytes,
            "total_bytes": library_bytes + snapshots_bytes + saves_bytes + active_bytes,
        },
        "warnings": warnings,
    }


def cleanup_user_storage(user_id: str, keep_recent_library: int = 100, keep_recent_snapshots: int = 20, dry_run: bool = True) -> Dict[str, Any]:
    before = get_storage_quota_data(user_id)
    removed = {"library": [], "snapshots": []}

    lib_dir = get_user_library_dir(user_id)
    library_items = []
    if os.path.exists(lib_dir):
        for fn in os.listdir(lib_dir):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(lib_dir, fn)
            ts = ""
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ts = data.get("timestamp", "")
            except Exception:
                pass
            library_items.append({"file": fn, "path": fp, "timestamp": str(ts)})
    library_items = sorted(library_items, key=lambda x: x["timestamp"], reverse=True)
    for item in library_items[max(0, keep_recent_library):]:
        removed["library"].append(item["file"])
        if not dry_run:
            try:
                os.remove(item["path"])
            except Exception:
                pass

    snapshots_dir = os.path.join(get_user_data_root(user_id), "snapshots")
    snapshot_items = []
    if os.path.exists(snapshots_dir):
        for fn in os.listdir(snapshots_dir):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(snapshots_dir, fn)
            sid = fn.replace(".json", "")
            created = ""
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("id", sid)
                created = str(data.get("created_at", ""))
            except Exception:
                pass
            snapshot_items.append({"id": sid, "path": fp, "created": created})
    snapshot_items = sorted(snapshot_items, key=lambda x: x["created"], reverse=True)
    for item in snapshot_items[max(0, keep_recent_snapshots):]:
        removed["snapshots"].append(item["id"])
        if not dry_run:
            try:
                os.remove(item["path"])
            except Exception:
                pass

    after = before if dry_run else get_storage_quota_data(user_id)
    return {"dry_run": dry_run, "before": before, "after": after, "removed": removed}


def get_user_state_path(user_id: str) -> str:
    state_dir = get_user_data_root(user_id)
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "state.json")


def read_user_state(user_id: str) -> Dict[str, Any]:
    p = get_user_state_path(user_id)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {
        "active_mod_id": "default",
        "active_source": "default",
        "active_content_hash": "",
        "last_good_snapshot_id": "",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def write_user_state(user_id: str, state: Dict[str, Any]) -> None:
    p = get_user_state_path(user_id)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

from src.core.config import get_user_data_root


def get_snapshot_dir(user_id: str) -> str:
    path = os.path.join(get_user_data_root(user_id), "snapshots")
    os.makedirs(path, exist_ok=True)
    return path


def create_snapshot(user_id: str, content: Dict[str, Dict[str, str]], reason: str = "before_apply") -> Dict[str, Any]:
    snap_id = f"snap-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
    payload = {
        "id": snap_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason,
        "content": content,
    }
    out_path = os.path.join(get_snapshot_dir(user_id), f"{snap_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def list_snapshots(user_id: str) -> List[Dict[str, Any]]:
    snap_dir = get_snapshot_dir(user_id)
    items: List[Dict[str, Any]] = []
    for fn in os.listdir(snap_dir):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(snap_dir, fn), "r", encoding="utf-8") as f:
                data = json.load(f)
            items.append(
                {
                    "id": data.get("id"),
                    "created_at": data.get("created_at"),
                    "reason": data.get("reason", ""),
                }
            )
        except Exception:
            continue
    return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)


def load_snapshot(user_id: str, snapshot_id: str) -> Dict[str, Any]:
    path = os.path.join(get_snapshot_dir(user_id), f"{snapshot_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(snapshot_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def trim_snapshots(user_id: str, keep: int = 20) -> None:
    snaps = list_snapshots(user_id)
    for item in snaps[keep:]:
        sid = item.get("id")
        if not sid:
            continue
        path = os.path.join(get_snapshot_dir(user_id), f"{sid}.json")
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

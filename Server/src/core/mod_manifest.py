import hashlib
from datetime import datetime
from typing import Any, Dict, List, Tuple


def _sha256_text(text: str) -> str:
    data = (text or "").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def build_manifest(
    *,
    mod_id: str,
    name: str,
    author: str,
    source: str,
    content: Dict[str, Dict[str, str]],
    base_version: str = "default-v1",
    schema_version: int = 1,
) -> Dict[str, Any]:
    md_files = content.get("md", {}) if isinstance(content, dict) else {}
    csv_files = content.get("csv", {}) if isinstance(content, dict) else {}

    files: List[Dict[str, Any]] = []
    for path, text in md_files.items():
        files.append(
            {
                "path": f"prompts/{path}",
                "kind": "md",
                "size": len((text or "").encode("utf-8")),
                "sha256": _sha256_text(text or ""),
            }
        )
    for path, text in csv_files.items():
        files.append(
            {
                "path": f"events/{path}",
                "kind": "csv",
                "size": len((text or "").encode("utf-8")),
                "sha256": _sha256_text(text or ""),
            }
        )

    player_id = None
    try:
        roster_text = md_files.get("characters/roster.json") or md_files.get("roster.json")
        if roster_text:
            import json

            roster = json.loads(roster_text)
            if isinstance(roster, dict):
                for cid, item in roster.items():
                    if isinstance(item, dict) and bool(item.get("is_player", False)):
                        player_id = str(cid)
                        break
    except Exception:
        player_id = None

    return {
        "schema_version": schema_version,
        "mod_id": mod_id,
        "name": name,
        "author": author,
        "source": source,
        "base_version": base_version,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "entry": {"player_id": player_id},
        "files": files,
    }


def validate_manifest(manifest: Dict[str, Any], content: Dict[str, Dict[str, str]]) -> Tuple[bool, str]:
    if not isinstance(manifest, dict):
        return False, "manifest is not an object"
    for key in ["schema_version", "mod_id", "name", "author", "source", "files"]:
        if key not in manifest:
            return False, f"manifest missing field: {key}"

    files = manifest.get("files", [])
    if not isinstance(files, list):
        return False, "manifest.files must be list"

    md_files = content.get("md", {}) if isinstance(content, dict) else {}
    csv_files = content.get("csv", {}) if isinstance(content, dict) else {}
    expected = {}
    for path, text in md_files.items():
        expected[f"prompts/{path}"] = _sha256_text(text or "")
    for path, text in csv_files.items():
        expected[f"events/{path}"] = _sha256_text(text or "")

    for item in files:
        if not isinstance(item, dict):
            return False, "manifest.files item must be object"
        path = str(item.get("path", "")).strip()
        sha = str(item.get("sha256", "")).strip()
        if not path:
            return False, "manifest.files item missing path"
        if path not in expected:
            return False, f"manifest path not found in content: {path}"
        if sha != expected[path]:
            return False, f"hash mismatch: {path}"

    return True, "ok"

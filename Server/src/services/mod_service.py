import json
import os
import shutil
import tempfile
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException

from src.core.config import get_user_events_dir, get_user_prompts_dir


def package_mod(user_id: str):
    """将用户当前 active 目录打包为 Content 字典"""
    prompts_dir = get_user_prompts_dir(user_id)
    events_dir = get_user_events_dir(user_id)
    pack_content = {"md": {}, "csv": {}}

    if os.path.exists(prompts_dir):
        for root, _, files in os.walk(prompts_dir):
            for file in files:
                if file.endswith((".md", ".json")):
                    rel_path = os.path.relpath(os.path.join(root, file), prompts_dir)
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        pack_content["md"][rel_path] = f.read()

    if os.path.exists(events_dir):
        for file in os.listdir(events_dir):
            if file.endswith((".csv", ".json")):
                with open(os.path.join(events_dir, file), "r", encoding="utf-8-sig") as f:
                    pack_content["csv"][file] = f.read()
    return pack_content


def build_validation_report(
    content: dict,
    normalize_roster_single_player: Callable[[Dict[str, Any]], Dict[str, Any]],
    validate_manifest: Callable[[dict, dict], Any],
    manifest: Optional[dict] = None,
) -> Dict[str, Any]:
    errors = []
    warnings = []
    stats = {"md_files": 0, "csv_files": 0}

    if not isinstance(content, dict):
        errors.append("content 不是对象")
        return {"ok": False, "errors": errors, "warnings": warnings, "stats": stats}
    if "md" not in content or "csv" not in content:
        errors.append("content 缺少 md/csv 分组")
        return {"ok": False, "errors": errors, "warnings": warnings, "stats": stats}
    if not isinstance(content.get("md"), dict) or not isinstance(content.get("csv"), dict):
        errors.append("content.md/content.csv 必须是对象")
        return {"ok": False, "errors": errors, "warnings": warnings, "stats": stats}

    md_files = content.get("md", {})
    csv_files = content.get("csv", {})
    stats["md_files"] = len(md_files)
    stats["csv_files"] = len(csv_files)

    for p in md_files.keys():
        if ".." in str(p).replace("\\", "/"):
            errors.append(f"非法路径: md/{p}")
    for p in csv_files.keys():
        if ".." in str(p).replace("\\", "/"):
            errors.append(f"非法路径: csv/{p}")

    if "main_system.md" not in md_files and "main_author_note.md" not in md_files:
        warnings.append("未包含 main_system.md / main_author_note.md，可能只是局部补丁包")

    roster_text = md_files.get("characters/roster.json") or md_files.get("roster.json")
    if roster_text:
        try:
            roster = json.loads(roster_text)
            normalized = normalize_roster_single_player(roster)
            if normalized != roster:
                warnings.append("roster 存在多主角/无主角，系统会自动修正为唯一主角")
                md_files["characters/roster.json"] = json.dumps(normalized, ensure_ascii=False, indent=4)
        except Exception:
            errors.append("roster.json 不是合法 JSON")
    else:
        warnings.append("未包含 roster.json，主角配置将沿用当前 active")

    if manifest:
        ok, msg = validate_manifest(manifest, content)
        if not ok:
            errors.append(f"manifest 校验失败: {msg}")

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings, "stats": stats}


def validate_mod_content(
    content: dict,
    normalize_roster_single_player: Callable[[Dict[str, Any]], Dict[str, Any]],
    validate_manifest: Callable[[dict, dict], Any],
    manifest: Optional[dict] = None,
) -> Dict[str, Any]:
    report = build_validation_report(content, normalize_roster_single_player, validate_manifest, manifest)
    if not report.get("ok", False):
        raise HTTPException(status_code=400, detail="; ".join(report.get("errors", [])) or "Invalid mod content")
    return report


def apply_mod_content(user_id: str, content: dict):
    prompts_dir = get_user_prompts_dir(user_id)
    events_dir = get_user_events_dir(user_id)
    md_files = content.get("md", {})
    for rp, text in md_files.items():
        abs_p = os.path.join(prompts_dir, rp)
        os.makedirs(os.path.dirname(abs_p), exist_ok=True)
        with open(abs_p, "w", encoding="utf-8") as f:
            f.write(text)
    csv_files = content.get("csv", {})
    for fn, text in csv_files.items():
        abs_p = os.path.join(events_dir, fn)
        os.makedirs(os.path.dirname(abs_p), exist_ok=True)
        with open(abs_p, "w", encoding="utf-8") as f:
            f.write(text)


def apply_mod_content_atomic(
    user_id: str,
    content: dict,
    normalize_roster_single_player: Callable[[Dict[str, Any]], Dict[str, Any]],
    validate_manifest: Callable[[dict, dict], Any],
):
    validate_mod_content(content, normalize_roster_single_player, validate_manifest)
    prompts_dir = get_user_prompts_dir(user_id)
    events_dir = get_user_events_dir(user_id)

    if user_id == "default":
        apply_mod_content(user_id, content)
        return

    parent_prompts = os.path.dirname(prompts_dir)
    parent_events = os.path.dirname(events_dir)
    os.makedirs(parent_prompts, exist_ok=True)
    os.makedirs(parent_events, exist_ok=True)

    stage_prompts = tempfile.mkdtemp(prefix="staging_prompts_", dir=parent_prompts)
    stage_events = tempfile.mkdtemp(prefix="staging_events_", dir=parent_events)

    md_files = content.get("md", {})
    for rp, text in md_files.items():
        abs_p = os.path.join(stage_prompts, rp)
        os.makedirs(os.path.dirname(abs_p), exist_ok=True)
        with open(abs_p, "w", encoding="utf-8") as f:
            f.write(text)

    csv_files = content.get("csv", {})
    for fn, text in csv_files.items():
        abs_p = os.path.join(stage_events, fn)
        os.makedirs(os.path.dirname(abs_p), exist_ok=True)
        with open(abs_p, "w", encoding="utf-8") as f:
            f.write(text)

    backup_prompts = prompts_dir + ".bak"
    backup_events = events_dir + ".bak"
    try:
        if os.path.exists(backup_prompts):
            shutil.rmtree(backup_prompts, ignore_errors=True)
        if os.path.exists(backup_events):
            shutil.rmtree(backup_events, ignore_errors=True)

        if os.path.exists(prompts_dir):
            os.replace(prompts_dir, backup_prompts)
        if os.path.exists(events_dir):
            os.replace(events_dir, backup_events)

        os.replace(stage_prompts, prompts_dir)
        os.replace(stage_events, events_dir)

        shutil.rmtree(backup_prompts, ignore_errors=True)
        shutil.rmtree(backup_events, ignore_errors=True)
    except Exception as e:
        try:
            if os.path.exists(prompts_dir):
                shutil.rmtree(prompts_dir, ignore_errors=True)
            if os.path.exists(events_dir):
                shutil.rmtree(events_dir, ignore_errors=True)
            if os.path.exists(backup_prompts):
                os.replace(backup_prompts, prompts_dir)
            if os.path.exists(backup_events):
                os.replace(backup_events, events_dir)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Apply mod failed and rolled back: {e}")
    finally:
        shutil.rmtree(stage_prompts, ignore_errors=True)
        shutil.rmtree(stage_events, ignore_errors=True)


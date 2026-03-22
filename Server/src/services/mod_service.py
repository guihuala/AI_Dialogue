import json
import math
import os
import shutil
import tempfile
from datetime import datetime
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


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_record_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def write_record_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def summarize_content(content: Dict[str, Any]) -> Dict[str, Any]:
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


def normalize_library_record(record: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    data = dict(record or {})
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
    data["updated_at"] = str(data.get("updated_at", data.get("timestamp", now_str())) or now_str())
    data["timestamp"] = str(data.get("timestamp", data["updated_at"]) or data["updated_at"])
    data["summary"] = summarize_content(content)
    return data


def normalize_workshop_record(record: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(record or {})
    content = data.get("content", {}) if isinstance(data.get("content"), dict) else {"md": {}, "csv": {}}
    data["version"] = max(1, int(data.get("version", 1) or 1))
    data["visibility"] = "public"
    data["source_type"] = str(data.get("source_type", "original") or "original")
    data["source_mod_id"] = str(data.get("source_mod_id", "") or "")
    data["parent_workshop_id"] = str(data.get("parent_workshop_id", data.get("source_mod_id", "")) or "")
    data["published_at"] = str(data.get("published_at", data.get("timestamp", now_str())) or now_str())
    data["updated_at"] = str(data.get("updated_at", data.get("published_at", now_str())) or now_str())
    data["summary"] = summarize_content(content)
    return data


def build_library_record(
    *,
    item_id: str,
    user_id: str,
    name: str,
    description: str,
    content: Dict[str, Any],
    build_manifest: Callable[..., Dict[str, Any]],
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
    current_time = now_str()
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
        "timestamp": current_time,
        "updated_at": current_time,
        "summary": summarize_content(content),
    }


def build_workshop_record(
    *,
    item_id: str,
    linked_library_id: str,
    owner_user_id: str,
    name: str,
    author: str,
    description: str,
    content: Dict[str, Any],
    build_manifest: Callable[..., Dict[str, Any]],
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
    current_time = now_str()
    return {
        "id": item_id,
        "type": "prompt_pack",
        "name": name,
        "author": author,
        "description": description,
        "content": content,
        "manifest": manifest,
        "downloads": existing_downloads,
        "timestamp": existing_timestamp or current_time,
        "updated_at": current_time,
        "published_at": published_at or existing_timestamp or current_time,
        "owner_user_id": owner_user_id,
        "linked_library_id": linked_library_id,
        "version": max(1, int(version or 1)),
        "visibility": "public",
        "source_type": source_type,
        "source_mod_id": source_mod_id,
        "parent_workshop_id": parent_workshop_id or source_mod_id,
        "summary": summarize_content(content),
    }


def derive_focus_tags(summary: Dict[str, Any]) -> list[str]:
    data = summary or {}
    character_count = int(data.get("character_count", 0) or 0)
    skill_count = int(data.get("skill_count", 0) or 0)
    csv_count = int(data.get("csv_files", 0) or 0)
    world_count = int(data.get("world_count", 0) or 0)
    tags: list[str] = []

    if character_count >= 4:
        tags.append("偏角色向")
    if csv_count >= 3:
        tags.append("偏剧情向")
    if skill_count >= 2 or world_count >= 3:
        tags.append("偏系统向")

    if not tags:
        if character_count >= max(skill_count, csv_count):
            tags.append("轻角色向")
        elif csv_count >= max(character_count, skill_count):
            tags.append("轻剧情向")
        else:
            tags.append("轻系统向")
    return tags[:3]


def build_library_list_item(record: Dict[str, Any], upstream_record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    upstream_version = None
    has_update = False
    summary = record.get("summary", {})
    if upstream_record:
        upstream_version = int(upstream_record.get("version", 1) or 1)
        has_update = upstream_version > int(record.get("version", 1) or 1)
    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "description": record.get("description"),
        "author": record.get("author"),
        "timestamp": record.get("timestamp"),
        "source": record.get("manifest", {}).get("source", "library"),
        "base_version": record.get("manifest", {}).get("base_version", "default-v1"),
        "linked_workshop_id": record.get("linked_workshop_id", ""),
        "origin_workshop_id": record.get("origin_workshop_id", ""),
        "visibility": record.get("visibility", "private"),
        "version": record.get("version", 1),
        "source_type": record.get("source_type", "original"),
        "source_mod_id": record.get("source_mod_id", ""),
        "parent_workshop_id": record.get("parent_workshop_id", ""),
        "published_at": record.get("published_at", ""),
        "updated_at": record.get("updated_at", record.get("timestamp", "")),
        "summary": summary,
        "focus_tags": derive_focus_tags(summary),
        "upstream_version": upstream_version,
        "has_update": has_update,
    }


def build_workshop_list_item(record: Dict[str, Any], current_user_id: str) -> Dict[str, Any]:
    summary = record.get("summary", {})
    return {
        "id": record.get("id"),
        "type": record.get("type", "prompt_pack"),
        "name": record.get("name"),
        "author": record.get("author"),
        "description": record.get("description"),
        "downloads": record.get("downloads", 0),
        "timestamp": record.get("timestamp"),
        "updated_at": record.get("updated_at", ""),
        "published_at": record.get("published_at", ""),
        "summary": summary,
        "focus_tags": derive_focus_tags(summary),
        "version": record.get("version", 1),
        "source_type": record.get("source_type", "original"),
        "source_mod_id": record.get("source_mod_id", ""),
        "parent_workshop_id": record.get("parent_workshop_id", ""),
        "owner_user_id": record.get("owner_user_id", ""),
        "linked_library_id": record.get("linked_library_id", ""),
        "is_owned_by_current_user": str(record.get("owner_user_id", "")) == str(current_user_id),
    }


def build_mod_index_entry(record: Dict[str, Any], scope: str) -> Dict[str, Any]:
    focus_tags = derive_focus_tags(record.get("summary", {}) if isinstance(record.get("summary"), dict) else {})
    return {
        "id": record.get("id"),
        "scope": scope,
        "name": str(record.get("name", "") or ""),
        "author": str(record.get("author", "") or ""),
        "description": str(record.get("description", "") or ""),
        "visibility": str(record.get("visibility", "") or ""),
        "version": int(record.get("version", 1) or 1),
        "source_type": str(record.get("source_type", "") or ""),
        "updated_at": str(record.get("updated_at", record.get("timestamp", "")) or ""),
        "published_at": str(record.get("published_at", "") or ""),
        "focus_tags": focus_tags,
        "keywords": [
            str(record.get("name", "") or ""),
            str(record.get("author", "") or ""),
            str(record.get("description", "") or ""),
            str(record.get("source_type", "") or ""),
            *focus_tags,
        ],
    }


def load_library_record(path: str, user_id: str) -> Dict[str, Any]:
    return normalize_library_record(read_record_json(path), user_id)


def load_workshop_record(path: str) -> Dict[str, Any]:
    return normalize_workshop_record(read_record_json(path))


def list_library_records(lib_dir: str, user_id: str) -> list[Dict[str, Any]]:
    records: list[Dict[str, Any]] = []
    if not os.path.exists(lib_dir):
        return records
    for fn in os.listdir(lib_dir):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(lib_dir, fn)
        try:
            records.append(load_library_record(path, user_id))
        except Exception:
            continue
    return records


def list_workshop_records(workshop_dir: str) -> list[Dict[str, Any]]:
    records: list[Dict[str, Any]] = []
    if not os.path.exists(workshop_dir):
        return records
    for fn in sorted(os.listdir(workshop_dir), reverse=True):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(workshop_dir, fn)
        try:
            records.append(load_workshop_record(path))
        except Exception:
            continue
    return records


def query_mod_list(
    items: list[Dict[str, Any]],
    *,
    q: str = "",
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    source_type: str = "",
    visibility: str = "",
    focus_tag: str = "",
    owned_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> Dict[str, Any]:
    filtered = list(items)
    normalized_source_type = str(source_type or "").strip().lower()
    normalized_visibility = str(visibility or "").strip().lower()
    normalized_focus_tag = str(focus_tag or "").strip().lower()
    normalized_owned_only = bool(owned_only)

    if normalized_source_type:
        if normalized_source_type == "original":
            filtered = [
                item for item in filtered
                if str(item.get("source_type", "") or "").lower() not in {"downloaded", "forked"}
            ]
        else:
            filtered = [
                item for item in filtered
                if str(item.get("source_type", "") or "").lower() == normalized_source_type
            ]

    if normalized_visibility:
        filtered = [
            item for item in filtered
            if str(item.get("visibility", "") or "").lower() == normalized_visibility
        ]

    if normalized_focus_tag:
        filtered = [
            item
            for item in filtered
            if normalized_focus_tag in {
                str(tag or "").strip().lower()
                for tag in (item.get("focus_tags", []) if isinstance(item.get("focus_tags"), list) else [])
            }
        ]

    if normalized_owned_only:
        filtered = [item for item in filtered if bool(item.get("is_owned_by_current_user"))]

    query = str(q or "").strip().lower()
    if query:
        result: list[Dict[str, Any]] = []
        for item in filtered:
            index = item.get("index", {}) if isinstance(item.get("index"), dict) else {}
            haystacks = [
                str(item.get("name", "") or ""),
                str(item.get("author", "") or ""),
                str(item.get("description", "") or ""),
                str(index.get("source_type", "") or ""),
                str(index.get("visibility", "") or ""),
            ]
            keywords = index.get("keywords", [])
            if isinstance(keywords, list):
                haystacks.extend(str(keyword or "") for keyword in keywords)
            if query in " ".join(haystacks).lower():
                result.append(item)
        filtered = result

    reverse = str(sort_order or "desc").lower() != "asc"
    normalized_sort_by = str(sort_by or "updated_at").strip().lower()

    def _sort_value(item: Dict[str, Any]):
        if normalized_sort_by == "name":
            return str(item.get("name", "") or "").lower()
        if normalized_sort_by == "author":
            return str(item.get("author", "") or "").lower()
        if normalized_sort_by == "downloads":
            return int(item.get("downloads", 0) or 0)
        if normalized_sort_by == "version":
            return int(item.get("version", 1) or 1)
        if normalized_sort_by == "published_at":
            return str(item.get("published_at", "") or "")
        return str(item.get("updated_at", item.get("timestamp", "")) or "")

    filtered.sort(key=_sort_value, reverse=reverse)

    normalized_page_size = max(1, min(int(page_size or 50), 100))
    normalized_page = max(1, int(page or 1))
    total = len(filtered)
    total_pages = max(1, math.ceil(total / normalized_page_size)) if total else 1
    start = (normalized_page - 1) * normalized_page_size
    end = start + normalized_page_size
    paged = filtered[start:end]

    return {
        "items": paged,
        "pagination": {
            "page": normalized_page,
            "page_size": normalized_page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": normalized_page < total_pages,
            "has_prev": normalized_page > 1,
            "query": query,
            "sort_by": normalized_sort_by,
            "sort_order": "desc" if reverse else "asc",
            "source_type": normalized_source_type,
            "visibility": normalized_visibility,
            "focus_tag": normalized_focus_tag,
            "owned_only": normalized_owned_only,
        },
    }


def sync_library_record_with_upstream(
    library_data: Dict[str, Any],
    upstream_record: Dict[str, Any],
    *,
    build_manifest: Callable[..., Dict[str, Any]],
    item_id: str,
    user_id: str,
) -> Dict[str, Any]:
    synced = dict(library_data)
    synced["name"] = upstream_record.get("name", synced.get("name"))
    synced["description"] = upstream_record.get("description", synced.get("description"))
    synced["content"] = upstream_record.get("content", synced.get("content", {}))
    synced["manifest"] = build_manifest(
        mod_id=str(synced.get("id", item_id)),
        name=str(synced.get("name", item_id)),
        author=str(synced.get("author", f"User_{user_id[:4]}")),
        source="library",
        content=synced["content"],
    )
    synced["version"] = int(upstream_record.get("version", synced.get("version", 1)) or 1)
    synced["summary"] = summarize_content(synced["content"])
    synced["updated_at"] = now_str()
    synced["timestamp"] = synced["updated_at"]
    return synced


def resolve_publish_identity(
    *,
    current_library_item: Dict[str, Any],
    library_item: Optional[Dict[str, Any]],
    existing_workshop: Dict[str, Any],
    mode: str,
) -> Dict[str, Any]:
    source_type = str(current_library_item.get("source_type", "original") or "original")
    source_mod_id = str(current_library_item.get("source_mod_id", "") or "")
    parent_workshop_id = str(current_library_item.get("parent_workshop_id", "") or "")

    if mode == "fork":
        source_type = "forked"
        source_mod_id = source_mod_id or str(current_library_item.get("origin_workshop_id", "") or "")
        parent_workshop_id = parent_workshop_id or source_mod_id
    elif mode == "create":
        source_type = "original"
        source_mod_id = ""
        parent_workshop_id = ""

    next_version = int(existing_workshop.get("version", 0) or 0) + 1 if mode == "update" and existing_workshop else 1
    published_at = existing_workshop.get("published_at") if mode == "update" and existing_workshop else now_str()
    linked_workshop_id = str((library_item or {}).get("linked_workshop_id", "") or "").strip()

    return {
        "linked_workshop_id": linked_workshop_id,
        "source_type": source_type,
        "source_mod_id": source_mod_id,
        "parent_workshop_id": parent_workshop_id,
        "next_version": next_version,
        "published_at": published_at,
    }


def validate_publish_mode(current_library_item: Dict[str, Any], mode: str) -> None:
    current_source_type = str(current_library_item.get("source_type", "original") or "original")
    current_linked_workshop_id = str(current_library_item.get("linked_workshop_id", "") or "")
    current_visibility = str(current_library_item.get("visibility", "") or "")

    if mode == "update":
        if not current_linked_workshop_id or current_visibility != "public":
            raise HTTPException(status_code=400, detail="当前模组还没有公开版本，不能执行更新")
    elif mode == "fork":
        if current_source_type != "downloaded":
            raise HTTPException(status_code=400, detail="只有下载副本才能发布为派生作品")
    elif mode == "create":
        if current_linked_workshop_id and current_visibility == "public":
            raise HTTPException(status_code=400, detail="当前模组已有公开版本，请使用更新公开版本")


def resolve_publish_ids(
    *,
    mode: str,
    linked_workshop_id: str,
    make_id: Callable[[], str],
) -> Dict[str, str]:
    if mode == "update":
        workshop_id = linked_workshop_id or make_id()
    else:
        workshop_id = make_id()
    return {"workshop_id": workshop_id}


def build_publish_records(
    *,
    current_library_item: Dict[str, Any],
    library_id: str,
    workshop_id: str,
    existing_workshop: Dict[str, Any],
    mode: str,
    user_id: str,
    name: str,
    author: str,
    description: str,
    build_manifest: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    publish_meta = resolve_publish_identity(
        current_library_item=current_library_item,
        library_item=current_library_item,
        existing_workshop=existing_workshop,
        mode=mode,
    )
    content = current_library_item.get("content", {})
    workshop_record = build_workshop_record(
        item_id=workshop_id,
        linked_library_id=library_id,
        owner_user_id=user_id,
        name=name,
        author=author,
        description=description,
        content=content,
        build_manifest=build_manifest,
        existing_downloads=int(existing_workshop.get("downloads", 0) or 0),
        existing_timestamp=existing_workshop.get("timestamp"),
        version=int(publish_meta["next_version"]),
        source_type=str(publish_meta["source_type"]),
        source_mod_id=str(publish_meta["source_mod_id"]),
        parent_workshop_id=str(publish_meta["parent_workshop_id"]),
        published_at=str(publish_meta["published_at"]),
    )
    library_record = build_library_record(
        item_id=library_id,
        user_id=user_id,
        name=name,
        description=description,
        content=content,
        build_manifest=build_manifest,
        linked_workshop_id=workshop_id,
        visibility="public",
        version=int(publish_meta["next_version"]),
        source_type=str(publish_meta["source_type"]),
        source_mod_id=str(publish_meta["source_mod_id"]),
        parent_workshop_id=str(publish_meta["parent_workshop_id"]),
        published_at=str(publish_meta["published_at"]),
    )
    return {
        "publish_meta": publish_meta,
        "workshop_record": workshop_record,
        "library_record": library_record,
    }


def prepare_publish_bundle(
    *,
    current_library_item: Dict[str, Any],
    library_item: Optional[Dict[str, Any]],
    existing_workshop: Dict[str, Any],
    mode: str,
    user_id: str,
    name: str,
    author: str,
    description: str,
    build_manifest: Callable[..., Dict[str, Any]],
    make_id: Callable[[], str],
    library_id: str,
) -> Dict[str, Any]:
    validate_publish_mode(current_library_item, mode)
    linked_workshop_id = str((library_item or {}).get("linked_workshop_id", "") or "").strip()
    workshop_id = resolve_publish_ids(
        mode=mode,
        linked_workshop_id=linked_workshop_id,
        make_id=make_id,
    )["workshop_id"]
    records = build_publish_records(
        current_library_item=current_library_item,
        library_id=library_id,
        workshop_id=workshop_id,
        existing_workshop=existing_workshop,
        mode=mode,
        user_id=user_id,
        name=name,
        author=author,
        description=description,
        build_manifest=build_manifest,
    )
    return {
        "workshop_id": workshop_id,
        **records,
    }


def persist_publish_bundle(
    *,
    library_path: str,
    workshop_path: str,
    library_record: Dict[str, Any],
    workshop_record: Dict[str, Any],
    user_state: Dict[str, Any],
    write_record: Callable[[str, Dict[str, Any]], None],
    write_state: Callable[[Dict[str, Any]], None],
    library_id: str,
) -> Dict[str, Any]:
    write_record(library_path, library_record)
    write_record(workshop_path, workshop_record)

    updated_state = dict(user_state)
    updated_state["active_mod_id"] = library_id
    updated_state["active_source"] = "library"
    updated_state["active_content_hash"] = library_record.get("manifest", {}).get("mod_id", library_id)
    updated_state["updated_at"] = now_str()
    write_state(updated_state)
    return updated_state


def resolve_download_target(
    *,
    workshop_record: Dict[str, Any],
    user_id: str,
    library_exists: Callable[[str], bool],
    make_library_id: Callable[[], str],
    build_manifest: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    owner_user_id = str(workshop_record.get("owner_user_id", "") or "")
    linked_library_id = str(workshop_record.get("linked_library_id", "") or "").strip()
    if owner_user_id == str(user_id) and linked_library_id and library_exists(linked_library_id):
        return {
            "reuse_existing": True,
            "library_id": linked_library_id,
            "library_record": None,
        }

    library_id = make_library_id()
    source_mod_id = str(workshop_record.get("id", "") or "")
    library_record = build_library_record(
        item_id=library_id,
        user_id=user_id,
        name=workshop_record.get("name") or library_id,
        description=workshop_record.get("description") or "",
        content=workshop_record.get("content", {}),
        build_manifest=build_manifest,
        origin_workshop_id=source_mod_id,
        visibility="private",
        version=1,
        source_type="downloaded",
        source_mod_id=source_mod_id,
        parent_workshop_id=source_mod_id,
    )
    return {
        "reuse_existing": False,
        "library_id": library_id,
        "library_record": library_record,
    }


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

    has_legacy_main = ("main_system.md" in md_files) or ("main_author_note.md" in md_files)
    has_expression_main = (
        "system/expression_system_prompt.md" in md_files
        and "system/expression_user_prompt.md" in md_files
        and "system/expression_json_contract.md" in md_files
    )
    if not has_legacy_main and not has_expression_main:
        warnings.append(
            "未包含主提示词（legacy 或 expression-only），可能只是局部补丁包"
        )

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

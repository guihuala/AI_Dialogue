from typing import Any, Callable, Dict
from datetime import datetime
import json
import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from src.core.config import DATA_ROOT


class AdminFileSaveReq(BaseModel):
    type: str
    name: str
    content: str


class GenerateSkillPromptReq(BaseModel):
    concept: str


class AdminLoginReq(BaseModel):
    password: str


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
):
    router = APIRouter()
    accounts_by_id_dir = os.path.join(DATA_ROOT, "accounts", "by_id")
    accounts_sessions_dir = os.path.join(DATA_ROOT, "accounts", "sessions")

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

    return router

from typing import Any, Callable, Dict
import json
import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel


class AdminFileSaveReq(BaseModel):
    type: str
    name: str
    content: str


class GenerateSkillPromptReq(BaseModel):
    concept: str


def build_admin_router(
    *,
    get_user_id,
    get_engine: Callable[[str], Any],
    get_user_prompts_dir: Callable[[str], str],
    get_user_events_dir: Callable[[str], str],
    default_prompts_dir: str,
    default_events_dir: str,
    with_user_write_lock: Callable[[str], Any],
    append_audit_log: Callable[[str, str, str, str, Dict[str, Any]], None],
    normalize_roster_single_player: Callable[[Dict[str, Any]], Dict[str, Any]],
):
    router = APIRouter()

    @router.get("/api/admin/files")
    def get_admin_files(user_id: str = get_user_id):
        """获取所有剧情配置文件列表"""
        user_prompts_dir = get_user_prompts_dir(user_id)
        user_events_dir = get_user_events_dir(user_id)

        dirs_to_scan = [default_prompts_dir, user_prompts_dir]
        md_files_set = set()
        for d in dirs_to_scan:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for file in files:
                        if file.endswith((".md", ".json", ".csv")):
                            rel_path = os.path.relpath(os.path.join(root, file), d).replace("\\", "/")
                            md_files_set.add(rel_path)
        md_files = list(md_files_set)

        event_dirs = [default_events_dir, user_events_dir]
        csv_files_set = set()
        for d in event_dirs:
            if os.path.exists(d):
                for file in os.listdir(d):
                    if file.endswith((".csv", ".json")):
                        csv_files_set.add(file)
        csv_files = list(csv_files_set)

        return {"status": "success", "md": sorted(md_files), "csv": sorted(csv_files)}

    @router.get("/api/admin/file")
    def read_admin_file(type: str, name: str, user_id: str = get_user_id):
        """读取单个文件内容"""
        base_dir = get_user_prompts_dir(user_id) if type == "md" else get_user_events_dir(user_id)
        file_path = os.path.join(base_dir, name)

        if not os.path.exists(file_path):
            default_base = default_prompts_dir if type == "md" else default_events_dir
            file_path = os.path.join(default_base, name)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        with open(file_path, "r", encoding="utf-8") as f:
            return {"status": "success", "content": f.read()}

    @router.post("/api/admin/file")
    def save_admin_file(req: AdminFileSaveReq, user_id: str = get_user_id):
        """保存单个文件内容 (保存到用户私有目录)"""
        base_dir = get_user_prompts_dir(user_id) if req.type == "md" else get_user_events_dir(user_id)
        file_path = os.path.join(base_dir, req.name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with with_user_write_lock(user_id):
                content_to_write = req.content
                if req.type == "md" and req.name.endswith("roster.json"):
                    parsed = json.loads(req.content)
                    parsed = normalize_roster_single_player(parsed)
                    content_to_write = json.dumps(parsed, ensure_ascii=False, indent=4)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content_to_write)

                if req.type == "md" and req.name.endswith("roster.json"):
                    engine = get_engine(user_id)
                    if engine:
                        if hasattr(engine, "pm"):
                            engine.pm = type(engine.pm)(user_id)
                        if hasattr(engine, "player_name"):
                            engine.player_name = engine.pm.get_player_name() if hasattr(engine.pm, "get_player_name") else "陆陈安然"
            append_audit_log(user_id, "save_admin_file", "ok", f"{req.type}:{req.name}", {})
            return {"status": "success", "message": f"{req.name} 保存成功"}
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

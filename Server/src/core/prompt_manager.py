import os
import csv
import json
import re
from typing import Any, Dict, List, Tuple

from src.core.config import get_user_data_root, get_user_prompts_dir, DEFAULT_PROMPTS_DIR

class PromptManager:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.prompts_dir = get_user_prompts_dir(user_id)
        self.default_prompts_dir = DEFAULT_PROMPTS_DIR
        self._file_cache = {}
        self._relationship_cache = {"path": None, "mtime": None, "rows": []}
        
        self.skills_dir = os.path.join(self.prompts_dir, "skills")
        self.world_dir = os.path.join(self.prompts_dir, "world")
        self.chars_dir = os.path.join(self.prompts_dir, "characters") 
        
        # Ensure user directories exist
        os.makedirs(self.skills_dir, exist_ok=True)
        os.makedirs(self.world_dir, exist_ok=True)
        os.makedirs(self.chars_dir, exist_ok=True)
        
        # 注册系统动态技能库
        self.skills = {
            "slang_dict": self._skill_slang_dict,
            "academic_world": self._skill_academic_world,
            "character_roster": self._skill_character_roster, 
            "relationship_matrix": self._skill_relationship_matrix,
            "secret_note": self._skill_secret_note,
            "relationship_milestone": self._skill_relationship_milestone,
            "user_skills": self._skill_user_defined_loader 
        }
        self.default_enabled_skills = list(self.skills.keys())

        # 动态角色文件映射
        self.roster_data = self._load_roster_data()
        self.char_file_map = self._load_char_file_map()
        self.player_name = self._resolve_player_name()
        self.player_file = self.char_file_map.get(self.player_name, "")
        self._compact_author_note_cache = None

    def _nonempty_blocks(self, blocks):
        return [str(block).strip() for block in blocks if str(block).strip()]

    def _load_roster_data(self) -> dict:
        mapping_file = os.path.join(self.chars_dir, "roster.json")
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                print(f"Failed to load dynamic roster data: {e}")
        return {}

    def _skill_user_defined_loader(self, context: dict) -> str:
        """动态加载 skills/ 目录下除系统保留文件以外的所有 .md 技能块（支持结构化元数据）"""
        user_skills: List[str] = []
        for item in self.get_user_skill_catalog(context):
            if not bool(item.get("active", True)):
                continue
            content = item.get("content", "")
            if not content:
                continue
            display_name = str(item.get("name") or item.get("file") or "custom_skill")
            tags = item.get("tags") if isinstance(item.get("tags"), list) else []
            tags_text = f"（{', '.join(str(x) for x in tags if str(x).strip())}）" if tags else ""
            user_skills.append(f"【系统扩展插件: {display_name}{tags_text}】\n{content}")

        return "\n\n".join(user_skills) if user_skills else ""

    def _parse_front_matter(self, raw: str) -> Tuple[Dict[str, Any], str]:
        text = str(raw or "")
        if not text.startswith("---"):
            return {}, text
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, text

        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
        if end_idx <= 0:
            return {}, text

        meta: Dict[str, Any] = {}
        for line in lines[1:end_idx]:
            row = line.strip()
            if not row or row.startswith("#") or ":" not in row:
                continue
            k, v = row.split(":", 1)
            key = str(k).strip()
            value_raw = str(v).strip()
            if not key:
                continue
            meta[key] = self._parse_front_matter_value(value_raw)

        body = "\n".join(lines[end_idx + 1 :]).strip()
        return meta, body

    def _parse_front_matter_value(self, value: str) -> Any:
        s = str(value or "").strip()
        if not s:
            return ""
        low = s.lower()
        if low in {"true", "yes", "on"}:
            return True
        if low in {"false", "no", "off"}:
            return False
        if re.fullmatch(r"-?\d+", s):
            try:
                return int(s)
            except Exception:
                pass
        if re.fullmatch(r"-?\d+\.\d+", s):
            try:
                return float(s)
            except Exception:
                pass
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            try:
                return json.loads(s)
            except Exception:
                pass
        if "," in s:
            return [x.strip() for x in s.split(",") if x.strip()]
        return s.strip().strip('"').strip("'")

    def _is_user_skill_active_for_context(self, meta: Dict[str, Any], context: Dict[str, Any]) -> bool:
        enabled = meta.get("enabled", True)
        if isinstance(enabled, bool) and not enabled:
            return False

        when = str(meta.get("when", "always") or "always").strip().lower()
        if when in {"", "always"}:
            return True
        event_type = str(context.get("event_type", "") or context.get("event_kind", "") or "").strip().lower()
        is_key_event = bool(context.get("system_key_resolution")) or ("key" in event_type)
        if when == "key_event":
            return is_key_event
        if when == "daily_event":
            return not is_key_event
        if when == "transition":
            return bool(context.get("is_transition"))
        return True

    def get_user_skill_catalog(self, context: dict = None) -> List[Dict[str, Any]]:
        context = context or {}
        out: List[Dict[str, Any]] = []
        if not os.path.exists(self.skills_dir):
            return out

        for file in sorted(os.listdir(self.skills_dir)):
            if not file.endswith(".md") or file.startswith("slang_chapter_"):
                continue
            raw = self._read_md(f"skills/{file}")
            if not raw:
                continue
            meta, body = self._parse_front_matter(raw)
            record = {
                "file": file,
                "file_path": f"skills/{file}",
                "id": str(meta.get("id") or os.path.splitext(file)[0]).strip(),
                "name": str(meta.get("name") or os.path.splitext(file)[0]).strip(),
                "description": str(meta.get("description") or "").strip(),
                "enabled": bool(meta.get("enabled", True)),
                "priority": int(meta.get("priority", 100) or 100),
                "target": str(meta.get("target") or "").strip(),
                "when": str(meta.get("when") or "always").strip(),
                "tags": meta.get("tags") if isinstance(meta.get("tags"), list) else [],
                "meta": meta,
                "content": body.strip(),
            }
            record["active"] = self._is_user_skill_active_for_context(meta, context) and bool(record["content"])
            out.append(record)

        out.sort(key=lambda x: (int(x.get("priority", 100)), str(x.get("name", ""))))
        return out

    def _resolve_player_name(self) -> str:
        for _, profile in self.roster_data.items():
            if isinstance(profile, dict) and bool(profile.get("is_player", False)):
                name = str(profile.get("name", "")).strip()
                if name:
                    return name
        return "陆陈安然"

    def get_player_name(self) -> str:
        return self.player_name

    def get_player_file(self) -> str:
        return self.player_file

    def get_player_profile_text(self, player_name: str = None) -> str:
        target_name = (player_name or self.get_player_name() or "").strip()
        player_file = self.char_file_map.get(target_name, "") or self.get_player_file()
        if not player_file:
            return ""
        return self._read_md(f"characters/{player_file}")

    def _get_active_chars(self, context: dict = None) -> list:
        context = context or {}
        active_chars = context.get("active_chars", []) or []
        return [str(char).strip() for char in list(active_chars) if str(char).strip()]

    def _build_player_template_vars(self, context: dict = None) -> dict:
        context = context or {}
        player_name = context.get("player_name", self.get_player_name()) or self.get_player_name()
        player_profile = self.get_player_profile_text(player_name).strip()
        if not player_profile:
            player_profile = f"当前玩家主角是 {player_name}。请基于其角色设定生成符合人设的反应。"

        return {
            "PLAYER_NAME": player_name,
            "PLAYER_PROFILE": player_profile,
            "PLAYER_VIEW_LABEL": f"{player_name}视角",
        }

    def _build_template_vars(self, context: dict = None) -> dict:
        context = context or {}
        vars_map = self._build_player_template_vars(context)

        active_chars = self._get_active_chars(context)
        members = context.get("members")
        if isinstance(members, (list, tuple)):
            members_text = "、".join(str(item).strip() for item in members if str(item).strip())
        else:
            members_text = str(members or "").strip()
        if not members_text and active_chars:
            members_text = "、".join(active_chars)

        extra_vars = {
            "CHANNEL_NAME": str(context.get("channel_name", "") or "").strip(),
            "MEMBERS": members_text,
        }

        for key, value in context.items():
            if not isinstance(key, str):
                continue
            placeholder_key = key.strip().upper()
            if not placeholder_key or placeholder_key in vars_map:
                continue
            if isinstance(value, (str, int, float, bool)):
                extra_vars[placeholder_key] = str(value)

        vars_map.update(extra_vars)
        return vars_map

    def _render_prompt_template(self, text: str, context: dict = None) -> str:
        if not text:
            return text

        vars_map = self._build_template_vars(context)
        rendered = text
        for key, value in vars_map.items():
            rendered = rendered.replace(f"[{key}]", value)
            rendered = rendered.replace(f"{{{{{key}}}}}", value)

        player_name = vars_map["PLAYER_NAME"]
        if player_name and player_name != "陆陈安然":
            rendered = re.sub(r"(?<![\[\{])陆陈安然(?![\]\}])", player_name, rendered)
        return rendered

    def render_prompt_file(self, relative_path: str, context: dict = None) -> str:
        return self._render_prompt_template(self._read_md(relative_path), context)

    def get_roster_name_map(self) -> dict:
        """
        返回 {角色ID: 角色名}，供引擎把前端提交的 id 转换为名字。
        """
        out = {}
        for cid, profile in self.roster_data.items():
            if isinstance(profile, dict):
                name = str(profile.get("name", "")).strip()
                if name:
                    out[str(cid)] = name
        return out

    def _load_char_file_map(self) -> dict:
        default_map = {
            "陆陈安然": "player_anran.md",
            "唐梦琪": "tang_mengqi.md",
            "陈雨婷": "chen_yuting.md",
            "李一诺": "li_yinuo.md",
            "苏浅": "su_qian.md",
            "赵鑫": "zhao_xin.md",
            "林飒": "lin_sa.md"
        }
        
        if self.roster_data:
            try:
                new_map = {}
                for _, profile in self.roster_data.items():
                    if not isinstance(profile, dict):
                        continue
                    name = profile.get("name")
                    filename = profile.get("file")
                    if name and filename:
                        new_map[str(name)] = str(filename)
                if new_map:
                    return new_map
            except Exception as e:
                print(f"Failed to load dynamic roster: {e}")
        
        # fallback: scan directory if no mapping exists, using filenames as names (simplified)
        # But for now, returning default_map is safer to avoid breaking old characters
        return default_map

    def _read_md(self, relative_path: str) -> str:
        if not relative_path:
            return ""

        def _read_with_cache(abs_path: str) -> str:
            try:
                mtime = os.path.getmtime(abs_path)
                cached = self._file_cache.get(abs_path)
                if cached and cached.get("mtime") == mtime:
                    return cached.get("content", "")
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                self._file_cache[abs_path] = {"mtime": mtime, "content": content}
                return content
            except Exception:
                return ""

        # 1. 优先尝试用户专属路径
        user_path = os.path.join(self.prompts_dir, relative_path)
        if os.path.exists(user_path) and not os.path.isdir(user_path):
            return _read_with_cache(user_path)

        # 2. 回退到默认公共路径
        default_path = os.path.join(self.default_prompts_dir, relative_path)
        if os.path.exists(default_path) and not os.path.isdir(default_path):
            return _read_with_cache(default_path)

        return ""

    def _get_relationship_rows(self) -> list:
        rel_csv_path = os.path.join(self.chars_dir, "relationship.csv")
        if not os.path.exists(rel_csv_path):
            return []

        try:
            mtime = os.path.getmtime(rel_csv_path)
            cached = self._relationship_cache
            if cached.get("path") == rel_csv_path and cached.get("mtime") == mtime:
                return cached.get("rows", [])

            rows = []
            with open(rel_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
            self._relationship_cache = {"path": rel_csv_path, "mtime": mtime, "rows": rows}
            return rows
        except Exception:
            return []

    def _skill_slang_dict(self, context: dict) -> str:
        chapter = context.get("chapter", 1)
        return self._read_md(f"skills/slang_chapter_{chapter}.md")

    def _skill_academic_world(self, context: dict) -> str:
        world_text = self._read_md("world/base_setting.md") + "\n"
        event_desc = context.get("event_description", "")
        event_name = context.get("event_name", "")
        if any(keyword in event_desc + event_name for keyword in ["课", "教室", "期末", "老师", "班长", "作业", "发表", "图书馆"]):
            if str(context.get("prompt_budget", "full")).lower() == "compact":
                world_text += "\n" + self._get_compact_academic_npcs()
            else:
                world_text += "\n" + self._read_md("world/academic_npcs.md")
            world_text += "\n⚠️【指令】：当前处于教学区，请在对话中自然引入上述老师或同学的互动，维持他们的性格设定；如果配角是第一次在本事件出场，务必顺手交代她/他是谁。\n"
        return world_text

    def _skill_character_roster(self, context: dict) -> str:
        active_chars = self._get_active_chars(context)
        player_name = context.get("player_name", self.get_player_name())
        if player_name not in active_chars: active_chars.append(player_name)
        if str(context.get("prompt_budget", "full")).lower() == "compact":
            compact_profiles = []
            for _, profile in self.roster_data.items():
                if not isinstance(profile, dict):
                    continue
                name = str(profile.get("name", "")).strip()
                if not name or name not in active_chars:
                    continue
                archetype = str(profile.get("archetype", "")).strip()
                description = str(profile.get("description", "")).strip()
                tags = [str(tag).strip() for tag in profile.get("tags", []) if str(tag).strip()]
                compact_profiles.append(
                    f"- {name}：{archetype or '角色'}。{description[:48]}{'…' if len(description) > 48 else ''}"
                    + (f" 关键词：{'、'.join(tags[:3])}" if tags else "")
                )
            if compact_profiles:
                return "👥【在场角色速览】\n" + "\n".join(compact_profiles)
        profiles = []
        for char in active_chars:
            if char in self.char_file_map:
                md_content = self._read_md(f"characters/{self.char_file_map[char]}")
                if md_content: profiles.append(md_content)
        if profiles: return "👥【在场角色核心级设定与语料库】（请严格遵循以下设定描写细节与语气）：\n" + "\n---\n".join(profiles)
        return ""

    def _get_compact_academic_npcs(self) -> str:
        return (
            "【教学区常见配角速览】\n"
            "- 陈砚秋：编导专业老师，毒舌但负责，抓作业细节很狠。\n"
            "- 张桂芳：宿管阿姨，查寝严格，但关键时刻会护学生。\n"
            "- 林一航：大四学长，影视工作室主理人，技术强、话少。\n"
            "- 苏念：同班卷王，成绩和比赛都很强，小组作业能带飞全场。\n"
            "- 这些配角若首次出场，要顺手让玩家知道“她/他是谁”。"
        )

    def _skill_relationship_matrix(self, context: dict) -> str:
        active_chars = self._get_active_chars(context)
        player_name = context.get("player_name", self.get_player_name())
        if player_name not in active_chars: active_chars.append(player_name)
        compact_mode = str(context.get("prompt_budget", "full")).lower() == "compact"

        relations = []
        try:
            for row in self._get_relationship_rows():
                source = row.get("评价者", "").strip()
                target = row.get("被评价者", "").strip()

                # 必须“评价者”和“被评价者”同时在场，才触发关系
                # 否则会引发不在场角色的名字污染大模型，导致幽灵室友出现
                if source in active_chars and target in active_chars:
                    surface = row.get("表面态度", "").strip()
                    inner = row.get("内心真实评价", "").strip()
                    if compact_mode:
                        summary = inner or surface
                        if len(summary) > 24:
                            summary = summary[:24] + "…"
                        relations.append(f"- {source} -> {target}：{summary}")
                    else:
                        relations.append(f"- 【{source}】对待【{target}】：表面上展现出[{surface}]，内心实际上觉得[{inner}]。")
        except Exception as e:
            print(f"关系矩阵读取失败: {e}")
        
        if relations:
            if compact_mode:
                return "【在场关系速览】\n" + "\n".join(relations[:8])
            return "【人物社交网络】（请根据以下关系，精准把控在场角色的语言温度、暗场动作及阴阳怪气程度）：\n" + "\n".join(relations)
        return ""

    def _skill_secret_note(self, context: dict) -> str:
        return self._read_md("skills/secret_note.md")

    def _skill_relationship_milestone(self, context: dict) -> str:
        return self._read_md("skills/relationship_milestone.md")
        
    def get_main_system_prompt_bundle(self, context: dict) -> dict:
        base_prompt = self.render_prompt_file("main_system.md", context)
        active_skills = []
        enabled = set(self.get_enabled_skills())
        for skill_name, skill_func in self.skills.items():
            if skill_name not in enabled:
                continue
            skill_text = skill_func(context)
            if skill_text: active_skills.append(skill_text)

        rag_lore = context.get("rag_lore", "")
        trimmable_blocks = []
        if rag_lore:
            trimmable_blocks.append(f"【专属语料检索命中】（如果以下语料符合当前情境，请优先引用）：\n{rag_lore}")

        repeated_blocks = list(active_skills)
        skills_payload = self._nonempty_blocks(repeated_blocks + trimmable_blocks)
        skills_str = "\n\n[已加载的系统动态插件 (Skills)]\n" + "\n".join(skills_payload) if skills_payload else ""

        mod_override = ""
        custom_prompts = context.get("custom_prompts", {}) or {}
        c_world, c_events, c_char = custom_prompts.get("world"), custom_prompts.get("events"), custom_prompts.get("character")
        if c_world or c_events or c_char:
            mod_override = "\n\n🚀【玩家深度干预 MOD (Local Overrides)】（最高优先级硬性设定，无条件覆盖默认）：\n"
            if c_world: mod_override += f"🌍 [世界观重构]:\n{c_world}\n"
            if c_events: mod_override += f"📜 [事件流干预]:\n{c_events}\n"
            if c_char: mod_override += f"👤 [角色灵魂修正]:\n{c_char}\n"
            skills_str += mod_override

        if "[ACTIVE_SKILLS]" in base_prompt:
            final_prompt = base_prompt.replace("[ACTIVE_SKILLS]", skills_str)
        else:
            final_prompt = base_prompt + skills_str

        return {
            "static_blocks": self._nonempty_blocks([base_prompt.replace("[ACTIVE_SKILLS]", "").strip()]),
            "repeated_blocks": self._nonempty_blocks(repeated_blocks),
            "dynamic_blocks": self._nonempty_blocks([mod_override]),
            "trimmable_blocks": self._nonempty_blocks(trimmable_blocks),
            "final_prompt": final_prompt,
        }

    def get_main_system_prompt(self, context: dict) -> str:
        bundle = self.get_main_system_prompt_bundle(context)
        return bundle.get("final_prompt", "")

    def get_mod_features(self) -> Dict[str, Any]:
        """
        从模组可编辑文件读取系统开关。
        约定路径：prompts/system/mod_features.json
        """
        raw = self._read_md("system/mod_features.json")
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _skill_profile_path(self) -> str:
        return os.path.join(get_user_data_root(self.user_id), "skill_profile.json")

    def get_skill_profile(self) -> Dict[str, Any]:
        path = self._skill_profile_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def get_enabled_skills(self, context: dict = None) -> list[str]:
        context = context or {}
        features = self.get_mod_features()
        profile = self.get_skill_profile()
        raw = features.get("enabled_skills")
        auto_new_skills = {"secret_note", "relationship_milestone"}
        disabled = set()
        disabled_raw = features.get("disabled_skills")
        if isinstance(disabled_raw, list):
            for item in disabled_raw:
                name = str(item or "").strip()
                if name:
                    disabled.add(name)
        if isinstance(raw, list):
            enabled = []
            for item in raw:
                name = str(item or "").strip()
                if name and name in self.skills:
                    enabled.append(name)
            for name in auto_new_skills:
                if name in self.skills and name not in enabled and name not in disabled:
                    enabled.append(name)
            if enabled:
                base_enabled = enabled
            else:
                base_enabled = [x for x in list(self.default_enabled_skills) if x not in disabled]
        else:
            base_enabled = [x for x in list(self.default_enabled_skills) if x not in disabled]

        result = set(base_enabled)
        # profile 全局覆盖（解耦后主入口）
        prof_skills = profile.get("skills", {}) if isinstance(profile.get("skills", {}), dict) else {}
        for name, item in prof_skills.items():
            sid = str(name or "").strip()
            if not sid or sid not in self.skills:
                continue
            enabled_v = bool(item.get("enabled", True)) if isinstance(item, dict) else bool(item)
            if enabled_v:
                result.add(sid)
            else:
                result.discard(sid)

        # 可选：按 mod_id 覆盖
        mod_id = str(context.get("mod_id", "") or "").strip()
        overrides = profile.get("per_mod_overrides", {}) if isinstance(profile.get("per_mod_overrides", {}), dict) else {}
        mod_cfg = overrides.get(mod_id, {}) if mod_id else {}
        if isinstance(mod_cfg, dict):
            mod_skills = mod_cfg.get("skills", {}) if isinstance(mod_cfg.get("skills", {}), dict) else {}
            for name, item in mod_skills.items():
                sid = str(name or "").strip()
                if not sid or sid not in self.skills:
                    continue
                enabled_v = bool(item.get("enabled", True)) if isinstance(item, dict) else bool(item)
                if enabled_v:
                    result.add(sid)
                else:
                    result.discard(sid)
        return sorted(list(result))

    def is_phone_system_enabled(self, context: dict = None) -> bool:
        context = context or {}
        features = self.get_mod_features()
        profile = self.get_skill_profile()
        value = features.get("phone_system_enabled", features.get("wechat_system_enabled", True))
        enabled = bool(value)
        global_cfg = profile.get("global", {}) if isinstance(profile.get("global", {}), dict) else {}
        if "phone_system_enabled" in global_cfg:
            enabled = bool(global_cfg.get("phone_system_enabled"))
        mod_id = str(context.get("mod_id", "") or "").strip()
        overrides = profile.get("per_mod_overrides", {}) if isinstance(profile.get("per_mod_overrides", {}), dict) else {}
        mod_cfg = overrides.get(mod_id, {}) if mod_id else {}
        if isinstance(mod_cfg, dict) and "phone_system_enabled" in mod_cfg:
            enabled = bool(mod_cfg.get("phone_system_enabled"))
        return enabled

    def get_expression_flavor_context(self, context: dict) -> str:
        """
        expression-only 模式下的轻量设定注入：
        保留世界观/角色差异，同时控制长度避免显著增加延迟。
        """
        compact_ctx = dict(context or {})
        compact_ctx["prompt_budget"] = "compact"

        blocks = []
        enabled = set(self.get_enabled_skills(context))

        if "academic_world" in enabled:
            world_text = self._skill_academic_world(compact_ctx)
            if world_text:
                blocks.append(world_text.strip())

        if "character_roster" in enabled:
            char_text = self._skill_character_roster(compact_ctx)
            if char_text:
                blocks.append(char_text.strip())

        if "relationship_matrix" in enabled:
            rel_text = self._skill_relationship_matrix(compact_ctx)
            if rel_text:
                blocks.append(rel_text.strip())

        if not blocks:
            return ""

        merged = "\n\n".join(blocks).strip()
        if len(merged) > 900:
            merged = merged[:900].rstrip() + "…"
        return merged

    def get_main_author_note(self, context: dict = None, compact: bool = False) -> str:
        context = context or {}
        if compact:
            if self._compact_author_note_cache is None:
                self._compact_author_note_cache = (
                    "[稳定输出简表]\n"
                    "1. 只输出一个合法 JSON 对象。\n"
                    "2. 必须包含 narrator_transition/current_scene/dialogue_sequence/next_options/effects/is_end。\n"
                    "3. dialogue_sequence 的每一项都必须是对象，且只能包含 speaker/content 两个字段。\n"
                    "4. 严禁输出 _note、_comment、placeholder、explanation、数组长度说明、自我校验说明。\n"
                    "5. 不要把“内部备注”“模型思考”“为了满足 schema”之类内容写进 JSON。\n"
                    "6. 内心独白也必须写成正常 dialogue item，例如 speaker='陆陈安然'、content='(内心独白)...'。\n"
                    "7. dialogue_sequence 优先给 4-8 条有效互动。\n"
                    "8. next_options 给 3-4 个有明显策略差异的可执行选项。\n"
                    "8.1 严禁使用“继续剧情...”这类占位词做选项文案。\n"
                    "9. effects 只表达数值变化；手机消息优先使用 phone_enqueue_message 工具调用，不要输出多余字段。\n"
                    "10. 不要解释规则，不要输出代码块。"
                )
            return self._render_prompt_template(self._compact_author_note_cache, context)
        return self.render_prompt_file("main_author_note.md", context)

    def get_wechat_system_prompt(self, context: dict = None) -> str:
        context = context or {}
        return self.render_prompt_file("wechat_system.md", context)

    def get_all_relationships(self) -> str:
        """提取全局角色认知网络与底层偏见"""
        if not os.path.exists(os.path.join(self.chars_dir, "relationship.csv")):
            return "认知拓扑文件(relationship.csv)缺失"
        
        lines = []
        try:
            for row in self._get_relationship_rows():
                source = row.get("评价者", "").strip()
                target = row.get("被评价者", "").strip()
                surface = row.get("表面态度", "").strip()
                inner = row.get("内心真实评价", "").strip()
                lines.append(f"[{source} ➡️  {target}] 表面: {surface} | 内心: {inner}")
        except Exception as e:
            return f"认知拓扑解码失败: {e}"
            
        return "\n".join(lines) if lines else "认知拓扑未挂载任何节点"

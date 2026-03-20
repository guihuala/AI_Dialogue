import os
import csv
import json
import re

from src.core.config import get_user_prompts_dir, DEFAULT_PROMPTS_DIR

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
            "user_skills": self._skill_user_defined_loader 
        }

        # 动态角色文件映射
        self.roster_data = self._load_roster_data()
        self.char_file_map = self._load_char_file_map()
        self.player_name = self._resolve_player_name()
        self.player_file = self.char_file_map.get(self.player_name, "")

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
        """动态加载 skills/ 目录下除系统保留文件以外的所有 .md 技能块"""
        user_skills = []
        if os.path.exists(self.skills_dir):
            for file in os.listdir(self.skills_dir):
                # 排除系统内置或专有逻辑处理的文件（如 slang_chapter_x.md）
                if file.endswith(".md") and not file.startswith("slang_chapter_"):
                    content = self._read_md(f"skills/{file}")
                    if content:
                        # 自动解析 ID 描述，通过文件名的首行或备注
                        user_skills.append(f"【系统扩展插件: {file}】\n{content}")
        
        return "\n\n".join(user_skills) if user_skills else ""

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
            world_text += "\n" + self._read_md("world/academic_npcs.md")
            world_text += "\n⚠️【指令】：当前处于教学区，请在对话中自然引入上述老师或同学的互动，维持他们的性格设定；如果配角是第一次在本事件出场，务必顺手交代她/他是谁。\n"
        return world_text

    def _skill_character_roster(self, context: dict) -> str:
        active_chars = self._get_active_chars(context)
        player_name = context.get("player_name", self.get_player_name())
        if player_name not in active_chars: active_chars.append(player_name)
        profiles = []
        for char in active_chars:
            if char in self.char_file_map:
                md_content = self._read_md(f"characters/{self.char_file_map[char]}")
                if md_content: profiles.append(md_content)
        if profiles: return "👥【在场角色核心级设定与语料库】（请严格遵循以下设定描写细节与语气）：\n" + "\n---\n".join(profiles)
        return ""

    def _skill_relationship_matrix(self, context: dict) -> str:
        active_chars = self._get_active_chars(context)
        player_name = context.get("player_name", self.get_player_name())
        if player_name not in active_chars: active_chars.append(player_name)

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
                    relations.append(f"- 【{source}】对待【{target}】：表面上展现出[{surface}]，内心实际上觉得[{inner}]。")
        except Exception as e:
            print(f"关系矩阵读取失败: {e}")
        
        if relations:
            return "【人物社交网络】（请根据以下关系，精准把控在场角色的语言温度、暗场动作及阴阳怪气程度）：\n" + "\n".join(relations)
        return ""
        
    def get_main_system_prompt(self, context: dict) -> str:
        base_prompt = self.render_prompt_file("main_system.md", context)
        active_skills = []
        for skill_name, skill_func in self.skills.items():
            skill_text = skill_func(context)
            if skill_text: active_skills.append(skill_text)
                
        rag_lore = context.get("rag_lore", "")
        if rag_lore: active_skills.append(f"【专属语料检索命中】（如果以下语料符合当前情境，请优先引用）：\n{rag_lore}")

        skills_str = "\n\n[已加载的系统动态插件 (Skills)]\n" + "\n".join(active_skills) if active_skills else ""
        
        custom_prompts = context.get("custom_prompts", {}) or {}
        c_world, c_events, c_char = custom_prompts.get("world"), custom_prompts.get("events"), custom_prompts.get("character")
        if c_world or c_events or c_char:
            mod_override = "\n\n🚀【玩家深度干预 MOD (Local Overrides)】（最高优先级硬性设定，无条件覆盖默认）：\n"
            if c_world: mod_override += f"🌍 [世界观重构]:\n{c_world}\n"
            if c_events: mod_override += f"📜 [事件流干预]:\n{c_events}\n"
            if c_char: mod_override += f"👤 [角色灵魂修正]:\n{c_char}\n"
            skills_str += mod_override

        if "[ACTIVE_SKILLS]" in base_prompt: return base_prompt.replace("[ACTIVE_SKILLS]", skills_str)
        return base_prompt + skills_str

    def get_main_author_note(self, context: dict = None) -> str:
        context = context or {}
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

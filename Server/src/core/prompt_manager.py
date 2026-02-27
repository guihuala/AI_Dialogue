import os

class PromptManager:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.prompts_dir = os.path.join(base_dir, "data", "prompts")
        self.skills_dir = os.path.join(self.prompts_dir, "skills")
        self.world_dir = os.path.join(self.prompts_dir, "world")
        self.chars_dir = os.path.join(self.prompts_dir, "characters") 
        
        os.makedirs(self.skills_dir, exist_ok=True)
        os.makedirs(self.world_dir, exist_ok=True)
        os.makedirs(self.chars_dir, exist_ok=True)
        
        self._init_default_prompt_files()
        
        self.skills = {
            "slang_dict": self._skill_slang_dict,
            "academic_world": self._skill_academic_world,
            "character_roster": self._skill_character_roster, 
        }

        self.char_file_map = {
            "陆陈安然": "player_anran.md",
            "唐梦琪": "tang_mengqi.md",
            "陈雨婷": "chen_yuting.md",
            "李一诺": "li_yinuo.md",
            "苏浅": "su_qian.md",
            "赵鑫": "zhao_xin.md",
            "林飒": "lin_sa.md"
        }

    def _read_md(self, relative_path: str) -> str:
        file_path = os.path.join(self.prompts_dir, relative_path)
        if not os.path.exists(file_path): return ""
        with open(file_path, 'r', encoding='utf-8') as f: return f.read().strip()

    def _skill_slang_dict(self, context: dict) -> str:
        chapter = context.get("chapter", 1)
        return self._read_md(f"skills/slang_chapter_{chapter}.md")

    def _skill_academic_world(self, context: dict) -> str:
        world_text = self._read_md("world/base_setting.md") + "\n"
        event_desc = context.get("event_description", "")
        event_name = context.get("event_name", "")
        if any(keyword in event_desc + event_name for keyword in ["课", "教室", "期末", "老师", "班长", "作业", "发表", "图书馆"]):
            world_text += "\n" + self._read_md("world/academic_npcs.md")
            world_text += "\n⚠️【指令】：当前处于教学区，请在对话中自然引入上述老师或同学的互动，维持他们的性格设定！\n"
        return world_text

    def _skill_character_roster(self, context: dict) -> str:
        active_chars = context.get("active_chars", [])
        if "陆陈安然" not in active_chars: active_chars.append("陆陈安然")
        profiles = []
        for char in active_chars:
            if char in self.char_file_map:
                md_content = self._read_md(f"characters/{self.char_file_map[char]}")
                if md_content: profiles.append(md_content)
        if profiles: return "👥【在场角色核心级设定与语料库】（请严格遵循以下设定描写细节与语气）：\n" + "\n---\n".join(profiles)
        return ""

    def get_main_system_prompt(self, context: dict) -> str:
        base_prompt = self._read_md("main_system.md")
        active_skills = []
        for skill_name, skill_func in self.skills.items():
            skill_text = skill_func(context)
            if skill_text: active_skills.append(skill_text)
                
        rag_lore = context.get("rag_lore", "")
        if rag_lore: active_skills.append(f"🧠【RAG 潜意识记忆与专属语料检索命中】（如果以下语料符合当前情境，请优先引用）：\n{rag_lore}")

        skills_str = "\n\n[已加载的系统动态插件 (Skills)]\n" + "\n".join(active_skills) if active_skills else ""
        if "[ACTIVE_SKILLS]" in base_prompt: return base_prompt.replace("[ACTIVE_SKILLS]", skills_str)
        return base_prompt + skills_str

    def get_main_author_note(self) -> str:
        return self._read_md("main_author_note.md")

    def _init_default_prompt_files(self):
        files_to_create = {
            "main_system.md": """你是一个多角色大学生存游戏的 AI 跑团 DM。
[核心职责]
1. 维持角色人设，严格遵守下方的【在场角色核心级设定】。禁止扮演未提及的角色。
2. 🌟【意图轮盘系统】：玩家将只提供她的【行动意图】。你需要根据该意图，先代入玩家角色（陆陈安然）生成符合她设定的具体台词，再生成NPC反应。如果玩家意图是在微信回复，生成的内容必须体现在 wechat_notifications 中。
3. 动态评估好感度变动。
[ACTIVE_SKILLS]""",
            
            # 🌟 这里的铁律 3 和 4 是核心更新！
            "main_author_note.md": """[⚠️ 系统最高指令 / 格式铁律]
你必须严格输出合法的 JSON 格式。
⚠️ 铁律1：字符串内部【绝对不准】使用双引号（"）！如需引述请使用单引号（'）。
⚠️ 铁律2：next_options 必须严格提供 5 个简短的【态度/意图】选项。如果当前有微信交互，务必提供类似【在群里强硬回复】或【无视群消息】的选项！
⚠️ 铁律3：如果发生冲突，极其鼓励你在 wechat_notifications 发送消息！聊天群名必须从【现有微信通讯录】中复制！
⚠️ 铁律4：如果玩家的行动意图是“在微信里回复”，请你务必代入玩家生成具体的回复内容，并将其放在 wechat_notifications 中，此时 sender 必须填 “陆陈安然”！

输出模板：
{
    "narrator_transition": "（旁白描写现实中的动态或玩家掏出手机的动作）",
    "dialogue_sequence": [
        {"speaker": "陆陈安然", "content": "（如果玩家在现实中说话，写在这里，否则留空）", "mood": "平静"},
        {"speaker": "室友", "content": "（现实中的反应）", "mood": "情绪"}
    ],
    "npc_background_actions": [{"character": "陈雨婷", "action": "冷笑", "affinity_change": -1}],
    "wechat_notifications": [
        {"chat_name": "【背着 李一诺 的小群】", "sender": "陆陈安然", "message": "算了，随便她吧。"},
        {"chat_name": "【背着 李一诺 的小群】", "sender": "唐梦琪", "message": "安然你脾气太好了！"}
    ],
    "next_options": ["【现实中和稀泥】", "【在群里继续吐槽】", "【私聊提醒李一诺】", "【沉默不语】", "【转移话题】"],
    "stat_changes": {"san_delta": -5, "money_delta": 0, "is_argument": true, "affinity_changes": {"唐梦琪": 2}},
    "is_end": false
}""",
            "skills/slang_chapter_1.md": "💬【年度流行词插件(大一)】：当前是2018年，请自然使用：[xswl, 绝绝子, 锦鲤, skr, 安排上了]。",
            "world/base_setting.md": "🏫【全局世界观】：位于江城传媒大学。物价高，宿管阿姨极其严格。编导专业，需要熬夜剪视频。",
            "world/academic_npcs.md": "👨‍🏫【在场 NPC 图鉴】：\n- 李建国老师: 极其古板。迟到扣光平时分。\n- 王莫非老师: 青年讲师，文艺青年。",
            "characters/player_anran.md": "🎭 **陆陈安然 (玩家主角)**\n- **核心人设**：温吞、淡漠、选择困难症、观察型内倾。\n- **家庭背景**：父母离异，习惯了看人眼色，因此在寝室里经常扮演“和稀泥”或“明哲保身”的角色。",
            "characters/tang_mengqi.md": "🎭 **唐梦琪 (精致名媛)**\n- **核心人设**：重度颜控、小红书重度用户、讨好型人格但有些虚荣。",
            "characters/chen_yuting.md": "🎭 **陈雨婷 (学生会干部/利己主义)**\n- **核心人设**：精明干练、掌控欲极强、极度双标。",
            "characters/li_yinuo.md": "🎭 **李一诺 (极致内卷/小镇做题家)**\n- **核心人设**：极度自律、低情商、刻板、只认死理。",
            "characters/su_qian.md": "🎭 **苏浅 (社恐/内向敏感)**\n- **核心人设**：内向敏感、脆弱易碎、讨好型、极度害怕冲突。",
            "characters/zhao_xin.md": "🎭 **赵鑫 (网瘾暴躁/摆烂王者)**\n- **核心人设**：重度网瘾、生活邋遢、嘴臭、随性。",
            "characters/lin_sa.md": "🎭 **林飒 (本地富二代/直球克星)**\n- **核心人设**：本地人、直性子、护短、大门不出二门不迈。"
        }

        for rel_path, content in files_to_create.items():
            full_path = os.path.join(self.prompts_dir, rel_path)
            if not os.path.exists(full_path):
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
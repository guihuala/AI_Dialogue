import os

class PromptManager:
    def __init__(self):
        # 定位到 data/prompts 目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.prompts_dir = os.path.join(base_dir, "data", "prompts")
        self.skills_dir = os.path.join(self.prompts_dir, "skills")
        self.world_dir = os.path.join(self.prompts_dir, "world")
        self.chars_dir = os.path.join(self.prompts_dir, "characters") # 🌟 新增：专门存放角色设定的文件夹
        
        # 确保目录存在
        os.makedirs(self.skills_dir, exist_ok=True)
        os.makedirs(self.world_dir, exist_ok=True)
        os.makedirs(self.chars_dir, exist_ok=True)
        
        # 自动生成默认的 Markdown 文件
        self._init_default_prompt_files()
        
        # 🌟 注册系统技能库 (Skills Library)
        self.skills = {
            "wechat_monitor": self._skill_wechat_monitor,
            "slang_dict": self._skill_slang_dict,
            "academic_world": self._skill_academic_world,
            "character_roster": self._skill_character_roster, # 🌟 注册新技能：动态在场角色图鉴
        }

        # 角色名字到文件名的映射
        self.char_file_map = {
            "陆陈安然": "player_anran.md",
            "唐梦琪": "tang_mengqi.md",
            "陈雨婷": "chen_yuting.md",
            "李一诺": "li_yinuo.md",
            "苏浅": "su_qian.md",
            "赵鑫": "zhao_xin.md",
            "林飒": "lin_sa.md"
        }

    # ==========================================
    # 🗂️ 文件读取引擎
    # ==========================================
    def _read_md(self, relative_path: str) -> str:
        file_path = os.path.join(self.prompts_dir, relative_path)
        if not os.path.exists(file_path):
            return ""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    # ==========================================
    # 🧩 技能模块 (Skills)
    # ==========================================
    def _skill_wechat_monitor(self, context: dict) -> str:
        return self._read_md("skills/wechat_monitor.md")

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
        """🌟 核心新技能：动态读取在场角色的详细 Markdown 设定"""
        active_chars = context.get("active_chars", [])
        
        # 确保主角始终被加载
        if "陆陈安然" not in active_chars:
            active_chars.append("陆陈安然")
            
        profiles = []
        for char in active_chars:
            if char in self.char_file_map:
                md_content = self._read_md(f"characters/{self.char_file_map[char]}")
                if md_content:
                    profiles.append(md_content)
                    
        if profiles:
            return "👥【在场角色核心级设定与语料库】（请严格遵循以下设定描写细节与语气）：\n" + "\n---\n".join(profiles)
        return ""

    # ==========================================
    # 🍔 动态组装流水线 (Prompt Assembly)
    # ==========================================
    def get_main_system_prompt(self, context: dict) -> str:
        base_prompt = self._read_md("main_system.md")
        active_skills = []
        for skill_name, skill_func in self.skills.items():
            skill_text = skill_func(context)
            if skill_text:
                active_skills.append(skill_text)
                
        # 🌟 提取 RAG 向量数据库里的记忆/语料
        rag_lore = context.get("rag_lore", "")
        if rag_lore:
            active_skills.append(f"🧠【RAG 潜意识记忆与专属语料检索命中】（如果以下语料符合当前情境，请优先引用）：\n{rag_lore}")

        # 拼接所有激活的技能和 RAG 数据
        skills_str = "\n\n[已加载的系统动态插件 (Skills)]\n" + "\n".join(active_skills) if active_skills else ""
        
        if "[ACTIVE_SKILLS]" in base_prompt:
            return base_prompt.replace("[ACTIVE_SKILLS]", skills_str)
        else:
            return base_prompt + skills_str

    def get_main_author_note(self) -> str:
        return self._read_md("main_author_note.md")

    def get_wechat_prompt(self, channel_name: str, members: list, context: dict) -> str:
        base_wechat = self._read_md("wechat_system.md")
        members_str = ", ".join(members)
        base_wechat = base_wechat.replace("[CHANNEL_NAME]", channel_name)
        base_wechat = base_wechat.replace("[MEMBERS]", members_str)
        
        # 微信也加载在场角色的设定
        roster_skill = self._skill_character_roster(context)
        slang_skill = self._skill_slang_dict(context)
        
        skills_str = "\n\n"
        if roster_skill: skills_str += roster_skill + "\n"
        if slang_skill: skills_str += slang_skill
        
        if "[ACTIVE_SKILLS]" in base_wechat:
            return base_wechat.replace("[ACTIVE_SKILLS]", skills_str)
        else:
            return base_wechat + skills_str

    # ==========================================
    # 🛠️ 首次运行自动生成默认文件
    # ==========================================
    def _init_default_prompt_files(self):
        files_to_create = {
            "main_system.md": """你是一个多角色大学生存游戏的 AI 跑团 DM。
[核心职责]
1. 维持角色人设，严格遵守下方的【在场角色核心级设定】。禁止扮演未提及的角色。
2. 🌟【意图轮盘系统】：玩家将只提供她的【行动意图】。你需要根据该意图，先代入玩家角色（陆陈安然）生成符合她设定的具体台词，再生成NPC反应。
3. 动态评估好感度变动。
[ACTIVE_SKILLS]""",
            
            # 将旧的铁律1替换为这句更清晰的指令：
            "main_author_note.md": """[⚠️ 系统最高指令 / 格式铁律]
你必须严格输出合法的 JSON 格式。
⚠️ 铁律1：JSON 的 Value 字符串内部【绝对禁止】使用英文双引号（"）和换行符！如果角色需要引用说话，请直接使用【中文双引号（“”）】或单引号！
⚠️ 铁律2：next_options 必须严格提供 5 个简短的【态度/意图】选项。如果当前有微信交互，务必提供类似【在群里强硬回复】或【无视群消息】的选项！
⚠️ 铁律3：如果发生冲突，极其鼓励你在 wechat_notifications 发送消息！聊天群名必须从【现有微信通讯录】中复制！
⚠️ 铁律4：如果玩家的行动意图是“在微信里回复”，请你务必代入玩家生成具体的回复内容，并将其放在 wechat_notifications 中，此时 sender 必须填 “陆陈安然”！
输出模板：
{
    "narrator_transition": "旁白文本",
    "dialogue_sequence": [
        {"speaker": "陆陈安然", "content": "（根据意图生成的具体台词）", "mood": "平静"},
        {"speaker": "室友", "content": "内容", "mood": "情绪"}
    ],
    "npc_background_actions": [{"character": "陈雨婷", "action": "冷笑", "affinity_change": -1}],
    "wechat_notifications": [{"chat_name": "【背着 李一诺 的小群】", "sender": "唐梦琪", "message": "无语！"}],
    "next_options": ["【强硬反对】", "【和稀泥】", "【转移话题】", "【沉默不语】", "【阴阳怪气】"],
    "stat_changes": {"san_delta": -5, "money_delta": 0, "is_argument": true, "affinity_changes": {"陈雨婷": -2}},
    "is_end": false
}""",

            "wechat_system.md": """你正在模拟大学女生寝室的微信聊天。
[群成员与逻辑防线警告]
当前聊天窗口：【[CHANNEL_NAME]】
本群/私聊成员包含：**玩家(陆陈安然)** 以及 **[MEMBERS]**。
⚠️ 铁律1：室友知道安然能看到消息！绝不允许出现当面把安然当做不在场的第三人进行蛐蛐的降智行为！
⚠️ 铁律2：绝对禁止生成名单之外的角色发言！
[核心指令]
1. 玩家刚发了消息，请扮演上述 NPC 进行回复。
2. 语言必须是极度真实的大学生微信风格。
[ACTIVE_SKILLS]
输出模板：
{
    "chat_history": [{"sender": "对方名字", "message": "回复内容"}],
    "affinity_changes": {"唐梦琪": 2}
}""",
            "skills/wechat_monitor.md": "🕵️‍♀️【表里不一判定】：我会提供【近期微信动态】。若玩家微信发言和现实意图严重冲突，请让内情NPC立刻拆穿！",
            "skills/slang_chapter_1.md": "💬【年度流行词插件(大一)】：当前是2018年，请自然使用：[xswl, 绝绝子, 锦鲤, skr, 安排上了]。",
            "world/base_setting.md": "🏫【全局世界观】：位于江城传媒大学。物价高，宿管阿姨极其严格。编导专业，需要熬夜剪视频。",
            "world/academic_npcs.md": "👨‍🏫【在场 NPC 图鉴】：\n- 李建国老师: 极其古板。迟到扣光平时分。\n- 王莫非老师: 青年讲师，文艺青年。",
            
            # 🌟 新增：角色的极致丰富档案 (分好类的语料库)
            "characters/player_anran.md": """🎭 **陆陈安然 (玩家主角)**
- **核心人设**：温吞、淡漠、选择困难症、观察型内倾。不喜欢强出头。
- **外貌与习惯**：常年戴着一副索尼降噪耳机，遇到不想听的争吵就会默默把耳机音量调大。喜欢穿宽松的深色卫衣。
- **家庭背景**：父母离异，习惯了看人眼色，因此在寝室里经常扮演“和稀泥”或“明哲保身”的角色。
- **专属分类语料库**：
  - `[明哲保身]`：“我都行，你们决定就好。” / “（默默把耳机戴上，假装没听见）”
  - `[被逼急了]`：“既然你们都不想退一步，那干脆抽签吧，公平。”""",
  
            "characters/tang_mengqi.md": """🎭 **唐梦琪 (精致名媛)**
- **核心人设**：重度颜控、小红书重度用户、讨好型人格但有些虚荣。
- **外貌与习惯**：桌子上摆满了昂贵的护肤品（部分是分期买的）。生气时喜欢翻白眼、双手抱胸。
- **冲突风格**：喜欢拉帮结派，擅长在背后拉小群吐槽，很少当面硬刚。
- **专属分类语料库**：
  - `[开心/日常]`：“姐妹们！看我刚拔草的这家网红店，出片率绝绝子！”
  - `[阴阳怪气]`：“哎哟，有些人啊，就是不知道自己几斤几两，还真当自己是学霸了呢。”
  - `[委屈/破防]`：“（眼圈瞬间红了）我也就是好心提个建议，你至于这么凶我吗？”"""
        }

        for rel_path, content in files_to_create.items():
            full_path = os.path.join(self.prompts_dir, rel_path)
            if not os.path.exists(full_path):
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
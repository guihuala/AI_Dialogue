import os

class PromptManager:
    def __init__(self):
        # 定位到 data/prompts 目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.prompts_dir = os.path.join(base_dir, "data", "prompts")
        self.skills_dir = os.path.join(self.prompts_dir, "skills")
        
        # 确保目录存在
        os.makedirs(self.skills_dir, exist_ok=True)
        
        # 自动生成默认的 Markdown 文件（仅在文件不存在时创建，方便你后续独立编辑）
        self._init_default_prompt_files()
        
        # 注册系统技能库 (Skills Library)
        self.skills = {
            "wechat_monitor": self._skill_wechat_monitor,
            "slang_dict": self._skill_slang_dict,
        }

    # ==========================================
    # 🗂️ 文件读取引擎
    # ==========================================
    def _read_md(self, relative_path: str) -> str:
        """从 data/prompts 目录读取 Markdown 文件，支持热更新"""
        file_path = os.path.join(self.prompts_dir, relative_path)
        if not os.path.exists(file_path):
            return ""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    # ==========================================
    # 🧩 技能模块 (Skills) - 通过读取独立的 MD 文件实现
    # ==========================================
    def _skill_wechat_monitor(self, context: dict) -> str:
        """抓绿茶技能：监控微信发言与现实意图的冲突"""
        return self._read_md("skills/wechat_monitor.md")

    def _skill_slang_dict(self, context: dict) -> str:
        """流行词知识库技能：根据学年动态加载对应的 MD 词库文件"""
        chapter = context.get("chapter", 1)
        # 动态寻找对应学年的流行词库，例如 skills/slang_chapter_1.md
        return self._read_md(f"skills/slang_chapter_{chapter}.md")

    # ==========================================
    # 🍔 动态组装流水线 (Prompt Assembly)
    # ==========================================
    def get_main_system_prompt(self, context: dict) -> str:
        """读取主线 Prompt 模板，并动态拼接 Skills"""
        base_prompt = self._read_md("main_system.md")
        
        # 动态按需加载 Skills
        active_skills = []
        for skill_name, skill_func in self.skills.items():
            skill_text = skill_func(context)
            if skill_text:
                active_skills.append(skill_text)
                
        # 占位符替换：将激活的技能拼接到 [ACTIVE_SKILLS] 位置
        skills_str = "\n\n[已加载的系统动态插件 (Skills)]\n" + "\n".join(active_skills) if active_skills else ""
        
        # 如果模板里有占位符则替换，没有则直接追加在末尾
        if "[ACTIVE_SKILLS]" in base_prompt:
            return base_prompt.replace("[ACTIVE_SKILLS]", skills_str)
        else:
            return base_prompt + skills_str

    def get_main_author_note(self) -> str:
        """读取底层格式铁律"""
        return self._read_md("main_author_note.md")

    def get_wechat_prompt(self, channel_name: str, members: list, context: dict) -> str:
        """读取微信专用 Prompt 模板，并进行占位符替换"""
        base_wechat = self._read_md("wechat_system.md")
        
        # 替换上下文变量
        members_str = ", ".join(members)
        base_wechat = base_wechat.replace("[CHANNEL_NAME]", channel_name)
        base_wechat = base_wechat.replace("[MEMBERS]", members_str)
        
        # 在微信里也加载流行词技能
        slang_skill = self._skill_slang_dict(context)
        skills_str = "\n\n" + slang_skill if slang_skill else ""
        
        if "[ACTIVE_SKILLS]" in base_wechat:
            return base_wechat.replace("[ACTIVE_SKILLS]", skills_str)
        else:
            return base_wechat + skills_str

    # ==========================================
    # 🛠️ 首次运行自动生成默认文件 (仅起引导作用)
    # ==========================================
    def _init_default_prompt_files(self):
        """如果 MD 文件不存在，则自动创建并写入初始内容"""
        
        files_to_create = {
            "main_system.md": """你是一个多角色大学生存游戏的 AI 跑团 DM。
[核心职责]
1. 维持角色人设，严格遵守【在场角色图鉴】。禁止扮演未提及的角色。
2. 🌟【意图轮盘系统】：玩家将只提供她的【行动意图】。你需要根据该意图，先代入玩家角色（陆陈安然）生成符合她“淡漠/观察型”人设的具体台词，再生成NPC反应。
3. 动态评估好感度变动（affinity_changes）。
4. 【暗场行动】：评估没说话的角色背地里的行为，记录在 npc_background_actions。
[ACTIVE_SKILLS]
""",
            
            "main_author_note.md": """[⚠️ 系统最高指令 / 格式铁律]
你必须严格输出合法的 JSON 格式。
⚠️ 铁律1：字符串内部【绝对不准】使用双引号（"）！如需引述请使用单引号（'）。
⚠️ 铁律2：next_options 必须严格提供 5 个简短的【态度/意图】选项。
⚠️ 铁律3：如果发生冲突或有八卦，极其鼓励你在 wechat_notifications 发送消息！但聊天群名【绝对只能】从我提供的【现有微信通讯录】中原封不动地复制，严禁你自创群名！

输出模板：
{
    "narrator_transition": "旁白文本",
    "dialogue_sequence": [
        {"speaker": "陆陈安然", "content": "（根据意图生成的具体台词）", "mood": "平静"},
        {"speaker": "室友", "content": "内容", "mood": "情绪"}
    ],
    "npc_background_actions": [{"character": "陈雨婷", "action": "冷笑", "affinity_change": -1}],
    "wechat_notifications": [{"chat_name": "【背着 李一诺 的小群】", "sender": "唐梦琪", "message": "真是无语了！"}],
    "next_options": ["【强硬反对】", "【和稀泥】", "【转移话题】", "【沉默不语】", "【阴阳怪气】"],
    "stat_changes": {"san_delta": -5, "money_delta": 0, "is_argument": true, "affinity_changes": {"陈雨婷": -2}},
    "is_end": false
}""",

            "wechat_system.md": """你正在模拟大学女生寝室的微信聊天。
[系统级物理隔离警告]
当前玩家正在【[CHANNEL_NAME]】中发言。该聊天窗口内 **仅存在** 以下角色：[MEMBERS]。
⚠️ 绝对禁止生成名单之外的任何角色发言！私聊窗口绝对不能出现第三个人！

[核心指令]
1. 玩家刚发了消息，请扮演上述成员进行回复。结合【当前现实进展】。
2. 语言必须是极度真实的【大学生微信风格】：爱用缩写、乱用标点、表情包代词。
3. 必须严格输出合法 JSON，严禁自创键名！字符串内部严禁使用双引号！
[ACTIVE_SKILLS]

输出模板：
{
    "chat_history": [{"sender": "对方名字", "message": "回复内容"}],
    "affinity_changes": {"唐梦琪": 2}
}""",
            
            "skills/wechat_monitor.md": "🕵️‍♀️【表里不一判定】：我会提供【近期微信动态】。若玩家在微信里的发言和现实意图严重冲突（当面一套背后一套），请让知道内情的 NPC 立刻在对话中阴阳怪气或直接拆穿她！",
            
            "skills/slang_chapter_1.md": "💬【年度流行词插件(大一)】：当前是2018年，请在角色（特别是冲浪达人人设）的对话中极其自然地使用以下词汇：[xswl, 绝绝子, 锦鲤, skr, 安排上了]。",
            
            "skills/slang_chapter_2.md": "💬【年度流行词插件(大二)】：当前是2019年，本学年流行词：[雨女无瓜, 柠檬精, 硬核, 996, 盘他]。",
        }

        for rel_path, content in files_to_create.items():
            full_path = os.path.join(self.prompts_dir, rel_path)
            if not os.path.exists(full_path):
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
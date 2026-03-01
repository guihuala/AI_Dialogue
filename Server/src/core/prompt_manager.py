import os
import csv

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
        
        # 🌟 注册系统动态技能库
        self.skills = {
            "slang_dict": self._skill_slang_dict,
            "academic_world": self._skill_academic_world,
            "character_roster": self._skill_character_roster, 
            "relationship_matrix": self._skill_relationship_matrix 
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

    def _skill_relationship_matrix(self, context: dict) -> str:
        active_chars = context.get("active_chars", [])
        if "陆陈安然" not in active_chars: active_chars.append("陆陈安然")
        
        rel_csv_path = os.path.join(self.chars_dir, "relationship.csv")
        if not os.path.exists(rel_csv_path): return ""
        
        relations = []
        try:
            with open(rel_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    source = row.get("评价者", "").strip()
                    target = row.get("被评价者", "").strip()
                    
                    # 🌟 核心修复：必须“评价者”和“被评价者”同时在场，才触发关系！
                    # 否则会引发不在场角色的名字污染大模型，导致幽灵室友出现
                    if source in active_chars and target in active_chars:
                        surface = row.get("表面态度", "").strip()
                        inner = row.get("内心真实评价", "").strip()
                        relations.append(f"- 【{source}】对待【{target}】：表面上展现出[{surface}]，内心实际上觉得[{inner}]。")
        except Exception as e:
            print(f"关系矩阵读取失败: {e}")
        
        if relations:
            return "🕸️【人物社交网络与底层偏见】（请根据以下关系，精准把控在场角色的语言温度、暗场动作及阴阳怪气程度）：\n" + "\n".join(relations)
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
        # 🌟 注意：这里修改了 main_author_note.md 的 wechat_notifications 示范
        files_to_create = {
            "main_system.md": "你是一个多角色大学生存游戏的 AI 跑团 DM。\n[核心职责]\n1. 维持角色人设，严格遵守下方的【在场角色核心级设定】。禁止扮演未提及的角色。\n2. 🌟【意图轮盘系统】：玩家将只提供她的【行动意图】。你需要根据该意图，先代入玩家角色（陆陈安然）生成符合她设定的具体台词，再生成NPC反应。如果玩家意图是在微信回复，生成的内容必须体现在 wechat_notifications 中。\n3. 动态评估好感度变动。\n[ACTIVE_SKILLS]",
            "main_author_note.md": "[⚠️ 系统最高指令 / 格式铁律]\n你必须严格输出合法的 JSON 格式。\n⚠️ 铁律1：JSON 的 Value 字符串内部【绝对禁止】使用英文双引号（\"）和换行符！如果角色需要引用说话，请直接使用【中文双引号（“”）】或单引号！\n⚠️ 铁律2：next_options 必须严格提供 5 个简短的【态度/意图】选项。如果当前有微信交互，务必提供类似【在群里强硬回复】或【无视群消息】的选项！\n⚠️ 铁律3：如果发生冲突，极其鼓励你在 wechat_notifications 发送消息！聊天群名必须从【现有微信通讯录】中复制！\n⚠️ 铁律4：如果玩家的行动意图是“在微信里回复”，请你务必代入玩家生成具体的回复内容，并将其放在 wechat_notifications 中，此时 sender 必须填 “陆陈安然”！\n\n输出模板：\n{\n    \"narrator_transition\": \"（旁白描写现实中的动态或玩家掏出手机的动作）\",\n    \"dialogue_sequence\": [\n        {\"speaker\": \"陆陈安然\", \"content\": \"（如果玩家在现实中说话，写在这里，否则留空）\", \"mood\": \"平静\"},\n        {\"speaker\": \"室友\", \"content\": \"（现实中的反应）\", \"mood\": \"情绪\"}\n    ],\n    \"npc_background_actions\": [{\"character\": \"陈雨婷\", \"action\": \"冷笑\", \"affinity_change\": -1}],\n    \"wechat_notifications\": [\n        {\"chat_name\": \"【404 仙女下凡大群】\", \"sender\": \"陆陈安然\", \"message\": \"收到。\"},\n        {\"chat_name\": \"唐梦琪 (私聊)\", \"sender\": \"唐梦琪\", \"message\": \"安然，你看辅导员发的通知了吗？\"}\n    ],\n    \"next_options\": [\"【现实中和稀泥】\", \"【在群里继续吐槽】\", \"【私聊回复唐梦琪】\", \"【沉默不语】\", \"【转移话题】\"],\n    \"stat_changes\": {\"san_delta\": -5, \"money_delta\": 0, \"is_argument\": true, \"affinity_changes\": {\"唐梦琪\": 2}},\n    \"is_end\": false\n}",
            "skills/slang_chapter_1.md": "💬【年度流行词插件(大一)】：当前是2018年，请自然使用：[xswl, 绝绝子, 锦鲤, skr, 安排上了]。",
            "world/base_setting.md": "🏫【全局世界观】：位于江城传媒大学。物价高，宿管阿姨极其严格。编导专业，需要熬夜剪视频。",
            "world/academic_npcs.md": "👨‍🏫【在场 NPC 图鉴】：\n- 李建国老师: 极其古板。迟到扣光平时分。\n- 王莫非老师: 青年讲师，文艺青年。"
        }

        for rel_path, content in files_to_create.items():
            full_path = os.path.join(self.prompts_dir, rel_path)
            if not os.path.exists(full_path):
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
        rel_csv_path = os.path.join(self.chars_dir, "relationship.csv")
        if not os.path.exists(rel_csv_path):
            os.makedirs(os.path.dirname(rel_csv_path), exist_ok=True)
            with open(rel_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["评价者", "被评价者", "表面态度", "内心真实评价"])
                writer.writerow(["唐梦琪", "陆陈安然", "热情分享", "觉得安然是个好听众，适合当倾诉垃圾桶"])
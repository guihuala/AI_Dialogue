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
        
        # 注册系统动态技能库
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
        if not relative_path: return ""
        file_path = os.path.join(self.prompts_dir, relative_path)
        if not os.path.exists(file_path) or os.path.isdir(file_path): return ""
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
        base_prompt = self._read_md("main_system.md")
        active_skills = []
        for skill_name, skill_func in self.skills.items():
            skill_text = skill_func(context)
            if skill_text: active_skills.append(skill_text)
                
        rag_lore = context.get("rag_lore", "")
        if rag_lore: active_skills.append(f"【专属语料检索命中】（如果以下语料符合当前情境，请优先引用）：\n{rag_lore}")

        skills_str = "\n\n[已加载的系统动态插件 (Skills)]\n" + "\n".join(active_skills) if active_skills else ""
        if "[ACTIVE_SKILLS]" in base_prompt: return base_prompt.replace("[ACTIVE_SKILLS]", skills_str)
        return base_prompt + skills_str

    def get_main_author_note(self) -> str:
        return self._read_md("main_author_note.md")

    def get_all_relationships(self) -> str:
        """提取全局角色认知网络与底层偏见"""
        rel_csv_path = os.path.join(self.chars_dir, "relationship.csv")
        if not os.path.exists(rel_csv_path): 
            return "认知拓扑文件(relationship.csv)缺失"
        
        lines = []
        try:
            import csv
            with open(rel_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    source = row.get("评价者", "").strip()
                    target = row.get("被评价者", "").strip()
                    surface = row.get("表面态度", "").strip()
                    inner = row.get("内心真实评价", "").strip()
                    lines.append(f"[{source} ➡️  {target}] 表面: {surface} | 内心: {inner}")
        except Exception as e:
            return f"认知拓扑解码失败: {e}"
            
        return "\n".join(lines) if lines else "认知拓扑未挂载任何节点"
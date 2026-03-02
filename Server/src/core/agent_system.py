import json
import re

class NPCAgent:
    def __init__(self, name: str, profile_text: str, relationship_text: str, llm_service):
        self.name = name
        self.profile = profile_text
        self.relationship = relationship_text
        self.llm = llm_service

    def react(self, event_context: str, player_action: str) -> dict:
        """每个 NPC 独立思考并做出反应"""
        
        sys_prompt = f"""你是{self.name}。
【你的设定】:
{self.profile}

【你对别人的看法】:
{self.relationship}

[演出任务]
现在发生了一个事件，请你根据自己的性格，给出最真实的反应。
你必须输出合法的 JSON 格式。

输出模板：
{{
    "dialogue": "（你的台词。如果没有说话留空）",
    "mood": "（你当前的情绪，例如：愤怒/鄙夷/平静）",
    "action": "（你的暗场动作，例如：翻白眼/叹气/摔门/在一旁冷笑 等）",
    "wechat_message": "（如果在这种情况下你想在微信里说话，写下内容，否则留空）"
}}"""

        user_prompt = f"【当前发生的事件】:\n{event_context}\n\n【玩家的行动】:\n{player_action}\n\n请给出你的独立反应："

        # 调用大模型，让这个 NPC 独立思考（自动继承了 json_object 模式）
        res_text = self.llm.generate_response(
            system_prompt=sys_prompt, 
            user_input=user_prompt, 
            temperature=0.75, 
            max_tokens=200
        )
        
        try:
            # 暴力洗码并解析，防止单个演员忘词导致崩溃
            res_text = re.sub(r'```json\s*', '', res_text)
            res_text = re.sub(r'```\s*', '', res_text)
            res_text = res_text.replace('“', '"').replace('”', '"')
            return json.loads(res_text)
        except:
            return {"dialogue": "", "mood": "沉默", "action": "（没有明显反应）", "wechat_message": ""}


import os
import csv

class ReflectionSystem:
    def __init__(self, llm_service, prompts_dir):
        self.llm = llm_service
        self.rel_csv_path = os.path.join(prompts_dir, "characters", "relationship.csv")

    def trigger_night_reflection(self, chapter: int, recent_history: str, active_chars: list) -> str:
        """🌙 深夜反思引擎：让所有 NPC 根据今天的遭遇，修改对别人的偏见"""
        if not os.path.exists(self.rel_csv_path):
            return "⚠️ 未找到 relationship.csv，无法进行反思。"

        # 1. 读取当前的社交网络状态
        current_relations = {}
        with open(self.rel_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                evaluator = row.get("评价者", "").strip()
                target = row.get("被评价者", "").strip()
                if evaluator not in current_relations: current_relations[evaluator] = []
                current_relations[evaluator].append({
                    "target": target,
                    "surface": row.get("表面态度", "").strip(),
                    "inner": row.get("内心真实评价", "").strip()
                })

        # 2. 构建反思 Prompt
        sys_prompt = """你是一个“上帝视角的心理分析师”。
现在是深夜，404寝室的女生们正在各自的床上复盘今天发生的事情。
请你根据她们今天经历的剧情，推演她们心理状态的变化，并重新评估她们对其他人的【表面态度】和【内心真实评价】。

[⚠️ 输出要求]
必须返回合法的 JSON 格式。
请以日记的形式输出她们各自今天的心得，并给出更新后的人际偏见。如果没有明显变化，可以保持原样，但如果发生了冲突或背叛，请狠狠地修改她们的评价！

格式范例：
{
    "reflections": [
        {
            "character": "唐梦琪",
            "diary": "今天安然居然帮着李一诺说话，真是看错她了，以后必须防着点。",
            "updated_relations": [
                {"target": "陆陈安然", "surface": "假笑客套", "inner": "是个墙头草，不可深交"},
                {"target": "李一诺", "surface": "阴阳怪气", "inner": "死板的独裁者，恶心"}
            ]
        }
    ]
}"""
        
        user_prompt = f"【近期剧情回顾 (第{chapter}章)】:\n{recent_history}\n\n请进行深夜反思并更新偏见矩阵！"

        # 3. 呼叫大模型进行深度心理演算
        res_text = self.llm.generate_response(sys_prompt, user_prompt, temperature=0.8, max_tokens=1500)
        
        try:
            # 解析洗码
            res_text = re.sub(r'```json\s*', '', res_text)
            res_text = re.sub(r'```\s*', '', res_text)
            res_text = res_text.replace('“', '"').replace('”', '"')
            parsed = json.loads(res_text)
            
            reflections = parsed.get("reflections", [])
            reflection_logs = "🌙 **【深夜反思日志】**\n\n"
            
            # 4. 将新的偏见写回内存，准备覆写 CSV
            for ref in reflections:
                char_name = ref.get("character")
                diary = ref.get("diary", "")
                updates = ref.get("updated_relations", [])
                
                if char_name in current_relations:
                    reflection_logs += f"📖 **{char_name}的日记**：“{diary}”\n"
                    for up in updates:
                        target = up.get("target")
                        for existing in current_relations[char_name]:
                            if existing["target"] == target:
                                existing["surface"] = up.get("surface", existing["surface"])
                                existing["inner"] = up.get("inner", existing["inner"])
                                reflection_logs += f"  > 🔄 对 {target} 的看法已更新！\n"
            
            # 5. 覆写保存 relationship.csv
            with open(self.rel_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["评价者", "被评价者", "表面态度", "内心真实评价"])
                for evaluator, targets in current_relations.items():
                    for t in targets:
                        writer.writerow([evaluator, t["target"], t["surface"], t["inner"]])
                        
            return reflection_logs
            
        except Exception as e:
            return f"⚠️ 反思模块解析失败: {e}\n模型原始返回: {res_text}"
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
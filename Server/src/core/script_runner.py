import json
from typing import Dict, Any, Optional, List

class ScriptRunner:
    """
    负责解析和导航预生成的完整事件剧本。
    """
    def __init__(self, script_data: Dict[str, Any]):
        self.script = script_data
        self.turns = {t.get("turn_num", i+1): t for i, t in enumerate(script_data.get("turns", []))}
        self.event_id = script_data.get("event_id", "unknown")

    def get_turn(self, turn_num: int) -> Optional[Dict[str, Any]]:
        return self.turns.get(turn_num)

    def execute_choice(self, turn_num: int, choice_text: str) -> Optional[Dict[str, Any]]:
        """
        根据当前回合和玩家选择，返回结果。
        """
        turn = self.get_turn(turn_num)
        if not turn:
            return None
        
        choices = turn.get("player_choices", [])
        selected_choice = None
        
        # 模糊匹配选项
        for c in choices:
            if choice_text in c.get("text", "") or c.get("text", "") in choice_text:
                selected_choice = c
                break
        
        if not selected_choice:
            # 如果没匹配到，默认返回第一个
            if choices:
                selected_choice = choices[0]
            else:
                return None
        
        return selected_choice

    def get_next_turn_data(self, turn_num: int, choice_text: str) -> Dict[str, Any]:
        """
        封装为一个符合 GameEngine.play_main_turn 返回格式的字典。
        """
        choice_result = self.execute_choice(turn_num, choice_text)
        if not choice_result:
            return {"error": "Choice not found in script"}

        leads_to = choice_result.get("leads_to_turn")
        next_turn = self.get_turn(leads_to) if leads_to else None
        
        # 构造对话序列：玩家选择后的即时反馈 + 下一回合的出场对话
        dialogue_seq = choice_result.get("immediate_outcome_dialogue", [])
        if next_turn:
            dialogue_seq.extend(next_turn.get("dialogue_sequence", []))

        # 构造选项
        next_options = [opt.get("text") for opt in next_turn.get("player_choices", [])] if next_turn else []
        
        is_end = next_turn.get("is_end", False) if next_turn else True

        return {
            "narrator_transition": f"你选择了：{choice_result.get('text')}",
            "dialogue_sequence": dialogue_seq,
            "next_options": next_options,
            "stat_changes": choice_result.get("stat_changes", {}),
            "is_end": is_end,
            "current_scene": next_turn.get("scene", "场景") if next_turn else "场景",
            "turn": leads_to if leads_to else turn_num + 1
        }

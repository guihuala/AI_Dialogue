from __future__ import annotations

from typing import Dict, List, Any


class NarrativeStateManager:
    """
    将数值和最近决策压缩成更适合剧情消费的叙事状态摘要。
    第一阶段先做轻量规则版，避免再增加一次 LLM 调用。
    """

    def __init__(self):
        self.state = self._default_state()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "player_arc": [],
            "room_tension": "平静但暗流涌动",
            "recent_impressions": [],
            "active_threads": [],
            "mood_flags": {},
            "choice_tendencies": [],
            "last_event_id": "",
            "last_event_name": "",
            "last_choice": "",
        }

    def reset(self):
        self.state = self._default_state()

    def load(self, raw_state: Dict[str, Any] | None):
        base = self._default_state()
        if isinstance(raw_state, dict):
            base.update({k: v for k, v in raw_state.items() if k in base})
        for key in ["player_arc", "recent_impressions", "active_threads", "choice_tendencies"]:
            if not isinstance(base.get(key), list):
                base[key] = []
        if not isinstance(base.get("mood_flags"), dict):
            base["mood_flags"] = {}
        self.state = base

    def export(self) -> Dict[str, Any]:
        return {
            "player_arc": list(self.state.get("player_arc", [])),
            "room_tension": str(self.state.get("room_tension", "")),
            "recent_impressions": list(self.state.get("recent_impressions", [])),
            "active_threads": list(self.state.get("active_threads", [])),
            "mood_flags": dict(self.state.get("mood_flags", {})),
            "choice_tendencies": list(self.state.get("choice_tendencies", [])),
            "last_event_id": str(self.state.get("last_event_id", "")),
            "last_event_name": str(self.state.get("last_event_name", "")),
            "last_choice": str(self.state.get("last_choice", "")),
        }

    def build_prompt_summary(
        self,
        *,
        player_name: str,
        san: float,
        affinity: Dict[str, float] | None,
        active_chars: List[str] | None,
    ) -> str:
        affinity = affinity or {}
        active_chars = active_chars or []
        lines: List[str] = ["【当前剧情状态摘要】"]

        room_tension = str(self.state.get("room_tension", "") or "").strip()
        if room_tension:
            lines.append(f"- 宿舍局势：{room_tension}")

        player_arc = [str(item).strip() for item in self.state.get("player_arc", []) if str(item).strip()]
        if player_arc:
            lines.append(f"- {player_name} 的近期状态：{'；'.join(player_arc[:3])}")
        else:
            lines.append(f"- {player_name} 的近期状态：暂未形成明确人设，需根据当下表现继续塑造。")

        recent_impressions = [str(item).strip() for item in self.state.get("recent_impressions", []) if str(item).strip()]
        if recent_impressions:
            lines.append("- 最近形成的印象：")
            lines.extend([f"  * {item}" for item in recent_impressions[:4]])

        active_threads = [str(item).strip() for item in self.state.get("active_threads", []) if str(item).strip()]
        if active_threads:
            lines.append("- 当前仍在发酵的话题：")
            lines.extend([f"  * {item}" for item in active_threads[:3]])

        tendencies = [str(item).strip() for item in self.state.get("choice_tendencies", []) if str(item).strip()]
        if tendencies:
            lines.append(f"- 玩家近期决策倾向：{'；'.join(tendencies[:3])}")

        san_desc = self._describe_san(player_name, san)
        lines.append(f"- 心理状态：{san_desc}")

        affinity_summary = self._summarize_affinity(player_name, affinity, active_chars)
        if affinity_summary:
            lines.append("- 当前关系温度：")
            lines.extend([f"  * {item}" for item in affinity_summary])

        mood_flags = self.state.get("mood_flags", {})
        if isinstance(mood_flags, dict) and mood_flags:
            lines.append("- 当前气氛标签：")
            for name, mood in list(mood_flags.items())[:4]:
                lines.append(f"  * {name}: {mood}")

        lines.append("- 写作要求：本回合必须让以上关系和局势至少体现一处，不要让这些状态只停留在说明里。")
        return "\n".join(lines)

    def update_after_turn(
        self,
        *,
        player_name: str,
        event_obj,
        action_text: str,
        san: float,
        affinity: Dict[str, float] | None,
        active_chars: List[str] | None,
        effects_data: Dict[str, Any] | None,
        dialogue_sequence: List[Dict[str, Any]] | None,
        is_end: bool,
    ):
        affinity = affinity or {}
        active_chars = active_chars or []
        effects_data = effects_data or {}
        dialogue_sequence = dialogue_sequence or []

        state = self.state
        event_name = str(getattr(event_obj, "name", "") or "").strip()
        event_id = str(getattr(event_obj, "id", "") or "").strip()
        event_desc = str(getattr(event_obj, "description", "") or "").strip()

        state["last_event_id"] = event_id
        state["last_event_name"] = event_name
        state["last_choice"] = action_text or ""

        if event_name:
            thread_text = f"{event_name}：{event_desc[:26]}{'…' if len(event_desc) > 26 else ''}" if event_desc else event_name
            self._push_unique("active_threads", thread_text, max_len=4)
            if is_end:
                state["active_threads"] = [t for t in state["active_threads"] if event_name not in t]

        self._update_player_arc(player_name, action_text, san)
        self._update_choice_tendencies(action_text)
        self._update_room_tension(effects_data, dialogue_sequence)
        self._update_recent_impressions(player_name, affinity, active_chars, action_text, dialogue_sequence)
        self._update_mood_flags(player_name, san, active_chars, affinity)

    def _push_unique(self, key: str, value: str, max_len: int = 4):
        text = str(value or "").strip()
        if not text:
            return
        items = [str(item).strip() for item in self.state.get(key, []) if str(item).strip()]
        items = [item for item in items if item != text]
        items.insert(0, text)
        self.state[key] = items[:max_len]

    def _describe_san(self, player_name: str, san: float) -> str:
        try:
            value = float(san)
        except Exception:
            value = 100.0
        if value <= 25:
            return f"{player_name} 已明显绷紧，容易回避、失神或突然失控。"
        if value <= 50:
            return f"{player_name} 正在强撑，情绪阈值偏低，很容易被一句话刺到。"
        if value <= 75:
            return f"{player_name} 表面还算稳定，但已经开始在心里积压不满。"
        return f"{player_name} 目前还能维持基本镇定，仍有余裕观察和试探。"

    def _summarize_affinity(self, player_name: str, affinity: Dict[str, float], active_chars: List[str]) -> List[str]:
        items: List[str] = []
        for name in active_chars:
            if name == player_name or name not in affinity:
                continue
            val = affinity.get(name, 50)
            try:
                score = float(val)
            except Exception:
                score = 50.0
            if score >= 75:
                items.append(f"{name} 对 {player_name} 明显偏向亲近或护短。")
            elif score >= 60:
                items.append(f"{name} 对 {player_name} 已有一定信任，更容易给面子。")
            elif score <= 25:
                items.append(f"{name} 对 {player_name} 明显反感，随时可能借题发挥。")
            elif score <= 40:
                items.append(f"{name} 对 {player_name} 存在戒备或不耐烦。")
        return items[:4]

    def _update_player_arc(self, player_name: str, action_text: str, san: float):
        action = str(action_text or "").strip()
        if not action:
            return
        if any(keyword in action for keyword in ["沉默", "观察", "等等", "先看看", "不说话"]):
            self._push_unique("player_arc", f"{player_name} 最近更倾向先观察局势，再决定是否介入。", max_len=3)
        if any(keyword in action for keyword in ["缓和", "安慰", "圆场", "劝", "打圆场"]):
            self._push_unique("player_arc", f"{player_name} 最近常扮演和事佬，倾向先维持表面和平。", max_len=3)
        if any(keyword in action for keyword in ["质问", "反驳", "拒绝", "回怼", "硬刚"]):
            self._push_unique("player_arc", f"{player_name} 最近开始更明确地表达立场，不再一味退让。", max_len=3)
        try:
            if float(san) <= 45:
                self._push_unique("player_arc", f"{player_name} 的精神压力正在累积，行为里容易出现退缩和迟疑。", max_len=3)
        except Exception:
            pass

    def _update_choice_tendencies(self, action_text: str):
        action = str(action_text or "").strip()
        if not action:
            return
        mapping = [
            ("缓和", ["缓和", "安慰", "调解", "打圆场", "圆场"]),
            ("观察", ["观察", "沉默", "先看看", "旁观"]),
            ("对抗", ["质问", "反驳", "回怼", "拒绝", "硬刚"]),
            ("转移", ["转移", "换话题", "岔开", "跳过"]),
        ]
        for label, keywords in mapping:
            if any(keyword in action for keyword in keywords):
                self._push_unique("choice_tendencies", f"最近常选择“{label}”路线处理冲突。", max_len=3)
                break

    def _update_room_tension(self, effects_data: Dict[str, Any], dialogue_sequence: List[Dict[str, Any]]):
        arg_delta = 0
        try:
            arg_delta = int(float(effects_data.get("arg_delta", 0) or 0))
        except Exception:
            arg_delta = 0

        text_blob = " ".join(str(item.get("content", "")) for item in dialogue_sequence if isinstance(item, dict))
        if arg_delta > 0 or any(keyword in text_blob for keyword in ["吵", "闭嘴", "烦死", "别管", "有病"]):
            self.state["room_tension"] = "火药味明显，任何一句重话都可能把场面点燃"
        elif any(keyword in text_blob for keyword in ["尴尬", "沉默", "算了", "没事"]):
            self.state["room_tension"] = "表面平静，但尴尬和不满都还挂在空气里"
        elif any(keyword in text_blob for keyword in ["笑", "缓和", "行吧", "好好说"]):
            self.state["room_tension"] = "局势略有缓和，但矛盾并未真正消失"

    def _update_recent_impressions(
        self,
        player_name: str,
        affinity: Dict[str, float],
        active_chars: List[str],
        action_text: str,
        dialogue_sequence: List[Dict[str, Any]],
    ):
        action = str(action_text or "").strip()
        lines = [str(item.get("content", "")) for item in dialogue_sequence if isinstance(item, dict)]
        joined = " ".join(lines)

        if any(keyword in action for keyword in ["缓和", "安慰", "打圆场", "圆场"]):
            self._push_unique("recent_impressions", f"室友开始把 {player_name} 视为容易出来收场的人。")
        if any(keyword in action for keyword in ["沉默", "观察", "不说话"]):
            self._push_unique("recent_impressions", f"有人觉得 {player_name} 又在犹豫，不太愿意正面表态。")
        if any(keyword in action for keyword in ["质问", "拒绝", "反驳", "回怼"]):
            self._push_unique("recent_impressions", f"{player_name} 这次的态度比以往更硬，容易让人重新评估她的边界。")

        for name in active_chars:
            if name == player_name or name not in affinity:
                continue
            try:
                score = float(affinity.get(name, 50))
            except Exception:
                score = 50.0
            if score >= 70:
                self._push_unique("recent_impressions", f"{name} 现在更可能在公开场合给 {player_name} 留面子。")
            elif score <= 30:
                self._push_unique("recent_impressions", f"{name} 对 {player_name} 的不耐烦已经很难藏住。")

        if "对不起" in joined or "算了" in joined:
            self._push_unique("recent_impressions", "这场互动留下了没说开的别扭感，后续很容易翻旧账。")

    def _update_mood_flags(self, player_name: str, san: float, active_chars: List[str], affinity: Dict[str, float]):
        mood_flags: Dict[str, str] = {}
        try:
            san_value = float(san)
        except Exception:
            san_value = 100.0

        if san_value <= 35:
            mood_flags[player_name] = "强撑着不崩"
        elif san_value <= 60:
            mood_flags[player_name] = "敏感而犹豫"
        else:
            mood_flags[player_name] = "尚能冷静观察"

        for name in active_chars[:4]:
            if name == player_name:
                continue
            try:
                score = float(affinity.get(name, 50))
            except Exception:
                score = 50.0
            if score >= 70:
                mood_flags[name] = "对主角更愿意帮腔"
            elif score <= 30:
                mood_flags[name] = "对主角明显带刺"
            else:
                mood_flags[name] = "态度仍在摇摆"

        self.state["mood_flags"] = mood_flags

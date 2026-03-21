from __future__ import annotations

from typing import Dict, List, Any


class NarrativeStateManager:
    """
    将数值和最近决策压缩成更适合剧情消费的叙事状态摘要。
    第一阶段先做轻量规则版，避免再增加一次 LLM 调用。
    """

    def __init__(self):
        self.state = self._default_state()
        self._new_milestones: List[str] = []

    def _default_state(self) -> Dict[str, Any]:
        return {
            "player_arc": [],
            "room_tension": "平静但暗流涌动",
            "recent_impressions": [],
            "active_threads": [],
            "mood_flags": {},
            "choice_tendencies": [],
            "relationship_state": {},
            "long_term_milestones": [],
            "last_event_id": "",
            "last_event_name": "",
            "last_choice": "",
        }

    def reset(self):
        self.state = self._default_state()
        self._new_milestones = []

    def load(self, raw_state: Dict[str, Any] | None):
        base = self._default_state()
        if isinstance(raw_state, dict):
            base.update({k: v for k, v in raw_state.items() if k in base})
        for key in ["player_arc", "recent_impressions", "active_threads", "choice_tendencies", "long_term_milestones"]:
            if not isinstance(base.get(key), list):
                base[key] = []
        if not isinstance(base.get("mood_flags"), dict):
            base["mood_flags"] = {}
        if not isinstance(base.get("relationship_state"), dict):
            base["relationship_state"] = {}
        self.state = base
        self._new_milestones = []

    def export(self) -> Dict[str, Any]:
        return {
            "player_arc": list(self.state.get("player_arc", [])),
            "room_tension": str(self.state.get("room_tension", "")),
            "recent_impressions": list(self.state.get("recent_impressions", [])),
            "active_threads": list(self.state.get("active_threads", [])),
            "mood_flags": dict(self.state.get("mood_flags", {})),
            "choice_tendencies": list(self.state.get("choice_tendencies", [])),
            "relationship_state": dict(self.state.get("relationship_state", {})),
            "long_term_milestones": list(self.state.get("long_term_milestones", [])),
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

        relation_lines = self._summarize_relationship_state(player_name, active_chars)
        if relation_lines:
            lines.append("- 关系阶段与风险：")
            lines.extend([f"  * {item}" for item in relation_lines])

        mood_flags = self.state.get("mood_flags", {})
        if isinstance(mood_flags, dict) and mood_flags:
            lines.append("- 当前气氛标签：")
            for name, mood in list(mood_flags.items())[:4]:
                lines.append(f"  * {name}: {mood}")

        milestones = [str(item).strip() for item in self.state.get("long_term_milestones", []) if str(item).strip()]
        if milestones:
            lines.append("- 历史里程碑（仅与当前局相关）：")
            lines.extend([f"  * {item}" for item in milestones[:3]])

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
        self._update_relationship_state(
            player_name=player_name,
            event_obj=event_obj,
            event_id=event_id,
            event_name=event_name,
            active_chars=active_chars,
            affinity=affinity,
            action_text=action_text,
            effects_data=effects_data,
            dialogue_sequence=dialogue_sequence,
            is_end=is_end,
        )

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

    def _get_or_create_relation(self, char_name: str, affinity_score: float) -> Dict[str, Any]:
        rel_map = self.state.get("relationship_state", {})
        if not isinstance(rel_map, dict):
            rel_map = {}
            self.state["relationship_state"] = rel_map
        rel = rel_map.get(char_name)
        if not isinstance(rel, dict):
            baseline = max(0.0, min(100.0, float(affinity_score)))
            rel = {
                "trust": round(baseline, 1),
                "tension": round(max(0.0, min(100.0, 100.0 - baseline)), 1),
                "intimacy": round(max(0.0, min(100.0, baseline * 0.6)), 1),
                "relationship_stage": "熟悉",
                "recent_flags": [],
                "last_milestone_at": "",
            }
            rel_map[char_name] = rel
        if not isinstance(rel.get("recent_flags"), list):
            rel["recent_flags"] = []
        if "conflict_streak" not in rel:
            rel["conflict_streak"] = 0
        if "repair_streak" not in rel:
            rel["repair_streak"] = 0
        return rel

    def _push_relation_flag(self, rel: Dict[str, Any], flag: str):
        text = str(flag or "").strip()
        if not text:
            return
        flags = [str(item).strip() for item in rel.get("recent_flags", []) if str(item).strip()]
        flags = [item for item in flags if item != text]
        flags.insert(0, text)
        rel["recent_flags"] = flags[:5]

    def _stage_by_scores(self, trust: float, tension: float, intimacy: float) -> str:
        if tension >= 78 and trust <= 28:
            return "敌对"
        if intimacy >= 72 and trust >= 70 and tension <= 40:
            return "恋爱倾向"
        if intimacy >= 56 and trust >= 60 and tension <= 50:
            return "暧昧"
        if trust >= 62 and tension <= 53:
            return "朋友"
        if trust <= 47 and tension >= 54:
            return "紧张"
        return "熟悉"

    def _stabilize_stage(
        self,
        *,
        prev_stage: str,
        candidate_stage: str,
        prev_trust: float,
        prev_tension: float,
        prev_intimacy: float,
        trust: float,
        tension: float,
        intimacy: float,
    ) -> str:
        if not prev_stage or prev_stage == candidate_stage:
            return candidate_stage

        delta = max(
            abs(trust - prev_trust),
            abs(tension - prev_tension),
            abs(intimacy - prev_intimacy),
        )
        # 常规阶段（熟悉/紧张/朋友/暧昧）允许随累计变化及时切换；
        # 极端阶段（敌对/恋爱倾向）再做更严格的防抖。
        if candidate_stage in {"敌对", "恋爱倾向"} and delta < 1.8:
            return prev_stage

        # 敌对与恋爱倾向都需要更强证据，避免轻微噪音导致剧烈跳变
        if candidate_stage == "敌对" and not (tension >= 82 and trust <= 24):
            return prev_stage
        if candidate_stage == "恋爱倾向" and not (intimacy >= 78 and trust >= 74 and tension <= 36):
            return prev_stage

        # 允许从极端阶段“缓慢退阶”，避免来回抖动
        if prev_stage == "敌对" and candidate_stage != "敌对":
            if not (trust >= 44 and tension <= 64):
                return prev_stage
        if prev_stage == "恋爱倾向" and candidate_stage != "恋爱倾向":
            if not (intimacy <= 72 or trust <= 68 or tension >= 44):
                return prev_stage

        return candidate_stage

    def _add_long_term_milestone(self, text: str):
        milestone = str(text or "").strip()
        if not milestone:
            return
        items = [str(item).strip() for item in self.state.get("long_term_milestones", []) if str(item).strip()]
        existed = milestone in items
        items = [item for item in items if item != milestone]
        items.insert(0, milestone)
        self.state["long_term_milestones"] = items[:12]
        if not existed:
            self._new_milestones.append(milestone)

    def consume_new_milestones(self) -> List[str]:
        out = [str(item).strip() for item in self._new_milestones if str(item).strip()]
        self._new_milestones = []
        return out

    def _summarize_relationship_state(self, player_name: str, active_chars: List[str]) -> List[str]:
        rel_map = self.state.get("relationship_state", {})
        if not isinstance(rel_map, dict):
            return []
        lines: List[str] = []
        for name in active_chars[:6]:
            if name == player_name:
                continue
            rel = rel_map.get(name)
            if not isinstance(rel, dict):
                continue
            stage = str(rel.get("relationship_stage", "熟悉"))
            try:
                trust = float(rel.get("trust", 50) or 50)
            except Exception:
                trust = 50.0
            try:
                tension = float(rel.get("tension", 50) or 50)
            except Exception:
                tension = 50.0
            try:
                intimacy = float(rel.get("intimacy", 30) or 30)
            except Exception:
                intimacy = 30.0
            flag = ""
            recent_flags = rel.get("recent_flags", [])
            if isinstance(recent_flags, list) and recent_flags:
                flag = f"，最近：{recent_flags[0]}"
            lines.append(
                f"{name}：{stage}（信任{trust:.0f}/紧张{tension:.0f}/亲密{intimacy:.0f}）{flag}"
            )
        return lines[:4]

    def _update_relationship_state(
        self,
        *,
        player_name: str,
        event_obj,
        event_id: str,
        event_name: str,
        active_chars: List[str],
        affinity: Dict[str, float],
        action_text: str,
        effects_data: Dict[str, Any],
        dialogue_sequence: List[Dict[str, Any]],
        is_end: bool,
    ):
        aff_changes = effects_data.get("affinity_changes", {}) if isinstance(effects_data, dict) else {}
        if not isinstance(aff_changes, dict):
            aff_changes = {}

        action = str(action_text or "").strip()
        dialog_blob = " ".join(str(item.get("content", "")) for item in dialogue_sequence if isinstance(item, dict))
        event_marker = f"{event_id or 'evt'}"
        event_tags = [str(t).strip() for t in (getattr(event_obj, "narrative_tags", []) or []) if str(t).strip()]
        relation_keywords = ["关系", "暧昧", "约会", "冲突", "冷战", "和解", "升温", "恶化", "公开冲突"]
        event_is_relation = any(any(k in tag for k in relation_keywords) for tag in event_tags)
        arg_delta = 0
        try:
            arg_delta = int(float(effects_data.get("arg_delta", 0) or 0))
        except Exception:
            arg_delta = 0

        def _focus_multiplier(char_name: str) -> float:
            text = f"{event_id} {event_name} {action} {dialog_blob}".lower()
            name = str(char_name or "").strip()
            aliases = {
                "唐梦琪": ["唐梦琪", "梦琪", "tang_mengqi", "tang", "mengqi"],
                "林飒": ["林飒", "飒", "lin_sa", "lin", "sa"],
                "李一诺": ["李一诺", "一诺", "li_yinuo", "li", "yinuo"],
            }
            keys = aliases.get(name, [name])
            hit = 0
            for key in keys:
                token = str(key or "").strip()
                if not token:
                    continue
                if token.lower() in text:
                    hit += 1
            if hit >= 2:
                return 1.45
            if hit == 1:
                return 1.2
            return 0.45

        for name in active_chars:
            if name == player_name:
                continue
            try:
                affinity_score = float(affinity.get(name, 50))
            except Exception:
                affinity_score = 50.0
            rel = self._get_or_create_relation(name, affinity_score)

            trust = float(rel.get("trust", 50) or 50)
            tension = float(rel.get("tension", 50) or 50)
            intimacy = float(rel.get("intimacy", 30) or 30)
            prev_trust = trust
            prev_tension = tension
            prev_intimacy = intimacy

            delta_aff = 0.0
            if name in aff_changes:
                try:
                    delta_aff = float(aff_changes.get(name, 0) or 0)
                except Exception:
                    delta_aff = 0.0
            focus = _focus_multiplier(name)

            # 让关系变量更快追随外层 affinity 变化，减少“数值变了但关系不动”的割裂感
            trust += delta_aff * 1.35
            intimacy += delta_aff * 0.95
            tension -= delta_aff * 1.15

            # 温和拉回到 affinity 基线，保证长期行为可以累积成阶段变化
            trust += (affinity_score - trust) * 0.12
            tension += ((100.0 - affinity_score) - tension) * 0.10

            if any(k in action for k in ["安慰", "缓和", "打圆场", "帮", "维护"]):
                trust += 2.2 * focus
                tension -= 1.4 * focus
                intimacy += 0.7 * focus
            if any(k in action for k in ["质问", "回怼", "拒绝", "硬刚"]):
                tension += 2.6 * focus
                trust -= 1.5 * focus
            if any(k in action for k in ["沉默", "观察", "先看看"]):
                trust -= 0.5 * focus

            if any(k in dialog_blob for k in ["谢谢", "我站你", "相信你", "我来帮你"]):
                trust += 1.8 * focus
                intimacy += 1.2 * focus
            if any(k in dialog_blob for k in ["闭嘴", "滚", "烦死", "有病", "别碰我"]):
                tension += 2.8 * focus
                trust -= 1.7 * focus

            if event_is_relation:
                if delta_aff >= 0:
                    trust += 0.8 * focus
                    intimacy += 0.6 * focus
                else:
                    tension += 0.9 * focus
                    trust -= 0.6 * focus

            if arg_delta > 0:
                tension += 2.2 * min(arg_delta, 2) * focus
                trust -= 1.3 * min(arg_delta, 2) * focus

            conflict_signal = (
                delta_aff <= -1
                or any(k in action for k in ["质问", "回怼", "拒绝", "硬刚"])
                or any(k in dialog_blob for k in ["闭嘴", "滚", "烦死", "有病", "别碰我", "吵"])
                or arg_delta > 0
            )
            repair_signal = (
                delta_aff >= 1
                or any(k in action for k in ["安慰", "缓和", "打圆场", "帮", "维护", "道歉"])
                or any(k in dialog_blob for k in ["谢谢", "我站你", "相信你", "我来帮你", "抱歉", "对不起"])
            )
            if conflict_signal and not repair_signal:
                rel["conflict_streak"] = int(rel.get("conflict_streak", 0) or 0) + 1
                rel["repair_streak"] = 0
            elif repair_signal and not conflict_signal:
                rel["repair_streak"] = int(rel.get("repair_streak", 0) or 0) + 1
                rel["conflict_streak"] = 0
            else:
                rel["conflict_streak"] = max(0, int(rel.get("conflict_streak", 0) or 0) - 1)
                rel["repair_streak"] = max(0, int(rel.get("repair_streak", 0) or 0) - 1)

            if int(rel.get("conflict_streak", 0) or 0) >= 2:
                tension += 1.8 * focus
                trust -= 1.1 * focus
            if int(rel.get("repair_streak", 0) or 0) >= 2:
                trust += 1.6 * focus
                intimacy += 1.2 * focus
                tension -= 0.9 * focus

            trust = max(0.0, min(100.0, trust))
            tension = max(0.0, min(100.0, tension))
            intimacy = max(0.0, min(100.0, intimacy))
            prev_stage = str(rel.get("relationship_stage", "熟悉"))
            candidate_stage = self._stage_by_scores(trust, tension, intimacy)
            stage = self._stabilize_stage(
                prev_stage=prev_stage,
                candidate_stage=candidate_stage,
                prev_trust=prev_trust,
                prev_tension=prev_tension,
                prev_intimacy=prev_intimacy,
                trust=trust,
                tension=tension,
                intimacy=intimacy,
            )
            # 兜底：当分值已经明显跨入新阶段却仍被防抖挡住时，强制落位，避免“数值极端但阶段不变”。
            if stage == "熟悉" and candidate_stage != "熟悉":
                if (
                    (candidate_stage == "敌对" and tension >= 86 and trust <= 26)
                    or (candidate_stage == "恋爱倾向" and intimacy >= 76 and trust >= 72 and tension <= 38)
                    or (candidate_stage == "紧张" and tension >= 58 and trust <= 44)
                    or (candidate_stage == "朋友" and trust >= 66 and tension <= 50)
                    or (candidate_stage == "暧昧" and intimacy >= 60 and trust >= 62 and tension <= 48)
                ):
                    stage = candidate_stage

            rel["trust"] = round(trust, 1)
            rel["tension"] = round(tension, 1)
            rel["intimacy"] = round(intimacy, 1)
            rel["relationship_stage"] = stage

            if delta_aff >= 3:
                self._push_relation_flag(rel, "关系明显升温")
            elif delta_aff <= -3:
                self._push_relation_flag(rel, "关系明显受损")
            elif delta_aff > 0:
                self._push_relation_flag(rel, "关系小幅改善")
            elif delta_aff < 0:
                self._push_relation_flag(rel, "关系小幅恶化")

            if any(k in action for k in ["安慰", "打圆场", "维护"]):
                self._push_relation_flag(rel, "主角主动维护场面")
            if any(k in action for k in ["质问", "回怼", "拒绝", "硬刚"]):
                self._push_relation_flag(rel, "发生正面冲突")

            if stage != prev_stage:
                milestone = f"{name} 与 {player_name} 关系阶段变化：{prev_stage} -> {stage}（{event_name or event_marker}）"
                rel["last_milestone_at"] = event_marker
                self._push_relation_flag(rel, f"阶段变化：{prev_stage}->{stage}")
                self._add_long_term_milestone(milestone)

            if is_end and event_name:
                snapshot = f"{event_name}结束：{name} 当前为{stage}（信任{trust:.0f}/紧张{tension:.0f}/亲密{intimacy:.0f}）"
                self._add_long_term_milestone(snapshot)

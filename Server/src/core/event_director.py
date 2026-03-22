import random
import json
import os
import re
import copy
from collections import deque
from src.core.event_script import load_user_events
from src.core.config import get_user_events_dir

class EventDirector:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        from src.core.config import get_user_events_dir, DEFAULT_EVENTS_DIR
        self.events_dir = get_user_events_dir(user_id)
        self.default_events_dir = DEFAULT_EVENTS_DIR
        self.timeline_path = os.path.join(self.events_dir, "timeline.json")
        self.default_timeline_path = os.path.join(self.default_events_dir, "timeline.json")
        
        self.used_events = []
        self.recent_events = deque(maxlen=6)
        self.event_last_picked = {}
        self.pick_counter = 0
        self.current_chapter = 1
        self.chapter_progress = 0
        self.event_database = load_user_events(user_id)
        self.timeline_config = self._load_timeline()
        self.relationship_feedback_window = 0
        self.relationship_feedback_tags = []
        self._seen_relation_shift_markers = set()
        self.affinity_feedback_window = 0
        self.affinity_feedback_tags = []
        self.affinity_feedback_target = None
        self.last_affinity_snapshot = {}
        self.affinity_shock_threshold = 8.0
        self.affinity_feedback_trigger_prob = 0.68
        self.materialized_origin_map = {}
        
    def reset(self):
        self.used_events = []
        self.recent_events.clear()
        self.event_last_picked = {}
        self.pick_counter = 0
        self.current_chapter = 1
        self.chapter_progress = 0
        self.relationship_feedback_window = 0
        self.relationship_feedback_tags = []
        self._seen_relation_shift_markers = set()
        self.affinity_feedback_window = 0
        self.affinity_feedback_tags = []
        self.affinity_feedback_target = None
        self.last_affinity_snapshot = {}
        self.materialized_origin_map = {}
        
    def reload_timeline(self):
        """支持热更新读取"""
        self.event_database = load_user_events(self.user_id)
        self.timeline_config = self._load_timeline()

    def _load_timeline(self):
        if os.path.exists(self.timeline_path):
            try:
                with open(self.timeline_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Timeline 读取失败: {e}")
        
        # 2. Try default timeline path
        if os.path.exists(self.default_timeline_path):
            try:
                with open(self.default_timeline_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass

        default_timeline = {
            "1": ["开局", "固定", "通用", "随机或专属", "固定", "Boss"],
            "2": ["固定", "通用", "随机或专属", "固定", "Boss"],
            "3": ["固定", "通用", "条件", "随机或专属", "Boss"],
            "4": ["固定", "随机或专属", "通用", "Boss"]
        }
        
        os.makedirs(os.path.dirname(self.timeline_path), exist_ok=True)
        with open(self.timeline_path, 'w', encoding='utf-8') as f:
            json.dump(default_timeline, f, ensure_ascii=False, indent=4)
            
        return default_timeline

    def _check_conditions(self, event, player_stats, active_chars, affinity):
        """动态条件解析引擎"""
        
        # 1. 检查【专属角色】(支持逗号分隔，要求全部在场)
        if hasattr(event, 'exclusive_char') and event.exclusive_char:
            # 将中文逗号转为英文逗号并分割
            req_chars = [c.strip() for c in event.exclusive_char.replace('，', ',').split(',') if c.strip()]
            for rc in req_chars:
                if rc not in active_chars:
                    return False # 只要有一个需要的人不在场，直接毙掉

        # 2. 检查【触发条件】(支持 San<40 & 唐梦琪>60 这种复合语法)
        if hasattr(event, 'trigger_conditions') and event.trigger_conditions:
            cond_str = event.trigger_conditions.replace('＆', '&').replace('，', '&').replace(',', '&')
            conditions = [c.strip() for c in cond_str.split('&') if c.strip()]
            
            for cond in conditions:
                # 解析诸如 "San < 40" 或 "唐梦琪 >= 60"
                match = re.match(r'(.+?)(>=|<=|>|<|==|!=)(.+)', cond)
                if not match: continue
                
                key, op, val_str = match.groups()
                key = key.strip()
                try: 
                    val = float(val_str.strip())
                except: 
                    continue
                
                # 动态获取玩家状态或好感度
                actual_val = 50 
                k_lower = key.lower()
                if k_lower in ['san', 'sanity']: actual_val = player_stats.get('san', 100)
                elif k_lower in ['money']: actual_val = player_stats.get('money', 0)
                elif k_lower in ['gpa']: actual_val = player_stats.get('gpa', 3.0)
                elif k_lower in ['hygiene']: actual_val = player_stats.get('hygiene', 100)
                elif k_lower in ['reputation', 'rep']: actual_val = player_stats.get('reputation', 50) 
                elif (k_lower in ['affinity', '好感度', '好感']) and hasattr(event, 'exclusive_char') and event.exclusive_char:
                    # 如果是角色专属事件，Affinity 代指该角色的好感度
                    first_char = [c.strip() for c in event.exclusive_char.replace('，', ',').split(',') if c.strip()][0]
                    actual_val = affinity.get(first_char, 50)
                elif key in affinity: actual_val = affinity[key]
                else: 
                    print(f"⚠️ [条件引擎警告] 未知变量 '{key}'，已拦截事件: {event.id}")
                    return False

                # 动态比较运算符
                if op == '>' and not (actual_val > val): return False
                if op == '<' and not (actual_val < val): return False
                if op == '>=' and not (actual_val >= val): return False
                if op == '<=' and not (actual_val <= val): return False
                if op == '==' and not (actual_val == val): return False
                if op == '!=' and not (actual_val != val): return False
                
        return True

    def _matches_expected_type(self, expected_type: str, event) -> bool:
        exp = str(expected_type or "")
        evt_type = str(getattr(event, "event_type", "") or "")

        is_boss = bool(getattr(event, "is_boss", False))
        is_opening = "开局" in evt_type
        is_fixed = "固定" in evt_type
        is_conditional = "条件" in evt_type
        is_persona = "专属" in evt_type
        is_general = ("通用" in evt_type or "随机" in evt_type)

        if "Boss" in exp:
            return is_boss
        if "开局" in exp:
            return is_opening
        if "固定" in exp:
            return is_fixed
        if "专属" in exp:
            return is_persona
        if "条件" in exp:
            return is_conditional
        if "通用" in exp:
            return is_general or is_fixed
        if "随机或专属" in exp:
            return is_general or is_persona or is_fixed
        return True

    def _event_weight(self, event, narrative_state=None) -> float:
        try:
            base_weight = max(0.1, float(getattr(event, "event_weight", 1.0) or 1.0))
        except Exception:
            base_weight = 1.0

        if not isinstance(narrative_state, dict):
            return base_weight

        tags = [str(item).strip() for item in (getattr(event, "narrative_tags", []) or []) if str(item).strip()]
        if not tags:
            return base_weight

        score = 1.0
        room_tension = str(narrative_state.get("room_tension", "") or "")
        player_arc = " ".join(str(item) for item in narrative_state.get("player_arc", []) if item)
        active_threads = " ".join(str(item) for item in narrative_state.get("active_threads", []) if item)
        state_blob = f"{room_tension} {player_arc} {active_threads}"

        tag_rules = {
            "争吵": ["火药", "争执", "冷战", "带刺"],
            "尴尬": ["尴尬", "没说开", "别扭"],
            "缓和": ["和事", "和平", "收场"],
            "压力": ["压力", "强撑", "迟疑", "敏感"],
            "关系": ["信任", "不耐烦", "帮腔", "面子"],
        }
        for tag in tags:
            for rule_tag, keywords in tag_rules.items():
                if rule_tag in tag and any(keyword in state_blob for keyword in keywords):
                    score += 0.25
                    break

        score *= self._relationship_weight_from_state(tags, narrative_state)

        return max(0.1, base_weight * score)

    def _relationship_feedback_tags_for_stage(self, stage: str):
        st = str(stage or "").strip()
        if st in {"敌对", "紧张"}:
            return ["关系-恶化", "公开冲突", "冷战", "争吵"]
        if st in {"恋爱倾向", "暧昧"}:
            return ["暧昧推进", "约会", "关系-升温", "关系-和解"]
        if st in {"朋友"}:
            return ["关系-升温", "关系-和解"]
        return ["关系"]

    def _extract_latest_relation_shift(self, narrative_state):
        if not isinstance(narrative_state, dict):
            return None
        milestones = [str(item).strip() for item in narrative_state.get("long_term_milestones", []) if str(item).strip()]
        for text in milestones[:3]:
            if "关系阶段变化" not in text or "->" not in text:
                continue
            # 形如：xxx：紧张 -> 朋友（evt_x）
            try:
                right = text.split("->", 1)[1]
                stage = right.split("（", 1)[0].strip()
                marker = text
                return {"stage": stage, "marker": marker}
            except Exception:
                continue
        return None

    def _update_relationship_feedback_window(self, narrative_state):
        shift = self._extract_latest_relation_shift(narrative_state)
        if not shift:
            return
        marker = str(shift.get("marker", "") or "").strip()
        if not marker or marker in self._seen_relation_shift_markers:
            return
        self._seen_relation_shift_markers.add(marker)
        stage = str(shift.get("stage", "") or "").strip()
        self.relationship_feedback_window = 3
        self.relationship_feedback_tags = self._relationship_feedback_tags_for_stage(stage)

    def _event_matches_relation_feedback(self, event, target_tags):
        if not target_tags:
            return False
        evt_tags = [str(item).strip() for item in (getattr(event, "narrative_tags", []) or []) if str(item).strip()]
        if not evt_tags:
            return False
        for evt_tag in evt_tags:
            for target in target_tags:
                if target and target in evt_tag:
                    return True
        return False

    def _update_affinity_feedback_window(self, active_chars, affinity):
        names = [str(n).strip() for n in (active_chars or []) if str(n).strip()]
        if not names or not isinstance(affinity, dict):
            return

        current = {}
        deltas = []
        for name in names:
            try:
                val = float(affinity.get(name, 50))
            except Exception:
                val = 50.0
            current[name] = val
            if name in self.last_affinity_snapshot:
                deltas.append((name, val - float(self.last_affinity_snapshot.get(name, 50.0))))

        # 初始化快照，不触发反馈
        if not self.last_affinity_snapshot:
            self.last_affinity_snapshot = current
            return

        if deltas:
            target_name, target_delta = max(deltas, key=lambda x: abs(x[1]))
            if abs(target_delta) >= float(self.affinity_shock_threshold):
                if target_delta > 0:
                    tags = ["约会", "暧昧推进", "关系-升温", "关系-和解"]
                else:
                    tags = ["关系-恶化", "公开冲突", "冷战", "争吵"]
                self.affinity_feedback_window = 2
                self.affinity_feedback_tags = tags
                self.affinity_feedback_target = str(target_name)
                print(
                    "🎯 [事件调度] 检测到好感波动触发窗口："
                    f"{target_name} Δ{target_delta:+.1f}，窗口={self.affinity_feedback_window}"
                )

        self.last_affinity_snapshot.update(current)

    def _event_matches_target_char(self, event, target_name):
        if not target_name:
            return True
        target = str(target_name).strip()
        if not target:
            return True
        exclusive = str(getattr(event, "exclusive_char", "") or "")
        if exclusive:
            req_chars = [c.strip() for c in exclusive.replace('，', ',').split(',') if c.strip()]
            if req_chars and target not in req_chars:
                return False
        return True

    def _is_template_event(self, event) -> bool:
        if not event:
            return False
        placeholder_patterns = [
            r"\[\[?\s*TARGET\s*\]?\]",
            r"\{\{\s*TARGET\s*\}\}",
            r"【\s*TARGET\s*】",
            r"<\s*TARGET\s*>",
        ]
        def _contains_token(obj) -> bool:
            if isinstance(obj, str):
                return any(re.search(pat, obj, flags=re.IGNORECASE) for pat in placeholder_patterns)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if _contains_token(str(k)) or _contains_token(v):
                        return True
                return False
            if isinstance(obj, list):
                return any(_contains_token(item) for item in obj)
            return False

        candidates = [
            getattr(event, "name", ""),
            getattr(event, "description", ""),
            getattr(event, "opening_goal", ""),
            getattr(event, "pressure_goal", ""),
            getattr(event, "turning_goal", ""),
            getattr(event, "settlement_goal", ""),
            getattr(event, "fallback_consequence", ""),
            getattr(event, "options", {}),
            getattr(event, "outcomes", {}),
            getattr(event, "potential_conflicts", []),
            getattr(event, "progress_beats", []),
            getattr(event, "end_signals", []),
            getattr(event, "fixed_dialogue", []),
        ]
        return any(_contains_token(obj) for obj in candidates)

    def _pick_relation_target(self, active_chars, affinity, narrative_state):
        chars = [str(c).strip() for c in (active_chars or []) if str(c).strip()]
        if not chars:
            return None
        rel_map = {}
        if isinstance(narrative_state, dict):
            rel_map = narrative_state.get("relationship_state", {}) or {}
        if isinstance(rel_map, dict):
            ranked = []
            for name in chars:
                rel = rel_map.get(name)
                if not isinstance(rel, dict):
                    continue
                try:
                    tension = float(rel.get("tension", 50) or 50)
                except Exception:
                    tension = 50.0
                try:
                    trust = float(rel.get("trust", 50) or 50)
                except Exception:
                    trust = 50.0
                try:
                    intimacy = float(rel.get("intimacy", 30) or 30)
                except Exception:
                    intimacy = 30.0
                score = tension - trust * 0.6 - intimacy * 0.2
                ranked.append((score, name))
            if ranked:
                ranked.sort(reverse=True)
                return ranked[0][1]

        # 回退：按 affinity 最低者
        def _aff(n):
            try:
                return float((affinity or {}).get(n, 50))
            except Exception:
                return 50.0
        chars_sorted = sorted(chars, key=_aff)
        return chars_sorted[0] if chars_sorted else None

    def _replace_target_tokens(self, text, target_name):
        raw = str(text or "")
        if not raw:
            return raw
        patterns = [
            r"\[\[?\s*TARGET\s*\]?\]",
            r"\{\{\s*TARGET\s*\}\}",
            r"【\s*TARGET\s*】",
            r"<\s*TARGET\s*>",
        ]
        for pat in patterns:
            raw = re.sub(pat, str(target_name), raw, flags=re.IGNORECASE)
        return raw

    def _replace_target_in_obj(self, obj, target_name):
        if isinstance(obj, str):
            return self._replace_target_tokens(obj, target_name)
        if isinstance(obj, dict):
            replaced = {}
            for k, v in obj.items():
                new_k = self._replace_target_tokens(k, target_name)
                replaced[new_k] = self._replace_target_in_obj(v, target_name)
            return replaced
        if isinstance(obj, list):
            return [self._replace_target_in_obj(item, target_name) for item in obj]
        return obj

    def _materialize_template_event(self, event, *, active_chars, affinity, narrative_state):
        if not self._is_template_event(event):
            return event
        target = self._pick_relation_target(active_chars, affinity, narrative_state)
        if not target:
            return event

        materialized = copy.deepcopy(event)
        base_id = str(getattr(event, "id", "") or "")
        safe_target = re.sub(r"[^0-9a-zA-Z_\u4e00-\u9fff]+", "_", str(target))
        materialized.id = f"{base_id}__tgt_{safe_target}"
        # ScriptedEvent 是严格模型，不能随意写入未定义字段；模板来源单独由 director 维护。
        if not hasattr(self, "materialized_origin_map") or not isinstance(self.materialized_origin_map, dict):
            self.materialized_origin_map = {}
        self.materialized_origin_map[materialized.id] = base_id
        materialized.name = self._replace_target_tokens(getattr(event, "name", ""), target)
        materialized.description = self._replace_target_tokens(getattr(event, "description", ""), target)
        materialized.opening_goal = self._replace_target_tokens(getattr(event, "opening_goal", ""), target)
        materialized.pressure_goal = self._replace_target_tokens(getattr(event, "pressure_goal", ""), target)
        materialized.turning_goal = self._replace_target_tokens(getattr(event, "turning_goal", ""), target)
        materialized.settlement_goal = self._replace_target_tokens(getattr(event, "settlement_goal", ""), target)
        materialized.fallback_consequence = self._replace_target_tokens(getattr(event, "fallback_consequence", ""), target)
        materialized.exclusive_char = str(target)
        if isinstance(getattr(event, "potential_conflicts", None), list):
            materialized.potential_conflicts = [self._replace_target_tokens(x, target) for x in event.potential_conflicts]
        if isinstance(getattr(event, "progress_beats", None), list):
            materialized.progress_beats = [self._replace_target_tokens(x, target) for x in event.progress_beats]
        if isinstance(getattr(event, "end_signals", None), list):
            materialized.end_signals = [self._replace_target_tokens(x, target) for x in event.end_signals]
        if isinstance(getattr(event, "options", None), dict):
            materialized.options = {k: self._replace_target_tokens(v, target) for k, v in event.options.items()}
        if isinstance(getattr(event, "outcomes", None), dict):
            materialized.outcomes = {k: self._replace_target_tokens(v, target) for k, v in event.outcomes.items()}
        if isinstance(getattr(event, "fixed_dialogue", None), list):
            materialized.fixed_dialogue = self._replace_target_in_obj(event.fixed_dialogue, target)
        return materialized

    def _relationship_weight_from_state(self, tags, narrative_state) -> float:
        if not isinstance(narrative_state, dict):
            return 1.0
        rel_map = narrative_state.get("relationship_state", {})
        if not isinstance(rel_map, dict) or not rel_map:
            return 1.0

        def _num(v, default):
            try:
                return float(v)
            except Exception:
                return default

        max_tension = 0.0
        min_trust = 100.0
        max_trust = 0.0
        max_intimacy = 0.0
        stage_hits = set()
        for _, rel in rel_map.items():
            if not isinstance(rel, dict):
                continue
            trust = _num(rel.get("trust", 50), 50.0)
            tension = _num(rel.get("tension", 50), 50.0)
            intimacy = _num(rel.get("intimacy", 30), 30.0)
            stage = str(rel.get("relationship_stage", "") or "").strip()

            max_tension = max(max_tension, tension)
            min_trust = min(min_trust, trust)
            max_trust = max(max_trust, trust)
            max_intimacy = max(max_intimacy, intimacy)
            if stage:
                stage_hits.add(stage)

        milestones = [str(item).strip() for item in narrative_state.get("long_term_milestones", []) if str(item).strip()]
        has_recent_stage_shift = any("关系阶段变化" in item for item in milestones[:3])

        score = 1.0
        for tag in tags:
            t = str(tag or "").strip()
            if not t:
                continue
            if any(key in t for key in ["关系-恶化", "公开冲突", "冷战", "争吵"]):
                if max_tension >= 70 or min_trust <= 35 or ("敌对" in stage_hits or "紧张" in stage_hits):
                    score += 0.35
            if any(key in t for key in ["关系-升温", "和解"]):
                if max_trust >= 65 and max_tension <= 55:
                    score += 0.28
            if any(key in t for key in ["暧昧推进", "约会", "亲密"]):
                if max_intimacy >= 60 and max_trust >= 65 and max_tension <= 50:
                    score += 0.35
            if has_recent_stage_shift and any(key in t for key in ["关系", "暧昧", "和解", "冲突"]):
                score += 0.18

        return max(0.7, min(score, 2.2))

    def _in_cooldown(self, event) -> bool:
        event_id = str(getattr(event, "id", "") or "")
        if not event_id:
            return False
        try:
            cd = max(0, int(getattr(event, "cooldown_turns", 2) or 2))
        except Exception:
            cd = 2
        last_picked = self.event_last_picked.get(event_id)
        if last_picked is None:
            return False
        return (self.pick_counter - last_picked) <= cd

    def _weighted_pick(self, pool, narrative_state=None):
        if not pool:
            return None
        try:
            weights = [self._event_weight(e, narrative_state) for e in pool]
            return random.choices(pool, weights=weights, k=1)[0]
        except Exception:
            return random.choice(pool)

    def get_next_event(self, player_stats, active_chars, affinity=None, narrative_state=None):
        if affinity is None: affinity = {}
        self._update_relationship_feedback_window(narrative_state)
        self._update_affinity_feedback_window(active_chars, affinity)
        
        if str(self.current_chapter) not in self.timeline_config:
            return None
            
        chapter_pools = self.timeline_config[str(self.current_chapter)]
        if self.chapter_progress >= len(chapter_pools):
            self.current_chapter += 1
            self.chapter_progress = 0
            return self.get_next_event(player_stats, active_chars, affinity, narrative_state)
            
        expected_type = chapter_pools[self.chapter_progress]
        self.chapter_progress += 1
        boss_slot = "Boss" in str(expected_type)
        
        # 初筛：拿出当前章节的所有未触发事件
        available_events = []
        for e in self.event_database.values():
            if e.chapter != self.current_chapter:
                continue
            if not getattr(e, "allow_repeat", False) and e.id in self.used_events:
                continue
            available_events.append(e)

        if not available_events:
            print(f"🔄 [事件调度] 第 {self.current_chapter} 章可用事件为空，推进到下一章。")
            self.current_chapter += 1
            self.chapter_progress = 0
            return self.get_next_event(player_stats, active_chars, affinity, narrative_state)

        # 分层筛选：优先满足类型+条件+去重，其次逐步放宽，避免“定义太硬”导致卡死。
        strict_pool = [
            e for e in available_events
            if self._matches_expected_type(expected_type, e)
            and self._check_conditions(e, player_stats, active_chars, affinity)
            and (e.id not in self.recent_events)
            and (not self._in_cooldown(e))
        ]
        soft_pool = [
            e for e in available_events
            if self._matches_expected_type(expected_type, e)
            and self._check_conditions(e, player_stats, active_chars, affinity)
        ]
        chapter_pool = [
            e for e in available_events
            if self._check_conditions(e, player_stats, active_chars, affinity)
            and (e.id not in self.recent_events)
        ]
        fallback_pool = [
            e for e in available_events
            if self._check_conditions(e, player_stats, active_chars, affinity)
        ]
        emergency_pool = list(available_events)

        if not boss_slot:
            strict_pool = [e for e in strict_pool if not getattr(e, "is_boss", False)]
            soft_pool = [e for e in soft_pool if not getattr(e, "is_boss", False)]
            chapter_pool = [e for e in chapter_pool if not getattr(e, "is_boss", False)]
            fallback_pool = [e for e in fallback_pool if not getattr(e, "is_boss", False)]
            non_boss_emergency = [e for e in emergency_pool if not getattr(e, "is_boss", False)]
            if non_boss_emergency:
                emergency_pool = non_boss_emergency

        valid_pool = strict_pool or soft_pool or chapter_pool or fallback_pool or emergency_pool

        if valid_pool is emergency_pool:
            print(f"⚠️ [事件调度] 第 {self.current_chapter} 章条件过严，已启用无条件兜底。")
        chosen = None
        if self.relationship_feedback_window > 0 and self.relationship_feedback_tags:
            relation_pool = [e for e in valid_pool if self._event_matches_relation_feedback(e, self.relationship_feedback_tags)]
            if relation_pool:
                chosen = self._weighted_pick(relation_pool, narrative_state)
                self.relationship_feedback_window = 0
                self.relationship_feedback_tags = []
                print("🎯 [事件调度] 命中关系反馈窗口，优先发放关系联动事件。")
            else:
                self.relationship_feedback_window = max(0, int(self.relationship_feedback_window) - 1)
                if self.relationship_feedback_window == 0:
                    self.relationship_feedback_tags = []

        if not chosen:
            if self.affinity_feedback_window > 0 and self.affinity_feedback_tags:
                trigger = random.random() <= float(self.affinity_feedback_trigger_prob)
                if trigger:
                    target = str(self.affinity_feedback_target or "").strip()
                    affinity_pool = [
                        e for e in valid_pool
                        if self._event_matches_relation_feedback(e, self.affinity_feedback_tags)
                        and self._event_matches_target_char(e, target)
                    ]
                    # 允许在目标角色专属事件不足时，退化为关系标签池，避免过窄导致无事发生。
                    if not affinity_pool:
                        affinity_pool = [
                            e for e in valid_pool
                            if self._event_matches_relation_feedback(e, self.affinity_feedback_tags)
                        ]
                    if affinity_pool:
                        chosen = self._weighted_pick(affinity_pool, narrative_state)
                        self.affinity_feedback_window = 0
                        self.affinity_feedback_tags = []
                        self.affinity_feedback_target = None
                        print("🎯 [事件调度] 命中好感波动窗口，发放关系特化事件。")
                    else:
                        self.affinity_feedback_window = max(0, int(self.affinity_feedback_window) - 1)
                        if self.affinity_feedback_window == 0:
                            self.affinity_feedback_tags = []
                            self.affinity_feedback_target = None
                else:
                    self.affinity_feedback_window = max(0, int(self.affinity_feedback_window) - 1)
                    if self.affinity_feedback_window == 0:
                        self.affinity_feedback_tags = []
                        self.affinity_feedback_target = None
        if not chosen:
            chosen = self._weighted_pick(valid_pool, narrative_state)
        if not chosen:
            return None

        chosen = self._materialize_template_event(
            chosen,
            active_chars=active_chars,
            affinity=affinity,
            narrative_state=narrative_state,
        )
        chosen_id = str(getattr(chosen, "id", "") or "")
        if chosen_id and chosen_id not in self.event_database:
            # 模板实例化后的事件需要可被下一回合按 ID 继续读取。
            self.event_database[chosen_id] = chosen

        if not getattr(chosen, "allow_repeat", False):
            self.used_events.append(chosen.id)
            template_base_id = str(self.materialized_origin_map.get(str(getattr(chosen, "id", "") or ""), "") or "")
            if template_base_id:
                self.used_events.append(template_base_id)
        self.recent_events.append(chosen.id)
        self.event_last_picked[chosen.id] = self.pick_counter
        self.pick_counter += 1
        return chosen

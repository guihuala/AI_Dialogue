from __future__ import annotations

import json
import os
import random
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.config import DEFAULT_EVENTS_DIR, get_user_events_dir


class EventSkeletonEngine:
    """System-side event scheduler for P0-2.

    Notes:
    - This engine does not replace current narrative flow yet.
    - It provides deterministic day plans (daily/key) as a compatibility layer.
    """

    def __init__(self, user_id: str = "default", definitions: Optional[List[Dict[str, Any]]] = None):
        self.user_id = user_id
        self.events_dir = get_user_events_dir(user_id)
        self.default_events_dir = DEFAULT_EVENTS_DIR
        self.skeleton_path = os.path.join(self.events_dir, "event_skeletons.json")
        self.default_skeleton_path = os.path.join(self.default_events_dir, "event_skeletons.json")
        self.definitions: List[Dict[str, Any]] = self._load_definitions(definitions)
        self.runtime: Dict[str, Any] = {
            "last_trigger_day": {},  # event_id -> day
            "triggered_once": set(),
            "daily_plan_cache": {},  # day -> plan
            "resolved_key_by_day": {},  # day -> event_id
            "last_key_offer_day": 0,  # day when key event was offered
        }

    def reset(self) -> None:
        self.runtime = {
            "last_trigger_day": {},
            "triggered_once": set(),
            "daily_plan_cache": {},
            "resolved_key_by_day": {},
            "last_key_offer_day": 0,
        }

    def reload(self) -> None:
        self.definitions = self._load_definitions(None)
        self.reset()

    def _load_definitions(self, definitions: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if isinstance(definitions, list):
            return self._ensure_baseline_events(self._normalize_definitions(definitions))

        for path in [self.skeleton_path, self.default_skeleton_path]:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    items = data.get("events", [])
                else:
                    items = data
                if isinstance(items, list) and items:
                    return self._ensure_baseline_events(self._normalize_definitions(items))
            except Exception:
                continue
        return self._ensure_baseline_events(self._normalize_definitions(self._default_definitions()))

    def _normalize_definitions(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            event_id = str(raw.get("id", "")).strip()
            if not event_id:
                continue
            evt_type = str(raw.get("type", "daily")).strip().lower()
            if evt_type not in {"daily", "key"}:
                evt_type = "daily"
            out.append(
                {
                    "id": event_id,
                    "type": evt_type,
                    "title": str(raw.get("title", event_id)).strip(),
                    "priority": int(raw.get("priority", 50) or 50),
                    "cooldown_days": max(0, int(raw.get("cooldown_days", 0) or 0)),
                    "once": bool(raw.get("once", False)),
                    "triggers": deepcopy(raw.get("triggers", {})) if isinstance(raw.get("triggers"), dict) else {},
                    "options": deepcopy(raw.get("options", [])) if isinstance(raw.get("options"), list) else [],
                    "meta": deepcopy(raw.get("meta", {})) if isinstance(raw.get("meta"), dict) else {},
                    "info_gate": deepcopy(raw.get("info_gate", {})) if isinstance(raw.get("info_gate"), dict) else {},
                }
            )
        return out

    def _ensure_baseline_events(self, defs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = list(defs or [])
        ids = {str(x.get("id", "")).strip() for x in out if isinstance(x, dict)}
        baseline_defs = [
            {
                "id": "daily_proactive_chat_ping",
                "type": "daily",
                "title": "室友主动找你搭话",
                "priority": 60,
                "cooldown_days": 1,
                "once": False,
                "triggers": {"day_min": 1, "active_any": ["lin_sa"]},
                "meta": {
                    "injected": True,
                    "npc_proactive": True,
                    "npc_proactive_weight": 10,
                    "kind": "chat",
                    "initiator": "lin_sa",
                    "weekly_bias": {"repair": 8, "calm": 4},
                    "relation_stage_bias": {"lin_sa": {"tense": 6, "familiar": 2}},
                    "public_line": "晚自习后，林飒主动把你叫到阳台，像是有话想说。",
                    "info_fragments": [
                        {"text": "你听见她反复提到‘先别把话说死’。", "info_gate": {"day_min": 1}},
                        {"text": "她语气比平时急，像在替某人兜底。", "info_gate": {"relation_target": {"char": "lin_sa", "trust_gte": 54}}},
                    ],
                },
            },
            {
                "id": "key_daily_room_decision",
                "type": "key",
                "title": "寝室临时决策",
                "priority": 52,
                "cooldown_days": 1,
                "once": False,
                "triggers": {"day_min": 1},
                "options": [
                    {"id": "support", "attitude": "支持", "effects": {"dorm_mood_delta": 2}},
                    {"id": "neutral", "attitude": "中立", "effects": {"dorm_mood_delta": 0}},
                    {"id": "avoid", "attitude": "回避", "effects": {"dorm_mood_delta": -2}},
                ],
                "meta": {"injected": True},
            },
            {
                "id": "key_chain_conflict_spark",
                "type": "key",
                "title": "冲突链：火药味升级",
                "priority": 76,
                "cooldown_days": 2,
                "once": False,
                "triggers": {
                    "day_min": 2,
                    "relation_any": {"tension_gte": 50},
                    "relation_stage_any": ["normal", "familiar", "tense", "hostile"],
                    "flags_all_false": ["chain_conflict_done"],
                },
                "options": [
                    {
                        "id": "confront",
                        "attitude": "对抗",
                        "effects": {
                            "dorm_mood_delta": -3,
                            "relation_delta": {
                                "tang_mengqi": {"trust": -8, "tension": 12, "intimacy": -5},
                                "lin_sa": {"trust": -4, "tension": 6, "intimacy": -2},
                            },
                            "set_flags": {"chain_conflict_started": True},
                            "memory_tags": ["chain:conflict:spark"],
                        },
                    },
                    {
                        "id": "mediate",
                        "attitude": "支持",
                        "effects": {
                            "dorm_mood_delta": 1,
                            "set_flags": {"chain_conflict_done": True},
                            "memory_tags": ["chain:conflict:mediate"],
                        },
                    },
                    {
                        "id": "avoid",
                        "attitude": "回避",
                        "effects": {
                            "dorm_mood_delta": -1,
                            "set_flags": {"chain_conflict_done": True},
                            "memory_tags": ["chain:conflict:avoid"],
                        },
                    },
                ],
                "meta": {
                    "injected": True,
                    "kind": "conflict",
                    "weekly_bias": {"escalate": 10, "active": 6, "calm": 4},
                },
            },
            {
                "id": "key_chain_conflict_showdown",
                "type": "key",
                "title": "冲突链：摊牌时刻",
                "priority": 78,
                "cooldown_days": 2,
                "once": False,
                "triggers": {
                    "day_min": 3,
                    "flags_all_true": ["chain_conflict_started"],
                },
                "options": [
                    {
                        "id": "public_break",
                        "attitude": "对抗",
                        "effects": {
                            "dorm_mood_delta": -4,
                            "relation_delta": {
                                "tang_mengqi": {"trust": -12, "tension": 14, "intimacy": -8},
                                "lin_sa": {"trust": -6, "tension": 7, "intimacy": -3},
                            },
                            "stage_transition": {"char": "tang_mengqi", "to": "紧张"},
                            "irreversible": "conflict_public_break",
                            "set_flags": {"chain_conflict_done": True},
                            "clear_flags": ["chain_conflict_started"],
                            "memory_tags": ["chain:conflict:showdown"],
                        },
                    },
                    {
                        "id": "private_talk",
                        "attitude": "中立",
                        "effects": {
                            "dorm_mood_delta": 1,
                            "set_flags": {"chain_conflict_done": True},
                            "clear_flags": ["chain_conflict_started"],
                            "memory_tags": ["chain:conflict:talk"],
                        },
                    },
                    {
                        "id": "temporary_freeze",
                        "attitude": "回避",
                        "effects": {"dorm_mood_delta": -1, "memory_tags": ["chain:conflict:freeze"]},
                    },
                ],
                "meta": {
                    "injected": True,
                    "kind": "conflict",
                    "weekly_bias": {"escalate": 12},
                },
            },
            {
                "id": "key_chain_repair_open",
                "type": "key",
                "title": "修复链：破冰谈话",
                "priority": 64,
                "cooldown_days": 2,
                "once": False,
                "triggers": {
                    "day_min": 2,
                    "weekly_rhythm_any": ["repair", "calm", "progress"],
                    "flags_all_false": ["chain_repair_done"],
                },
                "options": [
                    {
                        "id": "apologize",
                        "attitude": "支持",
                        "effects": {
                            "dorm_mood_delta": 2,
                            "relation_delta": {
                                "lin_sa": {"trust": 6, "tension": -8, "intimacy": 4},
                                "tang_mengqi": {"trust": 3, "tension": -4, "intimacy": 2},
                            },
                            "memory_tags": ["chain:repair:open"],
                            "set_flags": {"chain_repair_opened": True},
                        },
                    },
                    {
                        "id": "neutral_talk",
                        "attitude": "中立",
                        "effects": {"dorm_mood_delta": 1, "memory_tags": ["chain:repair:neutral"]},
                    },
                    {
                        "id": "delay",
                        "attitude": "回避",
                        "effects": {"dorm_mood_delta": -1, "memory_tags": ["chain:repair:delay"]},
                    },
                ],
                "meta": {
                    "injected": True,
                    "kind": "chat",
                    "weekly_bias": {"repair": 10, "calm": 4},
                },
            },
            {
                "id": "key_chain_repair_deepen",
                "type": "key",
                "title": "修复链：关系回暖",
                "priority": 74,
                "cooldown_days": 2,
                "once": False,
                "triggers": {
                    "day_min": 3,
                    "flags_all_true": ["chain_repair_opened"],
                    "relation_stage_any": ["normal", "familiar", "friend", "best_friend"],
                },
                "options": [
                    {
                        "id": "open_up",
                        "attitude": "支持",
                        "effects": {
                            "dorm_mood_delta": 2,
                            "relation_delta": {
                                "lin_sa": {"trust": 8, "tension": -10, "intimacy": 6},
                                "tang_mengqi": {"trust": 4, "tension": -5, "intimacy": 2},
                            },
                            "stage_transition": {"char": "lin_sa", "to": "朋友"},
                            "set_flags": {"chain_repair_done": True},
                            "clear_flags": ["chain_repair_opened"],
                            "memory_tags": ["chain:repair:deepen"],
                        },
                    },
                    {
                        "id": "keep_boundary",
                        "attitude": "中立",
                        "effects": {
                            "dorm_mood_delta": 0,
                            "set_flags": {"chain_repair_done": True},
                            "clear_flags": ["chain_repair_opened"],
                            "memory_tags": ["chain:repair:boundary"],
                        },
                    },
                    {
                        "id": "retreat_again",
                        "attitude": "回避",
                        "effects": {"dorm_mood_delta": -1, "memory_tags": ["chain:repair:retreat"]},
                    },
                ],
                "meta": {
                    "injected": True,
                    "kind": "chat",
                    "weekly_bias": {"repair": 9, "progress": 5},
                },
            },
            {
                "id": "key_chain_romance_hint",
                "type": "key",
                "title": "暧昧链：试探信号",
                "priority": 86,
                "cooldown_days": 2,
                "once": False,
                "triggers": {
                    "day_min": 2,
                    "relation_any": {"intimacy_gte": 30, "trust_gte": 49},
                    "weekly_rhythm_any": ["progress", "active", "repair", "calm"],
                    "flags_all_false": ["chain_romance_done", "irrev:romance_confirmed"],
                },
                "options": [
                    {
                        "id": "invite_walk",
                        "attitude": "支持",
                        "effects": {
                            "dorm_mood_delta": 2,
                            "relation_delta": {
                                "lin_sa": {"trust": 4, "tension": -3, "intimacy": 9},
                            },
                            "set_flags": {"chain_romance_hint": True},
                            "memory_tags": ["chain:romance:hint"],
                        },
                    },
                    {
                        "id": "stay_friends",
                        "attitude": "中立",
                        "effects": {
                            "dorm_mood_delta": 0,
                            "set_flags": {"chain_romance_done": True},
                            "memory_tags": ["chain:romance:friendzone"],
                        },
                    },
                    {
                        "id": "avoid_signal",
                        "attitude": "回避",
                        "effects": {
                            "dorm_mood_delta": -1,
                            "set_flags": {"chain_romance_done": True},
                            "memory_tags": ["chain:romance:avoid"],
                        },
                    },
                ],
                "meta": {
                    "injected": True,
                    "kind": "romance",
                    "weekly_bias": {"progress": 14, "active": 12, "repair": 8, "calm": 6},
                },
            },
            {
                "id": "key_chain_romance_date",
                "type": "key",
                "title": "暧昧链：关系定锚",
                "priority": 90,
                "cooldown_days": 2,
                "once": False,
                "triggers": {
                    "day_min": 3,
                    "flags_all_true": ["chain_romance_hint"],
                    "relation_stage_any": ["normal", "familiar", "friend", "best_friend"],
                    "flags_all_false": ["irrev:romance_confirmed"],
                },
                "options": [
                    {
                        "id": "confess",
                        "attitude": "支持",
                        "effects": {
                            "dorm_mood_delta": 3,
                            "relation_delta": {
                                "lin_sa": {"trust": 7, "tension": -5, "intimacy": 12},
                            },
                            "stage_transition": {"char": "lin_sa", "to": "恋爱"},
                            "irreversible": "romance_confirmed",
                            "set_flags": {"chain_romance_done": True},
                            "clear_flags": ["chain_romance_hint"],
                            "memory_tags": ["chain:romance:confirmed"],
                        },
                    },
                    {
                        "id": "keep_ambiguous",
                        "attitude": "中立",
                        "effects": {
                            "dorm_mood_delta": 1,
                            "set_flags": {"chain_romance_done": True},
                            "clear_flags": ["chain_romance_hint"],
                            "memory_tags": ["chain:romance:ambiguous"],
                        },
                    },
                    {
                        "id": "step_back",
                        "attitude": "回避",
                        "effects": {
                            "dorm_mood_delta": -2,
                            "clear_flags": ["chain_romance_hint"],
                            "memory_tags": ["chain:romance:step_back"],
                        },
                    },
                ],
                "meta": {
                    "injected": True,
                    "kind": "romance",
                    "weekly_bias": {"progress": 18, "active": 10, "calm": 6},
                },
            },
        ]
        for item in baseline_defs:
            if item["id"] not in ids:
                out.append(item)
                ids.add(item["id"])
        return out

    def _default_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "daily_room_smalltalk",
                "type": "daily",
                "title": "寝室闲聊",
                "priority": 55,
                "cooldown_days": 1,
                "triggers": {"day_min": 1},
            },
            {
                "id": "key_daily_room_decision",
                "type": "key",
                "title": "寝室临时决策",
                "priority": 52,
                "cooldown_days": 1,
                "triggers": {"day_min": 1},
                "options": [
                    {
                        "id": "support",
                        "attitude": "支持",
                        "effects": {"dorm_mood_delta": 2},
                    },
                    {
                        "id": "neutral",
                        "attitude": "中立",
                        "effects": {"dorm_mood_delta": 0},
                    },
                    {
                        "id": "avoid",
                        "attitude": "回避",
                        "effects": {"dorm_mood_delta": -2},
                    },
                ],
            },
        ]

    def build_day_plan(self, *, system_state: Dict[str, Any], active_chars: List[str]) -> Dict[str, Any]:
        time_data = system_state.get("time", {}) if isinstance(system_state, dict) else {}
        day = max(1, int((time_data or {}).get("day", 1) or 1))
        week = max(1, int((time_data or {}).get("week", 1) or 1))
        cache = self.runtime.get("daily_plan_cache", {})
        if isinstance(cache, dict) and day in cache:
            return deepcopy(cache[day])

        daily_pool = [e for e in self.definitions if e.get("type") == "daily" and self._is_eligible(e, system_state, active_chars)]
        key_pool = [e for e in self.definitions if e.get("type") == "key" and self._is_eligible(e, system_state, active_chars)]

        flags = system_state.get("flags", {}) if isinstance(system_state, dict) else {}
        run_seed = int((flags or {}).get("run_seed", 0) or 0)
        active_sig = 0
        for name in [str(x).strip() for x in (active_chars or []) if str(x).strip()]:
            active_sig += sum(ord(ch) for ch in name)
        seed = (day * 7919 + week * 131 + active_sig * 17 + run_seed * 19) % 2_147_483_647
        rng = random.Random(seed)
        daily_count = self._pick_daily_count(rng)
        chosen_daily = self._weighted_sample(
            daily_pool,
            min(daily_count, len(daily_pool)),
            rng=rng,
            system_state=system_state,
            active_chars=active_chars,
        )

        chosen_key = None
        key_roll = None
        key_triggered = False
        key_trigger_prob = 0.0
        force_key_offer = False
        if key_pool:
            key_trigger_prob = 0.90
            last_offer_day = int(self.runtime.get("last_key_offer_day", 0) or 0)
            # 防饿死机制：连续 2 天没给关键入口时，第三天强制给一次
            force_key_offer = bool(last_offer_day > 0 and (day - last_offer_day) >= 2)
            key_roll = rng.random()
            if force_key_offer or key_roll <= key_trigger_prob:
                key_triggered = True
                chosen_key = self._weighted_sample(
                    key_pool,
                    1,
                    rng=rng,
                    system_state=system_state,
                    active_chars=active_chars,
                )
                chosen_key = chosen_key[0] if chosen_key else None
                if chosen_key:
                    self.runtime["last_key_offer_day"] = int(day)

        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        plan = {
            "day": day,
            "week": week,
            "generated_at": now,
            "daily_events": [self._compact_event_payload(x, system_state=system_state, active_chars=active_chars) for x in chosen_daily],
            "key_event": self._compact_event_payload(chosen_key, system_state=system_state, active_chars=active_chars) if chosen_key else None,
            "key_event_resolved": bool(self.runtime.get("resolved_key_by_day", {}).get(day)),
            "debug": {
                "daily_pool_size": len(daily_pool),
                "key_pool_size": len(key_pool),
                "daily_count_target": daily_count,
                "daily_selected_count": len(chosen_daily),
                "key_trigger_probability": key_trigger_prob if key_pool else 0.0,
                "key_roll": round(float(key_roll), 4) if isinstance(key_roll, float) else None,
                "key_triggered": key_triggered,
                "force_key_offer": force_key_offer,
            },
        }

        self.runtime["daily_plan_cache"][day] = deepcopy(plan)
        return plan

    def settle_key_choice(
        self,
        *,
        day: int,
        event_id: str,
        attitude: str | None = None,
        choice_id: str | None = None,
    ) -> Dict[str, Any]:
        evt = self._find_event(event_id)
        if not evt:
            return {"ok": False, "error": "event_not_found"}
        if str(evt.get("type")) != "key":
            return {"ok": False, "error": "not_key_event"}

        choice = self._pick_choice(evt, choice_id=choice_id, attitude=attitude)
        if not choice:
            return {"ok": False, "error": "choice_not_found"}

        self.runtime["last_trigger_day"][event_id] = int(day)
        if bool(evt.get("once", False)):
            self.runtime["triggered_once"].add(event_id)
        self.runtime["resolved_key_by_day"][int(day)] = event_id
        cache = self.runtime.get("daily_plan_cache", {})
        if isinstance(cache, dict) and int(day) in cache and isinstance(cache[int(day)], dict):
            cache[int(day)]["key_event"] = None
            cache[int(day)]["key_event_resolved"] = True

        return {
            "ok": True,
            "event_id": event_id,
            "choice_id": str(choice.get("id", "")).strip(),
            "attitude": str(choice.get("attitude", "")).strip(),
            "effects": deepcopy(choice.get("effects", {})) if isinstance(choice.get("effects"), dict) else {},
            "is_irreversible": bool(
                isinstance(choice.get("effects", {}), dict) and bool((choice.get("effects", {}) or {}).get("irreversible"))
            ),
            "has_stage_transition": bool(
                isinstance(choice.get("effects", {}), dict) and bool((choice.get("effects", {}) or {}).get("stage_transition"))
            ),
        }

    def is_key_resolved_for_day(self, day: int) -> bool:
        return bool(self.runtime.get("resolved_key_by_day", {}).get(int(day)))

    def _find_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        target = str(event_id or "").strip()
        if not target:
            return None
        for evt in self.definitions:
            if str(evt.get("id", "")).strip() == target:
                return evt
        return None

    def _pick_choice(self, evt: Dict[str, Any], *, choice_id: Optional[str], attitude: Optional[str]) -> Optional[Dict[str, Any]]:
        options = evt.get("options", [])
        if not isinstance(options, list) or not options:
            return None
        if choice_id:
            cid = str(choice_id).strip().lower()
            for item in options:
                if str((item or {}).get("id", "")).strip().lower() == cid:
                    return item
        if attitude:
            att = str(attitude).strip()
            for item in options:
                if str((item or {}).get("attitude", "")).strip() == att:
                    return item
        return options[0]

    def _compact_event_payload(
        self,
        evt: Optional[Dict[str, Any]],
        *,
        system_state: Optional[Dict[str, Any]] = None,
        active_chars: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(evt, dict):
            return None
        options = evt.get("options", []) if isinstance(evt.get("options"), list) else []
        visible_options = []
        for item in options:
            if not isinstance(item, dict):
                continue
            gate = item.get("info_gate", {}) if isinstance(item.get("info_gate"), dict) else {}
            if gate and not self._check_triggers(gate, system_state or {}, active_chars or []):
                continue
            visible_options.append(item)
        meta = evt.get("meta", {}) if isinstance(evt.get("meta"), dict) else {}
        info_fragments = []
        for frag in meta.get("info_fragments", []) if isinstance(meta.get("info_fragments"), list) else []:
            if not isinstance(frag, dict):
                continue
            gate = frag.get("info_gate", {}) if isinstance(frag.get("info_gate"), dict) else {}
            if gate and not self._check_triggers(gate, system_state or {}, active_chars or []):
                continue
            text = str(frag.get("text", "")).strip()
            if text:
                info_fragments.append(text)
        trigger_debug = self._build_trigger_debug(
            evt.get("triggers", {}) if isinstance(evt.get("triggers"), dict) else {},
            system_state or {},
            active_chars or [],
        )
        return {
            "id": str(evt.get("id", "")).strip(),
            "type": str(evt.get("type", "")).strip(),
            "title": str(evt.get("title", "")).strip(),
            "priority": int(evt.get("priority", 50) or 50),
            "source": "skeleton_injected" if bool(meta.get("injected", False)) else "mod_defined",
            "meta": {
                "kind": str(meta.get("kind", "")).strip(),
                "initiator": str(meta.get("initiator", "")).strip(),
                "npc_proactive": bool(meta.get("npc_proactive", False)),
                "public_line": str(meta.get("public_line", "")).strip(),
                "info_fragments": info_fragments[:2],
            },
            "trigger_debug": trigger_debug,
            "options": [
                {
                    "id": str((item or {}).get("id", "")).strip(),
                    "attitude": str((item or {}).get("attitude", "")).strip(),
                    "is_irreversible": bool(
                        isinstance((item or {}).get("effects", {}), dict)
                        and bool(((item or {}).get("effects", {}) or {}).get("irreversible"))
                    ),
                    "stage_transition": (
                        ((item or {}).get("effects", {}) or {}).get("stage_transition", {})
                        if isinstance((item or {}).get("effects", {}), dict)
                        else {}
                    ),
                }
                for item in visible_options
            ],
        }

    def _build_trigger_debug(self, triggers: Dict[str, Any], system_state: Dict[str, Any], active_chars: List[str]) -> Dict[str, Any]:
        if not isinstance(triggers, dict):
            return {"hit": True, "checks": []}
        checks: List[Dict[str, Any]] = []
        time_data = system_state.get("time", {}) if isinstance(system_state, dict) else {}
        day = int((time_data or {}).get("day", 1) or 1)
        week = int((time_data or {}).get("week", 1) or 1)
        mood = float(system_state.get("dorm_mood", 50) or 50) if isinstance(system_state, dict) else 50.0
        relations = system_state.get("relations", {}) if isinstance(system_state, dict) else {}
        flags = system_state.get("flags", {}) if isinstance(system_state, dict) else {}
        weekly_rhythm = str(((system_state.get("meta", {}) if isinstance(system_state, dict) else {}) or {}).get("weekly_rhythm", "") or "").strip().lower()

        if "day_min" in triggers:
            val = int(triggers.get("day_min"))
            checks.append({"name": "day_min", "expect": val, "actual": day, "hit": day >= val})
        if "day_max" in triggers:
            val = int(triggers.get("day_max"))
            checks.append({"name": "day_max", "expect": val, "actual": day, "hit": day <= val})
        if "week_min" in triggers:
            val = int(triggers.get("week_min"))
            checks.append({"name": "week_min", "expect": val, "actual": week, "hit": week >= val})
        if "week_max" in triggers:
            val = int(triggers.get("week_max"))
            checks.append({"name": "week_max", "expect": val, "actual": week, "hit": week <= val})
        if "dorm_mood_gte" in triggers:
            val = float(triggers.get("dorm_mood_gte"))
            checks.append({"name": "dorm_mood_gte", "expect": val, "actual": round(mood, 2), "hit": mood >= val})
        if "dorm_mood_lte" in triggers:
            val = float(triggers.get("dorm_mood_lte"))
            checks.append({"name": "dorm_mood_lte", "expect": val, "actual": round(mood, 2), "hit": mood <= val})
        if isinstance(triggers.get("active_any"), list):
            expects = [str(x).strip() for x in triggers.get("active_any", []) if str(x).strip()]
            act = {str(x).strip() for x in (active_chars or []) if str(x).strip()}
            checks.append({"name": "active_any", "expect": expects, "actual": sorted(list(act)), "hit": any(x in act for x in expects)})
        if isinstance(triggers.get("flags_all_true"), list):
            expects = [str(x).strip() for x in triggers.get("flags_all_true", []) if str(x).strip()]
            hit = all(bool((flags or {}).get(x, False)) for x in expects)
            checks.append({"name": "flags_all_true", "expect": expects, "actual": {k: bool((flags or {}).get(k, False)) for k in expects}, "hit": hit})
        if isinstance(triggers.get("flags_all_false"), list):
            expects = [str(x).strip() for x in triggers.get("flags_all_false", []) if str(x).strip()]
            hit = all(not bool((flags or {}).get(x, False)) for x in expects)
            checks.append({"name": "flags_all_false", "expect": expects, "actual": {k: bool((flags or {}).get(k, False)) for k in expects}, "hit": hit})
        if isinstance(triggers.get("relation_any"), dict):
            cond = triggers.get("relation_any", {})
            hit = self._match_relation_any(relations if isinstance(relations, dict) else {}, cond)
            checks.append({"name": "relation_any", "expect": cond, "actual": "any_relation", "hit": hit})
        if isinstance(triggers.get("relation_target"), dict):
            cond = triggers.get("relation_target", {})
            hit = self._match_relation_target(relations if isinstance(relations, dict) else {}, cond)
            checks.append({"name": "relation_target", "expect": cond, "actual": "target_relation", "hit": hit})
        if isinstance(triggers.get("relation_stage_any"), list):
            cond = triggers.get("relation_stage_any", [])
            hit = self._match_relation_stage_any(relations if isinstance(relations, dict) else {}, cond)
            checks.append({"name": "relation_stage_any", "expect": cond, "actual": "relation_stage_set", "hit": hit})
        if isinstance(triggers.get("relation_stage_target"), dict):
            cond = triggers.get("relation_stage_target", {})
            hit = self._match_relation_stage_target(relations if isinstance(relations, dict) else {}, cond)
            checks.append({"name": "relation_stage_target", "expect": cond, "actual": "target_relation_stage", "hit": hit})
        if isinstance(triggers.get("weekly_rhythm_any"), list):
            expects = [str(x).strip().lower() for x in triggers.get("weekly_rhythm_any", []) if str(x).strip()]
            checks.append({"name": "weekly_rhythm_any", "expect": expects, "actual": weekly_rhythm, "hit": weekly_rhythm in set(expects)})
        final_hit = all(bool(x.get("hit", False)) for x in checks) if checks else True
        return {"hit": final_hit, "checks": checks[:10]}

    def _pick_daily_count(self, rng: random.Random) -> int:
        # 0: 45%, 1: 35%, 2: 20%
        p = rng.random()
        if p < 0.45:
            return 0
        if p < 0.80:
            return 1
        return 2

    def _weighted_sample(
        self,
        pool: List[Dict[str, Any]],
        k: int,
        *,
        rng: random.Random,
        system_state: Optional[Dict[str, Any]] = None,
        active_chars: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not pool or k <= 0:
            return []
        candidates = list(pool)
        chosen: List[Dict[str, Any]] = []
        while candidates and len(chosen) < k:
            weights = [self._event_weight(item, system_state=system_state, active_chars=active_chars or []) for item in candidates]
            picked = rng.choices(candidates, weights=weights, k=1)[0]
            chosen.append(picked)
            candidates = [x for x in candidates if x is not picked]
        return chosen

    def _event_weight(self, item: Dict[str, Any], *, system_state: Optional[Dict[str, Any]], active_chars: List[str]) -> float:
        base = max(1.0, float(item.get("priority", 50) or 50))
        event_id = str(item.get("id", "")).strip()
        meta = item.get("meta", {}) if isinstance(item.get("meta"), dict) else {}
        if bool(meta.get("npc_proactive", False)):
            base += max(0.0, float(meta.get("npc_proactive_weight", 8) or 8))
        kind = str(meta.get("kind", "")).strip()
        if kind in {"chat", "request", "conflict", "romance"}:
            base += 3.0
        initiator = str(meta.get("initiator", "")).strip()
        if initiator and initiator in {str(x).strip() for x in (active_chars or [])}:
            base += 4.0
        if kind == "conflict" and self._relation_any_hit(system_state or {}, {"tension_gte": 60}):
            base += 10.0
        if kind == "romance" and self._relation_any_hit(system_state or {}, {"intimacy_gte": 32, "trust_gte": 50}):
            base += 14.0
        weekly_rhythm = str(((system_state or {}).get("meta", {}) or {}).get("weekly_rhythm", "") or "").strip().lower()
        if weekly_rhythm:
            weekly_bias = meta.get("weekly_bias", {})
            if isinstance(weekly_bias, dict):
                base += float(weekly_bias.get(weekly_rhythm, 0) or 0)
            elif isinstance(weekly_bias, list):
                normalized = {str(x).strip().lower() for x in weekly_bias if str(x).strip()}
                if weekly_rhythm in normalized:
                    base += 8.0

        stage_bias = meta.get("relation_stage_bias", {})
        if isinstance(stage_bias, dict) and stage_bias:
            rel_map = (system_state or {}).get("relations", {}) if isinstance(system_state, dict) else {}
            if isinstance(rel_map, dict):
                for char_name, stage_val in stage_bias.items():
                    cname = str(char_name).strip()
                    if not cname:
                        continue
                    rel_item = rel_map.get(cname, {})
                    if not isinstance(rel_item, dict):
                        continue
                    stage = self._normalize_stage(str(rel_item.get("stage", "") or ""))
                    if isinstance(stage_val, dict):
                        base += float(stage_val.get(stage, 0) or 0)
                    elif isinstance(stage_val, list):
                        targets = {self._normalize_stage(str(x)) for x in stage_val if str(x).strip()}
                        if stage in targets:
                            base += 6.0
                    elif isinstance(stage_val, str):
                        if stage == self._normalize_stage(stage_val):
                            base += 6.0

        # 链路推进加权：前置旗标已就绪时，优先拉起后续节点，减少“有前置不推进”的体验
        flags = (system_state or {}).get("flags", {}) if isinstance(system_state, dict) else {}
        if isinstance(flags, dict):
            if event_id == "key_chain_conflict_showdown" and bool(flags.get("chain_conflict_started", False)):
                base += 20.0
            if event_id == "key_chain_repair_deepen" and bool(flags.get("chain_repair_opened", False)):
                base += 20.0
            if event_id == "key_chain_romance_date" and bool(flags.get("chain_romance_hint", False)):
                base += 24.0
        return max(1.0, base)

    def _is_eligible(self, evt: Dict[str, Any], system_state: Dict[str, Any], active_chars: List[str]) -> bool:
        event_id = str(evt.get("id", "")).strip()
        if not event_id:
            return False
        day = max(1, int(((system_state.get("time", {}) if isinstance(system_state, dict) else {}) or {}).get("day", 1) or 1))

        if bool(evt.get("once", False)) and event_id in self.runtime.get("triggered_once", set()):
            return False

        last_day = self.runtime.get("last_trigger_day", {}).get(event_id)
        cooldown = max(0, int(evt.get("cooldown_days", 0) or 0))
        if isinstance(last_day, int) and cooldown > 0 and (day - last_day) <= cooldown:
            return False

        triggers = evt.get("triggers", {})
        if not isinstance(triggers, dict):
            return True
        return self._check_triggers(triggers, system_state, active_chars)

    def _check_triggers(self, triggers: Dict[str, Any], system_state: Dict[str, Any], active_chars: List[str]) -> bool:
        time_data = system_state.get("time", {}) if isinstance(system_state, dict) else {}
        relations = system_state.get("relations", {}) if isinstance(system_state, dict) else {}
        dorm_mood = float(system_state.get("dorm_mood", 50) or 50) if isinstance(system_state, dict) else 50.0
        day = max(1, int((time_data or {}).get("day", 1) or 1))
        week = max(1, int((time_data or {}).get("week", 1) or 1))

        day_min = triggers.get("day_min")
        day_max = triggers.get("day_max")
        week_min = triggers.get("week_min")
        week_max = triggers.get("week_max")
        if day_min is not None and day < int(day_min):
            return False
        if day_max is not None and day > int(day_max):
            return False
        if week_min is not None and week < int(week_min):
            return False
        if week_max is not None and week > int(week_max):
            return False

        mood_gte = triggers.get("dorm_mood_gte")
        mood_lte = triggers.get("dorm_mood_lte")
        if mood_gte is not None and dorm_mood < float(mood_gte):
            return False
        if mood_lte is not None and dorm_mood > float(mood_lte):
            return False

        active_any = triggers.get("active_any")
        if isinstance(active_any, list) and active_any:
            names = {str(x).strip() for x in active_chars if str(x).strip()}
            if not any(str(x).strip() in names for x in active_any):
                return False

        relation_any = triggers.get("relation_any")
        if isinstance(relation_any, dict) and relation_any:
            if not self._match_relation_any(relations if isinstance(relations, dict) else {}, relation_any):
                return False
        relation_target = triggers.get("relation_target")
        if isinstance(relation_target, dict) and relation_target:
            if not self._match_relation_target(relations if isinstance(relations, dict) else {}, relation_target):
                return False
        stage_any = triggers.get("relation_stage_any")
        if isinstance(stage_any, list) and stage_any:
            if not self._match_relation_stage_any(relations if isinstance(relations, dict) else {}, stage_any):
                return False
        stage_target = triggers.get("relation_stage_target")
        if isinstance(stage_target, dict) and stage_target:
            if not self._match_relation_stage_target(relations if isinstance(relations, dict) else {}, stage_target):
                return False

        flags = system_state.get("flags", {}) if isinstance(system_state, dict) else {}
        must_true = triggers.get("flags_all_true")
        if isinstance(must_true, list) and must_true:
            for key in must_true:
                if not bool((flags or {}).get(str(key), False)):
                    return False
        must_false = triggers.get("flags_all_false")
        if isinstance(must_false, list) and must_false:
            for key in must_false:
                if bool((flags or {}).get(str(key), False)):
                    return False

        memory_any_tags = triggers.get("memory_any_tags")
        if isinstance(memory_any_tags, list) and memory_any_tags:
            if not self._match_memory_tags(system_state, memory_any_tags, require_all=False):
                return False
        memory_all_tags = triggers.get("memory_all_tags")
        if isinstance(memory_all_tags, list) and memory_all_tags:
            if not self._match_memory_tags(system_state, memory_all_tags, require_all=True):
                return False

        weekly_rhythm_any = triggers.get("weekly_rhythm_any")
        if isinstance(weekly_rhythm_any, list) and weekly_rhythm_any:
            current_rhythm = str(((system_state.get("meta", {}) if isinstance(system_state, dict) else {}) or {}).get("weekly_rhythm", "") or "").strip().lower()
            targets = {str(x).strip().lower() for x in weekly_rhythm_any if str(x).strip()}
            if current_rhythm not in targets:
                return False

        return True

    def _match_relation_any(self, rel_map: Dict[str, Any], cond: Dict[str, Any]) -> bool:
        for _, rel in rel_map.items():
            if not isinstance(rel, dict):
                continue
            trust = float(rel.get("trust", 50) or 50)
            tension = float(rel.get("tension", 50) or 50)
            intimacy = float(rel.get("intimacy", 30) or 30)
            ok = True
            if "trust_gte" in cond and trust < float(cond["trust_gte"]):
                ok = False
            if "trust_lte" in cond and trust > float(cond["trust_lte"]):
                ok = False
            if "tension_gte" in cond and tension < float(cond["tension_gte"]):
                ok = False
            if "tension_lte" in cond and tension > float(cond["tension_lte"]):
                ok = False
            if "intimacy_gte" in cond and intimacy < float(cond["intimacy_gte"]):
                ok = False
            if "intimacy_lte" in cond and intimacy > float(cond["intimacy_lte"]):
                ok = False
            if ok:
                return True
        return False

    def _relation_any_hit(self, system_state: Dict[str, Any], cond: Dict[str, Any]) -> bool:
        rel_map = system_state.get("relations", {}) if isinstance(system_state, dict) else {}
        if not isinstance(rel_map, dict):
            return False
        return self._match_relation_any(rel_map, cond)

    def _match_relation_target(self, rel_map: Dict[str, Any], cond: Dict[str, Any]) -> bool:
        target = str(cond.get("char", "")).strip()
        if not target:
            return False
        rel = rel_map.get(target)
        if not isinstance(rel, dict):
            return False
        trust = float(rel.get("trust", 50) or 50)
        tension = float(rel.get("tension", 50) or 50)
        intimacy = float(rel.get("intimacy", 30) or 30)
        if "trust_gte" in cond and trust < float(cond["trust_gte"]):
            return False
        if "trust_lte" in cond and trust > float(cond["trust_lte"]):
            return False
        if "tension_gte" in cond and tension < float(cond["tension_gte"]):
            return False
        if "tension_lte" in cond and tension > float(cond["tension_lte"]):
            return False
        if "intimacy_gte" in cond and intimacy < float(cond["intimacy_gte"]):
            return False
        if "intimacy_lte" in cond and intimacy > float(cond["intimacy_lte"]):
            return False
        return True

    def _normalize_stage(self, raw: str) -> str:
        text = str(raw or "").strip().lower()
        if not text:
            return ""
        mapping = {
            "普通": "normal",
            "normal": "normal",
            "熟悉": "familiar",
            "familiar": "familiar",
            "朋友": "friend",
            "friend": "friend",
            "挚友": "best_friend",
            "best_friend": "best_friend",
            "恋爱": "romance",
            "romance": "romance",
            "紧张": "tense",
            "tense": "tense",
            "敌对": "hostile",
            "hostile": "hostile",
        }
        return mapping.get(text, text)

    def _match_relation_stage_any(self, rel_map: Dict[str, Any], stages: List[str]) -> bool:
        targets = {self._normalize_stage(str(x)) for x in stages if str(x).strip()}
        if not targets:
            return True
        for rel in (rel_map or {}).values():
            if not isinstance(rel, dict):
                continue
            cur = self._normalize_stage(str(rel.get("stage", "") or ""))
            if cur in targets:
                return True
        return False

    def _match_relation_stage_target(self, rel_map: Dict[str, Any], target_map: Dict[str, Any]) -> bool:
        if not isinstance(target_map, dict) or not target_map:
            return True
        for char_name, expect in target_map.items():
            cname = str(char_name).strip()
            if not cname:
                continue
            rel = rel_map.get(cname)
            if not isinstance(rel, dict):
                return False
            cur = self._normalize_stage(str(rel.get("stage", "") or ""))
            if isinstance(expect, list):
                targets = {self._normalize_stage(str(x)) for x in expect if str(x).strip()}
                if cur not in targets:
                    return False
            else:
                if cur != self._normalize_stage(str(expect)):
                    return False
        return True

    def _match_memory_tags(self, system_state: Dict[str, Any], tags: List[str], *, require_all: bool) -> bool:
        normalized = {str(x).strip() for x in tags if str(x).strip()}
        if not normalized:
            return True
        mem = system_state.get("memory_points", []) if isinstance(system_state, dict) else []
        seen = set()
        if isinstance(mem, list):
            for item in mem:
                if not isinstance(item, dict):
                    continue
                for key in ("type", "event_id", "event_name"):
                    v = str(item.get(key, "")).strip()
                    if v:
                        seen.add(v)
                item_tags = item.get("tags", [])
                if isinstance(item_tags, list):
                    for t in item_tags:
                        tv = str(t).strip()
                        if tv:
                            seen.add(tv)
        if require_all:
            return normalized.issubset(seen)
        return any(t in seen for t in normalized)

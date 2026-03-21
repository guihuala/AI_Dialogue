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
        }

    def reset(self) -> None:
        self.runtime = {
            "last_trigger_day": {},
            "triggered_once": set(),
            "daily_plan_cache": {},
            "resolved_key_by_day": {},
        }

    def reload(self) -> None:
        self.definitions = self._load_definitions(None)
        self.reset()

    def _load_definitions(self, definitions: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if isinstance(definitions, list):
            return self._normalize_definitions(definitions)

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
                    return self._normalize_definitions(items)
            except Exception:
                continue
        return self._normalize_definitions(self._default_definitions())

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
                }
            )
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
                "id": "daily_class_pressure",
                "type": "daily",
                "title": "课程压力",
                "priority": 45,
                "cooldown_days": 2,
                "triggers": {"day_min": 2},
            },
            {
                "id": "key_tension_argument",
                "type": "key",
                "title": "意见冲突",
                "priority": 70,
                "cooldown_days": 3,
                "triggers": {"relation_any": {"tension_gte": 62}},
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
                        "id": "confront",
                        "attitude": "对抗",
                        "effects": {"dorm_mood_delta": -5},
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

        rng = random.Random(day * 7919 + week * 131 + len(active_chars) * 17)
        daily_count = self._pick_daily_count(rng)
        chosen_daily = self._weighted_sample(daily_pool, min(daily_count, len(daily_pool)), rng=rng)

        chosen_key = None
        if key_pool:
            key_trigger_prob = 0.72
            if rng.random() <= key_trigger_prob:
                chosen_key = self._weighted_sample(key_pool, 1, rng=rng)
                chosen_key = chosen_key[0] if chosen_key else None

        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        plan = {
            "day": day,
            "week": week,
            "generated_at": now,
            "daily_events": [self._compact_event_payload(x) for x in chosen_daily],
            "key_event": self._compact_event_payload(chosen_key) if chosen_key else None,
            "key_event_resolved": bool(self.runtime.get("resolved_key_by_day", {}).get(day)),
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

    def _compact_event_payload(self, evt: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(evt, dict):
            return None
        return {
            "id": str(evt.get("id", "")).strip(),
            "type": str(evt.get("type", "")).strip(),
            "title": str(evt.get("title", "")).strip(),
            "priority": int(evt.get("priority", 50) or 50),
            "options": [
                {
                    "id": str((item or {}).get("id", "")).strip(),
                    "attitude": str((item or {}).get("attitude", "")).strip(),
                }
                for item in (evt.get("options", []) if isinstance(evt.get("options"), list) else [])
            ],
        }

    def _pick_daily_count(self, rng: random.Random) -> int:
        # 0: 45%, 1: 35%, 2: 20%
        p = rng.random()
        if p < 0.45:
            return 0
        if p < 0.80:
            return 1
        return 2

    def _weighted_sample(self, pool: List[Dict[str, Any]], k: int, *, rng: random.Random) -> List[Dict[str, Any]]:
        if not pool or k <= 0:
            return []
        candidates = list(pool)
        chosen: List[Dict[str, Any]] = []
        while candidates and len(chosen) < k:
            weights = [max(1.0, float(item.get("priority", 50) or 50)) for item in candidates]
            picked = rng.choices(candidates, weights=weights, k=1)[0]
            chosen.append(picked)
            candidates = [x for x in candidates if x is not picked]
        return chosen

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

        flags = system_state.get("flags", {}) if isinstance(system_state, dict) else {}
        must_true = triggers.get("flags_all_true")
        if isinstance(must_true, list) and must_true:
            for key in must_true:
                if not bool((flags or {}).get(str(key), False)):
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

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List


class SystemStateManager:
    """System-driven runtime state container.

    This manager is intentionally lightweight for P0-1:
    - Unifies time / relation / dorm mood / memory points / flags
    - Keeps compatibility with current event-loop architecture
    """

    def __init__(self):
        self.state: Dict[str, Any] = self._empty_state()

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "time": {
                "day": 1,
                "week": 1,
                "chapter": 1,
                "event_turn": 0,
            },
            "dorm_mood": 50.0,
            "relations": {},
            "memory_points": [],
            "flags": {},
            "meta": {
                "last_updated_at": "",
            },
        }

    def reset(self) -> None:
        self.state = self._empty_state()

    def load(self, payload: Dict[str, Any] | None) -> None:
        base = self._empty_state()
        if isinstance(payload, dict):
            self._deep_merge(base, payload)
        self.state = base
        self._normalize()

    def export(self) -> Dict[str, Any]:
        self._normalize()
        return deepcopy(self.state)

    def set_flag(self, key: str, value: Any) -> None:
        flags = self.state.get("flags", {})
        if not isinstance(flags, dict):
            flags = {}
            self.state["flags"] = flags
        flags[str(key)] = value
        self._touch()

    def get_flag(self, key: str, default: Any = None) -> Any:
        flags = self.state.get("flags", {})
        if not isinstance(flags, dict):
            return default
        return flags.get(str(key), default)

    def bootstrap(self, *, active_chars: List[str], affinity: Dict[str, float], chapter: int, event_turn: int) -> None:
        self._sync_time(chapter=chapter, event_turn=event_turn)
        self._ensure_relations(active_chars, affinity)
        self._touch()

    def update_after_turn(
        self,
        *,
        active_chars: List[str],
        affinity: Dict[str, float],
        chapter: int,
        event_turn: int,
        effects_data: Dict[str, Any] | None,
        event_id: str,
        event_name: str,
        is_end: bool,
    ) -> None:
        effects_data = effects_data if isinstance(effects_data, dict) else {}

        self._sync_time(chapter=chapter, event_turn=event_turn)
        self._ensure_relations(active_chars, affinity)
        self._apply_relation_effects(affinity=affinity, effects_data=effects_data)
        self._apply_dorm_mood_effects(effects_data)

        if is_end:
            self._advance_day()
            self._append_memory_point(
                {
                    "type": "event_end",
                    "event_id": str(event_id or ""),
                    "event_name": str(event_name or ""),
                    "summary": f"事件结束：{event_name or event_id or '未命名事件'}",
                    "effects": {
                        "san_delta": float(effects_data.get("san_delta", 0) or 0),
                        "money_delta": float(effects_data.get("money_delta", 0) or 0),
                        "arg_delta": float(effects_data.get("arg_delta", 0) or 0),
                        "affinity_changes": dict(effects_data.get("affinity_changes", {}) or {}),
                    },
                }
            )
        self._touch()

    def apply_external_effects(self, effects: Dict[str, Any] | None, *, note: str = "") -> None:
        effects = effects if isinstance(effects, dict) else {}
        dorm_delta = float(effects.get("dorm_mood_delta", 0) or 0)
        if dorm_delta:
            self.state["dorm_mood"] = self._clamp(float(self.state.get("dorm_mood", 50) or 50) + dorm_delta, 0, 100)

        rel_delta = effects.get("relation_delta", {})
        if isinstance(rel_delta, dict):
            rel = self.state.get("relations", {})
            if not isinstance(rel, dict):
                rel = {}
                self.state["relations"] = rel
            for name, delta_obj in rel_delta.items():
                cname = str(name).strip()
                if not cname:
                    continue
                item = rel.get(cname)
                if not isinstance(item, dict):
                    item = {"trust": 50.0, "tension": 50.0, "intimacy": 30.0, "stage": "普通"}
                    rel[cname] = item
                if isinstance(delta_obj, dict):
                    trust = float(item.get("trust", 50) or 50) + float(delta_obj.get("trust", 0) or 0)
                    tension = float(item.get("tension", 50) or 50) + float(delta_obj.get("tension", 0) or 0)
                    intimacy = float(item.get("intimacy", 30) or 30) + float(delta_obj.get("intimacy", 0) or 0)
                    item["trust"] = self._clamp(trust, 0, 100)
                    item["tension"] = self._clamp(tension, 0, 100)
                    item["intimacy"] = self._clamp(intimacy, 0, 100)
                    item["stage"] = self._derive_stage((item["trust"] + (100 - item["tension"])) / 2.0)

        if effects:
            self._append_memory_point(
                {
                    "type": "system_effect",
                    "summary": note or "系统结算",
                    "effects": deepcopy(effects),
                }
            )
        self._touch()

    def _sync_time(self, *, chapter: int, event_turn: int) -> None:
        t = self.state.get("time", {})
        if not isinstance(t, dict):
            t = {}
            self.state["time"] = t
        t["chapter"] = max(1, int(chapter or 1))
        t["event_turn"] = max(0, int(event_turn or 0))
        day = max(1, int(t.get("day", 1) or 1))
        t["day"] = day
        t["week"] = max(1, ((day - 1) // 7) + 1)

    def _ensure_relations(self, active_chars: List[str], affinity: Dict[str, float]) -> None:
        rel = self.state.get("relations", {})
        if not isinstance(rel, dict):
            rel = {}
            self.state["relations"] = rel
        for name in [str(x).strip() for x in (active_chars or []) if str(x).strip()]:
            score = self._clamp(float((affinity or {}).get(name, 50) or 50), 0, 100)
            item = rel.get(name)
            if not isinstance(item, dict):
                item = {
                    "trust": score,
                    "tension": self._clamp(100 - score, 0, 100),
                    "intimacy": self._clamp(30 + (score - 50) * 0.25, 0, 100),
                    "stage": self._derive_stage(score),
                }
                rel[name] = item
            else:
                item["trust"] = self._clamp(float(item.get("trust", score) or score), 0, 100)
                item["tension"] = self._clamp(float(item.get("tension", 100 - score) or (100 - score)), 0, 100)
                item["intimacy"] = self._clamp(float(item.get("intimacy", 30) or 30), 0, 100)
                item["stage"] = str(item.get("stage", self._derive_stage(score)) or self._derive_stage(score))

    def _apply_relation_effects(self, *, affinity: Dict[str, float], effects_data: Dict[str, Any]) -> None:
        rel = self.state.get("relations", {})
        if not isinstance(rel, dict):
            return
        aff_changes = effects_data.get("affinity_changes", {})
        if not isinstance(aff_changes, dict):
            aff_changes = {}

        for name, item in rel.items():
            if not isinstance(item, dict):
                continue
            baseline = self._clamp(float((affinity or {}).get(name, item.get("trust", 50)) or 50), 0, 100)
            delta = float(aff_changes.get(name, 0) or 0)
            trust = float(item.get("trust", baseline) or baseline)
            tension = float(item.get("tension", 100 - baseline) or (100 - baseline))
            intimacy = float(item.get("intimacy", 30) or 30)

            trust += delta * 0.8 + (baseline - trust) * 0.10
            tension += -delta * 0.7 + ((100 - baseline) - tension) * 0.10
            intimacy += delta * 0.35

            item["trust"] = self._clamp(trust, 0, 100)
            item["tension"] = self._clamp(tension, 0, 100)
            item["intimacy"] = self._clamp(intimacy, 0, 100)
            item["stage"] = self._derive_stage((item["trust"] + (100 - item["tension"])) / 2.0)

    def _apply_dorm_mood_effects(self, effects_data: Dict[str, Any]) -> None:
        mood = float(self.state.get("dorm_mood", 50.0) or 50.0)
        san_delta = float(effects_data.get("san_delta", 0) or 0)
        arg_delta = float(effects_data.get("arg_delta", 0) or 0)
        aff_changes = effects_data.get("affinity_changes", {})
        mean_aff_delta = 0.0
        if isinstance(aff_changes, dict) and aff_changes:
            vals = []
            for val in aff_changes.values():
                try:
                    vals.append(float(val))
                except Exception:
                    pass
            if vals:
                mean_aff_delta = sum(vals) / len(vals)
        mood += mean_aff_delta * 0.6 + san_delta * 0.05 - arg_delta * 3.0
        self.state["dorm_mood"] = self._clamp(mood, 0, 100)

    def _advance_day(self) -> None:
        t = self.state.get("time", {})
        if not isinstance(t, dict):
            t = {}
            self.state["time"] = t
        day = max(1, int(t.get("day", 1) or 1)) + 1
        t["day"] = day
        t["week"] = max(1, ((day - 1) // 7) + 1)

    def _append_memory_point(self, item: Dict[str, Any]) -> None:
        mem = self.state.get("memory_points", [])
        if not isinstance(mem, list):
            mem = []
            self.state["memory_points"] = mem
        payload = {
            "day": int(self.state.get("time", {}).get("day", 1) or 1),
            "week": int(self.state.get("time", {}).get("week", 1) or 1),
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        payload.update(item or {})
        mem.insert(0, payload)
        self.state["memory_points"] = mem[:40]

    def _normalize(self) -> None:
        if not isinstance(self.state, dict):
            self.state = self._empty_state()
            return
        if not isinstance(self.state.get("time"), dict):
            self.state["time"] = self._empty_state()["time"]
        if not isinstance(self.state.get("relations"), dict):
            self.state["relations"] = {}
        if not isinstance(self.state.get("memory_points"), list):
            self.state["memory_points"] = []
        if not isinstance(self.state.get("flags"), dict):
            self.state["flags"] = {}
        self.state["dorm_mood"] = self._clamp(float(self.state.get("dorm_mood", 50) or 50), 0, 100)
        self._sync_time(
            chapter=int(self.state["time"].get("chapter", 1) or 1),
            event_turn=int(self.state["time"].get("event_turn", 0) or 0),
        )
        self._touch()

    def _touch(self) -> None:
        meta = self.state.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            self.state["meta"] = meta
        meta["last_updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def _deep_merge(self, base: Dict[str, Any], patch: Dict[str, Any]) -> None:
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = deepcopy(value)

    def _derive_stage(self, score: float) -> str:
        if score >= 75:
            return "朋友"
        if score >= 62:
            return "熟悉"
        if score <= 30:
            return "敌对"
        if score <= 42:
            return "紧张"
        return "普通"

    def _clamp(self, v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(v)))

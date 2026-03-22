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
                "pending_weekly_summary": None,
                "week_baseline": {},
                "weekly_rhythm": "calm",
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
        if self.get_flag("run_seed", None) is None:
            # 每局一个随机种子：同一局内可复现，不同开局有差异。
            self.set_flag("run_seed", int(datetime.utcnow().timestamp() * 1_000_000) % 1_000_003)
        self._ensure_week_baseline()
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
        old_week = int(((self.state.get("time", {}) if isinstance(self.state, dict) else {}) or {}).get("week", 1) or 1)

        self._sync_time(chapter=chapter, event_turn=event_turn)
        self._ensure_relations(active_chars, affinity)
        self._apply_relation_effects(affinity=affinity, effects_data=effects_data)
        self._apply_dorm_mood_effects(effects_data)

        if is_end:
            self._advance_day()
            new_week = int(((self.state.get("time", {}) if isinstance(self.state, dict) else {}) or {}).get("week", 1) or 1)
            if new_week > old_week:
                summary = self._build_weekly_summary(old_week)
                if summary:
                    self._apply_weekly_rhythm(summary)
                    self._set_pending_weekly_summary(summary)
                    self._append_memory_point(
                        {
                            "type": "weekly_summary",
                            "summary": f"第{old_week}周总结",
                            "weekly_summary": summary,
                            "tags": [f"weekly:{old_week}", f"weekly_rhythm:{summary.get('weekly_rhythm', '')}"],
                        }
                    )
                self._seed_week_baseline(new_week)
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

        stage_transition_tags: List[str] = []
        stage_transition = effects.get("stage_transition")
        if isinstance(stage_transition, dict):
            rel = self.state.get("relations", {})
            if not isinstance(rel, dict):
                rel = {}
                self.state["relations"] = rel
            # 支持两种结构：
            # 1) {"char":"lin_sa","to":"敌对"}
            # 2) {"lin_sa":"敌对","tang_mengqi":"朋友"}
            if "char" in stage_transition and "to" in stage_transition:
                target = str(stage_transition.get("char", "")).strip()
                target_stage = str(stage_transition.get("to", "")).strip()
                if target and target_stage:
                    item = rel.get(target)
                    if not isinstance(item, dict):
                        item = {"trust": 50.0, "tension": 50.0, "intimacy": 30.0, "stage": "普通"}
                        rel[target] = item
                    item["stage"] = target_stage
                    stage_transition_tags.extend([f"stage:{target}:{target_stage}", f"char:{target}"])
            else:
                for k, v in stage_transition.items():
                    target = str(k).strip()
                    target_stage = str(v).strip()
                    if not target or not target_stage:
                        continue
                    item = rel.get(target)
                    if not isinstance(item, dict):
                        item = {"trust": 50.0, "tension": 50.0, "intimacy": 30.0, "stage": "普通"}
                        rel[target] = item
                    item["stage"] = target_stage
                    stage_transition_tags.extend([f"stage:{target}:{target_stage}", f"char:{target}"])

        irreversible_flag = None
        irreversible = effects.get("irreversible")
        if isinstance(irreversible, str) and irreversible.strip():
            irreversible_flag = irreversible.strip()
        elif isinstance(irreversible, dict):
            irreversible_flag = str(
                irreversible.get("flag")
                or irreversible.get("id")
                or irreversible.get("key")
                or ""
            ).strip()
        elif bool(irreversible):
            irreversible_flag = str(effects.get("irreversible_flag", "")).strip() or "system_irreversible_choice"
        if irreversible_flag:
            self.set_flag(f"irrev:{irreversible_flag}", True)
            stage_transition_tags.append(f"irrev:{irreversible_flag}")

        set_flags = effects.get("set_flags")
        if isinstance(set_flags, dict):
            for k, v in set_flags.items():
                key = str(k).strip()
                if not key:
                    continue
                self.set_flag(key, bool(v))
                stage_transition_tags.append(f"flag:{key}:{'1' if bool(v) else '0'}")

        clear_flags = effects.get("clear_flags")
        if isinstance(clear_flags, list):
            for k in clear_flags:
                key = str(k).strip()
                if not key:
                    continue
                self.set_flag(key, False)
                stage_transition_tags.append(f"flag:{key}:0")

        memory_tags = effects.get("memory_tags")
        if isinstance(memory_tags, list):
            for t in memory_tags:
                tag = str(t).strip()
                if tag:
                    stage_transition_tags.append(tag)

        if effects:
            self._append_memory_point(
                {
                    "type": "system_effect",
                    "summary": note or "系统结算",
                    "effects": deepcopy(effects),
                    "tags": stage_transition_tags[:10],
                }
            )
        self._touch()

    def consume_weekly_summary(self) -> Dict[str, Any] | None:
        meta = self.state.get("meta", {})
        if not isinstance(meta, dict):
            return None
        payload = meta.get("pending_weekly_summary")
        if not isinstance(payload, dict):
            return None
        meta["pending_weekly_summary"] = None
        self._touch()
        return deepcopy(payload)

    def _set_pending_weekly_summary(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict) or not payload:
            return
        meta = self.state.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            self.state["meta"] = meta
        meta["pending_weekly_summary"] = deepcopy(payload)

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
        self._ensure_week_baseline()
        self._touch()

    def _touch(self) -> None:
        meta = self.state.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            self.state["meta"] = meta
        if "pending_weekly_summary" not in meta:
            meta["pending_weekly_summary"] = None
        if "week_baseline" not in meta or not isinstance(meta.get("week_baseline"), dict):
            meta["week_baseline"] = {}
        if "weekly_rhythm" not in meta:
            meta["weekly_rhythm"] = "calm"
        meta["last_updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def _ensure_week_baseline(self) -> None:
        meta = self.state.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            self.state["meta"] = meta
        week = int((self.state.get("time", {}) or {}).get("week", 1) or 1)
        baseline = meta.get("week_baseline")
        if not isinstance(baseline, dict) or int(baseline.get("week", 0) or 0) != week:
            self._seed_week_baseline(week)

    def _seed_week_baseline(self, week: int) -> None:
        meta = self.state.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            self.state["meta"] = meta
        meta["week_baseline"] = {
            "week": int(week),
            "dorm_mood": float(self.state.get("dorm_mood", 50) or 50),
            "relations": deepcopy(self.state.get("relations", {})) if isinstance(self.state.get("relations"), dict) else {},
        }

    def _build_weekly_summary(self, week: int) -> Dict[str, Any]:
        if week <= 0:
            return {}
        meta = self.state.get("meta", {})
        baseline = meta.get("week_baseline", {}) if isinstance(meta, dict) else {}
        baseline_rel = baseline.get("relations", {}) if isinstance(baseline, dict) else {}
        if not isinstance(baseline_rel, dict):
            baseline_rel = {}
        baseline_mood = float((baseline or {}).get("dorm_mood", self.state.get("dorm_mood", 50)) or self.state.get("dorm_mood", 50))

        rel_now = self.state.get("relations", {})
        if not isinstance(rel_now, dict):
            rel_now = {}

        relation_changes: List[Dict[str, Any]] = []
        for name, now_item in rel_now.items():
            if not isinstance(now_item, dict):
                continue
            old_item = baseline_rel.get(name, {}) if isinstance(baseline_rel.get(name), dict) else {}
            trust_old = float(old_item.get("trust", now_item.get("trust", 50)) or now_item.get("trust", 50) or 50)
            tension_old = float(old_item.get("tension", now_item.get("tension", 50)) or now_item.get("tension", 50) or 50)
            intimacy_old = float(old_item.get("intimacy", now_item.get("intimacy", 30)) or now_item.get("intimacy", 30) or 30)
            stage_old = str(old_item.get("stage", now_item.get("stage", "普通")) or now_item.get("stage", "普通"))

            trust_new = float(now_item.get("trust", 50) or 50)
            tension_new = float(now_item.get("tension", 50) or 50)
            intimacy_new = float(now_item.get("intimacy", 30) or 30)
            stage_new = str(now_item.get("stage", "普通") or "普通")

            relation_changes.append(
                {
                    "name": str(name),
                    "trust_delta": round(trust_new - trust_old, 2),
                    "tension_delta": round(tension_new - tension_old, 2),
                    "intimacy_delta": round(intimacy_new - intimacy_old, 2),
                    "stage_from": stage_old,
                    "stage_to": stage_new,
                }
            )

        relation_changes.sort(key=lambda x: abs(float(x.get("trust_delta", 0))) + abs(float(x.get("tension_delta", 0))), reverse=True)

        mem = self.state.get("memory_points", [])
        if not isinstance(mem, list):
            mem = []
        key_events: List[Dict[str, Any]] = []
        for item in mem:
            if not isinstance(item, dict):
                continue
            if int(item.get("week", 0) or 0) != int(week):
                continue
            if str(item.get("type", "")) not in {"system_effect", "event_end"}:
                continue
            effects = item.get("effects", {}) if isinstance(item.get("effects"), dict) else {}
            has_key_signal = (
                "关键事件" in str(item.get("summary", "") or "")
                or bool(effects.get("irreversible"))
                or bool(effects.get("stage_transition"))
            )
            if not has_key_signal:
                continue
            key_events.append(
                {
                    "summary": str(item.get("summary", "") or "").strip(),
                    "event_id": str(item.get("event_id", "") or "").strip(),
                    "tags": list(item.get("tags", [])) if isinstance(item.get("tags"), list) else [],
                }
            )
        key_events = key_events[:6]

        mood_now = float(self.state.get("dorm_mood", 50) or 50)
        mood_delta = round(mood_now - baseline_mood, 2)
        mood_trend = "上升" if mood_delta > 1 else ("下降" if mood_delta < -1 else "平稳")

        highlights: List[str] = []
        stage_jumps = [x for x in relation_changes if str(x.get("stage_from")) != str(x.get("stage_to"))]
        if stage_jumps:
            first = stage_jumps[0]
            highlights.append(f"{first.get('name')} 关系阶段：{first.get('stage_from')} -> {first.get('stage_to')}")
        if relation_changes:
            top = relation_changes[0]
            if abs(float(top.get("trust_delta", 0))) >= 1.0:
                sign = "+" if float(top.get("trust_delta", 0)) >= 0 else ""
                highlights.append(f"{top.get('name')} 信任变化 {sign}{top.get('trust_delta')}")
        if key_events:
            highlights.append(f"本周关键事件 {len(key_events)} 条")
        if not highlights:
            highlights.append("本周整体平稳推进。")

        weekly_rhythm = self._derive_weekly_rhythm(
            mood_delta=mood_delta,
            relation_changes=relation_changes,
            key_events=key_events,
        )

        return {
            "week": int(week),
            "title": f"第{int(week)}周总结",
            "dorm_mood": {
                "from": round(baseline_mood, 2),
                "to": round(mood_now, 2),
                "delta": mood_delta,
                "trend": mood_trend,
            },
            "relation_changes": relation_changes[:6],
            "key_events": key_events,
            "highlights": highlights[:4],
            "weekly_rhythm": weekly_rhythm,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }

    def _derive_weekly_rhythm(
        self,
        *,
        mood_delta: float,
        relation_changes: List[Dict[str, Any]],
        key_events: List[Dict[str, Any]],
    ) -> str:
        has_stage_jump = any(str(x.get("stage_from", "")) != str(x.get("stage_to", "")) for x in relation_changes or [])
        avg_trust = 0.0
        avg_tension = 0.0
        if relation_changes:
            avg_trust = sum(float(x.get("trust_delta", 0) or 0) for x in relation_changes) / len(relation_changes)
            avg_tension = sum(float(x.get("tension_delta", 0) or 0) for x in relation_changes) / len(relation_changes)

        if avg_tension >= 2.5 or mood_delta <= -4 or has_stage_jump and avg_tension > 0:
            return "escalate"
        if avg_trust >= 2.5 or mood_delta >= 4:
            return "progress"
        if avg_trust > 0 and avg_tension < 0:
            return "repair"
        if key_events and any("关键事件" in str(x.get("summary", "")) for x in key_events):
            return "active"
        return "calm"

    def _apply_weekly_rhythm(self, summary: Dict[str, Any]) -> None:
        if not isinstance(summary, dict):
            return
        rhythm = str(summary.get("weekly_rhythm", "") or "").strip().lower()
        if not rhythm:
            return
        meta = self.state.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            self.state["meta"] = meta
        meta["weekly_rhythm"] = rhythm
        self.set_flag("weekly_rhythm", rhythm)
        week = int(summary.get("week", 0) or 0)
        if week > 0:
            self.set_flag(f"weekly_rhythm:{week}", rhythm)

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

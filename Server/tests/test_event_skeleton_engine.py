import unittest

from src.core.event_skeleton_engine import EventSkeletonEngine


class EventSkeletonEngineTests(unittest.TestCase):
    def setUp(self):
        self.defs = [
            {
                "id": "daily_chat",
                "type": "daily",
                "title": "寝室闲聊",
                "priority": 60,
                "cooldown_days": 0,
                "triggers": {"day_min": 1},
            },
            {
                "id": "daily_study",
                "type": "daily",
                "title": "自习互助",
                "priority": 50,
                "cooldown_days": 0,
                "triggers": {"day_min": 1},
            },
            {
                "id": "key_conflict",
                "type": "key",
                "title": "意见冲突",
                "priority": 90,
                "cooldown_days": 2,
                "triggers": {"relation_any": {"tension_gte": 60}},
                "options": [
                    {"id": "support", "attitude": "支持", "effects": {"dorm_mood_delta": 2}},
                    {"id": "neutral", "attitude": "中立", "effects": {"dorm_mood_delta": 0}},
                    {"id": "confront", "attitude": "对抗", "effects": {"dorm_mood_delta": -5}},
                ],
            },
            {
                "id": "key_info_gate",
                "type": "key",
                "title": "信息门槛事件",
                "priority": 80,
                "cooldown_days": 0,
                "triggers": {"day_min": 1},
                "options": [
                    {"id": "safe", "attitude": "稳妥", "effects": {"dorm_mood_delta": 0}},
                    {"id": "hidden", "attitude": "追问细节", "effects": {"dorm_mood_delta": 1}, "info_gate": {"flags_all_true": ["know_secret"]}},
                    {
                        "id": "break",
                        "attitude": "公开对质",
                        "effects": {
                            "dorm_mood_delta": -2,
                            "stage_transition": {"char": "林飒", "to": "紧张"},
                            "irreversible": "public_break_test",
                        },
                    },
                ],
                "meta": {
                    "kind": "conflict",
                    "initiator": "林飒",
                    "info_fragments": [
                        {"text": "公共线索", "info_gate": {"day_min": 1}},
                        {"text": "隐蔽线索", "info_gate": {"flags_all_true": ["know_secret"]}},
                    ],
                },
            },
        ]
        self.engine = EventSkeletonEngine(user_id="default", definitions=self.defs)

    def _state(self, *, day=1, week=1, tension=50):
        return {
            "time": {"day": day, "week": week, "chapter": 1, "event_turn": 0},
            "dorm_mood": 50,
            "relations": {
                "林飒": {"trust": 50, "tension": tension, "intimacy": 30, "stage": "普通"},
            },
            "flags": {},
        }

    def test_build_day_plan_limits_counts(self):
        plan = self.engine.build_day_plan(system_state=self._state(day=3, tension=70), active_chars=["林飒"])
        self.assertIn("daily_events", plan)
        self.assertLessEqual(len(plan["daily_events"]), 2)
        self.assertTrue(plan.get("key_event") is None or isinstance(plan.get("key_event"), dict))

    def test_trigger_by_relation_tension(self):
        low = self.engine.build_day_plan(system_state=self._state(day=2, tension=40), active_chars=["林飒"])
        high = self.engine.build_day_plan(system_state=self._state(day=5, tension=75), active_chars=["林飒"])
        self.assertTrue(low.get("key_event") is None or low["key_event"]["id"] != "key_conflict")
        # high day may still miss key due probability. if key_conflict appears, it must be eligible.
        if high.get("key_event"):
            allowed_ids = {"key_conflict", "key_daily_room_decision", "key_asymmetry_rumor"}
            self.assertIn(high["key_event"]["id"], allowed_ids)

    def test_settle_key_choice(self):
        _ = self.engine.build_day_plan(system_state=self._state(day=7, tension=70), active_chars=["林飒"])
        result = self.engine.settle_key_choice(day=7, event_id="key_conflict", choice_id="confront")
        self.assertTrue(result["ok"])
        self.assertEqual(result["choice_id"], "confront")
        self.assertEqual(result["effects"]["dorm_mood_delta"], -5)
        self.assertTrue(self.engine.is_key_resolved_for_day(7))
        refreshed = self.engine.build_day_plan(system_state=self._state(day=7, tension=70), active_chars=["林飒"])
        self.assertTrue(refreshed.get("key_event_resolved"))

    def test_settle_flags_for_irreversible_and_stage_transition(self):
        result = self.engine.settle_key_choice(day=3, event_id="key_info_gate", choice_id="break")
        self.assertTrue(result["ok"])
        self.assertTrue(result.get("is_irreversible"))
        self.assertTrue(result.get("has_stage_transition"))

    def test_info_gate_filters_options_and_fragments(self):
        event = next((x for x in self.engine.definitions if x.get("id") == "key_info_gate"), None)
        self.assertIsNotNone(event)

        state_without_flag = self._state(day=3, tension=65)
        compact_without = self.engine._compact_event_payload(event, system_state=state_without_flag, active_chars=["林飒"])
        option_ids_without = [x.get("id") for x in compact_without.get("options", [])]
        self.assertIn("safe", option_ids_without)
        self.assertNotIn("hidden", option_ids_without)
        self.assertIn("公共线索", compact_without.get("meta", {}).get("info_fragments", []))
        self.assertNotIn("隐蔽线索", compact_without.get("meta", {}).get("info_fragments", []))

        state_with_flag = self._state(day=3, tension=65)
        state_with_flag["flags"] = {"know_secret": True}
        compact_with = self.engine._compact_event_payload(event, system_state=state_with_flag, active_chars=["林飒"])
        option_ids_with = [x.get("id") for x in compact_with.get("options", [])]
        self.assertIn("hidden", option_ids_with)
        self.assertIn("隐蔽线索", compact_with.get("meta", {}).get("info_fragments", []))
        break_opt = next((x for x in compact_with.get("options", []) if x.get("id") == "break"), None)
        self.assertIsNotNone(break_opt)
        self.assertTrue(break_opt.get("is_irreversible"))
        self.assertEqual((break_opt.get("stage_transition") or {}).get("to"), "紧张")


if __name__ == "__main__":
    unittest.main()

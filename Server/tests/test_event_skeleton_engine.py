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
        # high day may still miss key due probability, but if key appears it must be eligible
        if high.get("key_event"):
            self.assertEqual(high["key_event"]["id"], "key_conflict")

    def test_settle_key_choice(self):
        _ = self.engine.build_day_plan(system_state=self._state(day=7, tension=70), active_chars=["林飒"])
        result = self.engine.settle_key_choice(day=7, event_id="key_conflict", choice_id="confront")
        self.assertTrue(result["ok"])
        self.assertEqual(result["choice_id"], "confront")
        self.assertEqual(result["effects"]["dorm_mood_delta"], -5)
        self.assertTrue(self.engine.is_key_resolved_for_day(7))
        refreshed = self.engine.build_day_plan(system_state=self._state(day=7, tension=70), active_chars=["林飒"])
        self.assertTrue(refreshed.get("key_event_resolved"))


if __name__ == "__main__":
    unittest.main()

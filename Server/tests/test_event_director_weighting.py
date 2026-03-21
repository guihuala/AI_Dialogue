import unittest

from src.core.event_director import EventDirector


class DummyEvent:
    def __init__(self, event_weight=1.0, tags=None):
        self.event_weight = event_weight
        self.narrative_tags = tags or []
        self.id = "evt_template"
        self.name = "与[TARGET]爆发冲突"
        self.description = "[TARGET]在宿舍里突然翻旧账"
        self.opening_goal = "让[TARGET]先开口挑刺"
        self.pressure_goal = ""
        self.turning_goal = ""
        self.settlement_goal = ""
        self.fallback_consequence = ""
        self.exclusive_char = ""
        self.potential_conflicts = ["[TARGET]指责主角不守规矩"]
        self.progress_beats = []
        self.end_signals = []
        self.options = {"A": "和[TARGET]正面冲突"}
        self.outcomes = {"A": "[TARGET]情绪升级"}
        self.fixed_dialogue = [
            {"speaker": "[TARGET]", "content": "[TARGET]冷冷看着你。"}
        ]
        self.progress_beats = ["[[TARGET]]突然沉默了几秒。"]
        self.allow_repeat = False


class EventDirectorWeightingTests(unittest.TestCase):
    def setUp(self):
        # 只测试纯函数行为，避免触发完整初始化依赖
        self.director = EventDirector.__new__(EventDirector)

    def test_base_weight_without_state(self):
        event = DummyEvent(event_weight=1.2, tags=["关系-恶化"])
        weight = self.director._event_weight(event, None)
        self.assertAlmostEqual(weight, 1.2)

    def test_conflict_tag_boosted_by_relation_state(self):
        event = DummyEvent(event_weight=1.0, tags=["关系-恶化", "公开冲突"])
        narrative_state = {
            "room_tension": "普通",
            "player_arc": [],
            "active_threads": [],
            "relationship_state": {
                "林飒": {"trust": 20, "tension": 88, "intimacy": 15, "relationship_stage": "敌对"}
            },
            "long_term_milestones": [],
        }
        weight = self.director._event_weight(event, narrative_state)
        self.assertGreater(weight, 1.2)

    def test_warm_tag_boosted_by_relation_state(self):
        event = DummyEvent(event_weight=1.0, tags=["关系-升温", "和解"])
        narrative_state = {
            "room_tension": "平稳",
            "player_arc": [],
            "active_threads": [],
            "relationship_state": {
                "唐梦琪": {"trust": 82, "tension": 24, "intimacy": 68, "relationship_stage": "暧昧"}
            },
            "long_term_milestones": [],
        }
        weight = self.director._event_weight(event, narrative_state)
        self.assertGreater(weight, 1.2)

    def test_recent_stage_shift_boosts_relation_tags(self):
        event = DummyEvent(event_weight=1.0, tags=["关系-和解"])
        narrative_state = {
            "room_tension": "",
            "player_arc": [],
            "active_threads": [],
            "relationship_state": {
                "陈雨婷": {"trust": 62, "tension": 42, "intimacy": 40, "relationship_stage": "朋友"}
            },
            "long_term_milestones": [
                "陈雨婷 与 陆陈安然 关系阶段变化：紧张 -> 朋友（evt_x）"
            ],
        }
        weight = self.director._event_weight(event, narrative_state)
        self.assertGreater(weight, 1.1)

    def test_update_relationship_feedback_window_from_milestone(self):
        self.director.relationship_feedback_window = 0
        self.director.relationship_feedback_tags = []
        self.director._seen_relation_shift_markers = set()
        narrative_state = {
            "long_term_milestones": [
                "林飒 与 陆陈安然 关系阶段变化：紧张 -> 朋友（evt_demo）"
            ]
        }
        self.director._update_relationship_feedback_window(narrative_state)
        self.assertEqual(self.director.relationship_feedback_window, 3)
        self.assertTrue("关系-升温" in self.director.relationship_feedback_tags)

    def test_event_matches_relation_feedback(self):
        event = DummyEvent(tags=["关系-恶化", "宿舍矛盾"])
        self.assertTrue(self.director._event_matches_relation_feedback(event, ["关系-恶化"]))
        self.assertFalse(self.director._event_matches_relation_feedback(event, ["暧昧推进"]))

    def test_materialize_template_event_with_relation_target(self):
        event = DummyEvent(tags=["关系-恶化"])
        narrative_state = {
            "relationship_state": {
                "林飒": {"trust": 18, "tension": 90, "intimacy": 8, "relationship_stage": "敌对"},
                "唐梦琪": {"trust": 65, "tension": 35, "intimacy": 45, "relationship_stage": "朋友"},
            }
        }
        materialized = self.director._materialize_template_event(
            event,
            active_chars=["林飒", "唐梦琪"],
            affinity={"林飒": 22, "唐梦琪": 66},
            narrative_state=narrative_state,
        )
        self.assertIn("__tgt_", materialized.id)
        self.assertIn("林飒", materialized.name)
        self.assertEqual(materialized.exclusive_char, "林飒")
        self.assertIn("林飒", materialized.options["A"])
        self.assertEqual(materialized.fixed_dialogue[0]["speaker"], "林飒")
        self.assertIn("林飒", materialized.fixed_dialogue[0]["content"])
        self.assertIn("林飒", materialized.progress_beats[0])


if __name__ == "__main__":
    unittest.main()

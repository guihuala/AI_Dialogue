import unittest

from src.core.narrative_state_manager import NarrativeStateManager


class DummyEvent:
    def __init__(self, event_id: str, name: str, description: str = ""):
        self.id = event_id
        self.name = name
        self.description = description


class NarrativeStateManagerTests(unittest.TestCase):
    def setUp(self):
        self.mgr = NarrativeStateManager()
        self.player = "陆陈安然"
        self.char = "林飒"
        self.event = DummyEvent("evt_test", "宿舍夜谈", "一次容易引发误解的深夜对话")

    def _update(self, *, action_text: str, affinity: float, affinity_delta: float, is_end: bool = False):
        self.mgr.update_after_turn(
            player_name=self.player,
            event_obj=self.event,
            action_text=action_text,
            san=72,
            affinity={self.char: affinity, self.player: 50},
            active_chars=[self.char, self.player],
            effects_data={
                "san_delta": 0,
                "money_delta": 0,
                "arg_delta": 0,
                "affinity_changes": {self.char: affinity_delta},
            },
            dialogue_sequence=[{"speaker": self.char, "content": "我们把话说开吧。"}],
            is_end=is_end,
        )

    def test_relationship_state_fields_exist(self):
        self._update(action_text="先缓和一下", affinity=60, affinity_delta=2)
        state = self.mgr.export()
        rel = state["relationship_state"].get(self.char)
        self.assertIsInstance(rel, dict)
        for key in ["trust", "tension", "intimacy", "relationship_stage", "recent_flags", "last_milestone_at"]:
            self.assertIn(key, rel)

    def test_stage_does_not_jump_on_small_delta(self):
        self._update(action_text="先观察", affinity=55, affinity_delta=1)
        stage_1 = self.mgr.export()["relationship_state"][self.char]["relationship_stage"]
        self._update(action_text="先观察", affinity=56, affinity_delta=-1)
        stage_2 = self.mgr.export()["relationship_state"][self.char]["relationship_stage"]
        self.assertEqual(stage_1, stage_2)

    def test_milestone_generated_on_stage_change(self):
        # 先建立基线
        self._update(action_text="先观察", affinity=50, affinity_delta=0)
        # 持续升温，促使阶段变化
        for _ in range(6):
            self._update(action_text="安慰并维护她", affinity=80, affinity_delta=6)
        milestones = self.mgr.export()["long_term_milestones"]
        self.assertTrue(any("关系阶段变化" in item for item in milestones))

    def test_consume_new_milestones_once(self):
        self._update(action_text="先观察", affinity=50, affinity_delta=0)
        for _ in range(6):
            self._update(action_text="安慰并维护她", affinity=82, affinity_delta=6)
        first = self.mgr.consume_new_milestones()
        second = self.mgr.consume_new_milestones()
        self.assertTrue(len(first) >= 1)
        self.assertEqual(second, [])

    def test_force_stage_update_when_scores_already_extreme(self):
        self.mgr.load({
            "relationship_state": {
                self.char: {
                    "trust": 24.0,
                    "tension": 90.0,
                    "intimacy": 10.0,
                    "relationship_stage": "熟悉",
                    "recent_flags": [],
                    "last_milestone_at": "",
                }
            }
        })
        self._update(action_text="先观察", affinity=24, affinity_delta=0)
        rel = self.mgr.export()["relationship_state"][self.char]
        self.assertIn(rel["relationship_stage"], ["紧张", "敌对"])


if __name__ == "__main__":
    unittest.main()

import unittest

from src.core.system_state_manager import SystemStateManager


class SystemStateManagerTests(unittest.TestCase):
    def setUp(self):
        self.mgr = SystemStateManager()

    def test_bootstrap_initializes_time_and_relations(self):
        self.mgr.bootstrap(
            active_chars=["林飒", "唐梦琪"],
            affinity={"林飒": 62, "唐梦琪": 48},
            chapter=1,
            event_turn=0,
        )
        state = self.mgr.export()
        self.assertEqual(state["time"]["chapter"], 1)
        self.assertEqual(state["time"]["event_turn"], 0)
        self.assertIn("林飒", state["relations"])
        self.assertIn("唐梦琪", state["relations"])

    def test_update_after_turn_applies_effects_and_day_advance(self):
        self.mgr.bootstrap(
            active_chars=["林飒"],
            affinity={"林飒": 50},
            chapter=1,
            event_turn=0,
        )
        day_before = self.mgr.export()["time"]["day"]
        self.mgr.update_after_turn(
            active_chars=["林飒"],
            affinity={"林飒": 55},
            chapter=1,
            event_turn=1,
            effects_data={
                "san_delta": -2,
                "arg_delta": 1,
                "affinity_changes": {"林飒": 6},
            },
            event_id="evt_demo",
            event_name="夜谈",
            is_end=True,
        )
        state = self.mgr.export()
        self.assertGreaterEqual(state["relations"]["林飒"]["trust"], 50)
        self.assertEqual(state["time"]["day"], day_before + 1)
        self.assertGreaterEqual(len(state["memory_points"]), 1)

    def test_load_normalizes_broken_payload(self):
        self.mgr.load({"relations": [], "time": None, "dorm_mood": 999})
        state = self.mgr.export()
        self.assertIsInstance(state["relations"], dict)
        self.assertIsInstance(state["time"], dict)
        self.assertLessEqual(state["dorm_mood"], 100)


if __name__ == "__main__":
    unittest.main()


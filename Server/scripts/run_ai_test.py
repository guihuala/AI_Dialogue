import sys
import os
import json
import time

# Add Server/src to path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(base_dir))

from src.core.game_engine import GameEngine

def run_simulation(max_total_turns=150, use_mock=False):
    """
    Automated Playthrough Test Script.
    Runs the game logic by calling the real LLM (or mock) and verifies ending reachability.
    """
    print(f"🚀 Starting Game Logic Verification (Full Playthrough Test - {'MOCK' if use_mock else 'REAL LLM'})")
    engine = GameEngine()
    
    # Optional Mocking
    if use_mock:
        from unittest.mock import MagicMock, AsyncMock
        engine.llm.generate_response = MagicMock(side_effect=lambda **kwargs: json.dumps({
            "narrator_transition": "顺利推进中...",
            "current_scene": "宿舍",
            "dialogue_sequence": [{"speaker": "室友", "content": "（模拟对话：好的，我们走吧。）", "mood": "happy"}],
            "npc_background_actions": [],
            "wechat_notifications": [],
            "next_options": ["【选项 A】", "【选项 B】"],
            "stat_changes": {"san_delta": 0, "money_delta": 50},
            "is_end": True
        }))
        engine.llm.async_generate_response = AsyncMock(side_effect=lambda **kwargs: json.dumps({
            "mood": "平静", "action": "点点头", "dialogue": "挺好的。", "wechat_message": ""
        }))

    # Initial state
    state = {
        "choice": "",
        "active_roommates": ["唐梦琪", "林飒", "李一诺"],
        "current_evt_id": "",
        "is_transition": True,
        "chapter": 1,
        "turn": 0,
        "san": 100,
        "money": 2000,
        "gpa": 4.0,
        "hygiene": 100,
        "reputation": 100,
        "arg_count": 0,
        "affinity": {"唐梦琪": 50, "林飒": 50, "李一诺": 50},
        "wechat_data_dict": {}
    }

    report_log = []
    full_story_log = []
    current_chapter = 1
    total_events = 0
    total_api_calls = 0
    start_time = time.time()

    def save_partial_report(current_idx):
        path = os.path.join(base_dir, "data", "test_report.md")
        with open(path, 'w', encoding='utf-8') as f:
            f.write("# 游戏全流程生成测试报告 (真实大模型校验)\n\n")
            f.write(f"- **实时进度**: 回合 {current_idx+1}\n")
            f.write(f"- **累计调用**: {total_api_calls} 次\n")
            f.write(f"- **已过事件**: {total_events} 个\n")
            f.write(f"- **当前学年**: 大{state['chapter']}\n\n")
            f.write("## 运行摘要\n")
            for line in report_log:
                f.write(f"- {line}\n")
            f.write("\n---\n## AI 内容采样\n")
            for entry in full_story_log:
                if entry["turn"] == 1:
                    f.write(f"### 🚩 大{entry['chapter']} - {entry['event']}\n")
                    f.write(f"```text\n{entry['content']}\n```\n")

    print("\n--- Playthrough in Progress ---\n")
    
    for i in range(max_total_turns):
        t_start = time.time()
        res = engine.play_main_turn(
            action_text=state["choice"],
            selected_chars=state["active_roommates"],
            current_evt_id=state["current_evt_id"],
            is_transition=state["is_transition"],
            api_key="", base_url="", model="", 
            tmp=0.7, top_p=1.0, max_t=800, pres_p=0.3, freq_p=0.5,
            san=state["san"], money=state["money"], gpa=state["gpa"], 
            hygiene=state["hygiene"], reputation=state["reputation"],
            arg_count=state["arg_count"], chapter=state["chapter"], 
            turn=state["turn"], affinity=state["affinity"], 
            wechat_data_dict=state["wechat_data_dict"]
        )
        total_api_calls += 1
        gen_time = time.time() - t_start

        if "error" in res and res["error"]:
            print(f"❌ Error: {res['error']}")
            break

        # Dialogue capture
        dialogues = [f"[{l.get('speaker')}] {l.get('content')}" for l in res.get("dialogue_sequence", []) if isinstance(l, dict)]
        full_story_log.append({
            "chapter": state["chapter"],
            "event": res.get("current_evt_id"),
            "turn": res.get("turn"),
            "content": "\n".join(dialogues)
        })

        if res.get("is_game_over"):
            report_log.append("🎓 成功毕业！")
            save_partial_report(i)
            break

        if res["chapter"] > current_chapter:
            report_log.append(f"📈 升入大{res['chapter']}")
            current_chapter = res["chapter"]

        if res["is_end"]:
            total_events += 1
            report_log.append(f"✅ 完成事件: {res['current_evt_id']}")
            state["is_transition"] = True
            state["choice"] = ""
            state["current_evt_id"] = ""
        else:
            state["is_transition"] = False
            state["choice"] = res["next_options"][0] if res["next_options"] else "【沉默】"

        state.update({
            "chapter": res["chapter"], "turn": res["turn"], "san": res["san"],
            "money": res["money"], "gpa": res["gpa"], "arg_count": res["arg_count"],
            "affinity": res["affinity"], "current_evt_id": res["current_evt_id"]
        })
        
        save_partial_report(i)
        print(f"[Turn {i+1}] {state['chapter']}年-{res.get('turn')} | {res.get('current_evt_id')} | {gen_time:.1f}s")

    print(f"\n📝 Simulation Finished. Final Report in data/test_report.md")
    return True

if __name__ == "__main__":
    run_simulation(use_mock=False)

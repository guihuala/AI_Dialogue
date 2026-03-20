import json
import os
from typing import Any, Dict

from src.core.config import ROSTER_PATH, get_user_prompts_dir
from src.core.presets import CANDIDATE_POOL


def normalize_roster_single_player(roster: Dict[str, Any]) -> Dict[str, Any]:
    """
    保证 roster 中始终只有一个 is_player=True。
    若未设置主角，则默认回退到 player_anran 或第一位角色。
    """
    if not isinstance(roster, dict) or not roster:
        return roster

    normalized = {}
    for cid, item in roster.items():
        if isinstance(item, dict):
            normalized[cid] = dict(item)
        else:
            normalized[cid] = {"name": str(item)}

    player_ids = [cid for cid, item in normalized.items() if bool(item.get("is_player", False))]
    chosen = player_ids[0] if player_ids else ("player_anran" if "player_anran" in normalized else next(iter(normalized.keys())))

    for cid in normalized.keys():
        normalized[cid]["is_player"] = cid == chosen
    return normalized


def get_current_roster(user_id: str = "default"):
    """动态获取当前角色档案库集"""
    user_prompts_dir = get_user_prompts_dir(user_id)
    user_roster_path = os.path.join(user_prompts_dir, "characters", "roster.json")

    if os.path.exists(user_roster_path):
        try:
            with open(user_roster_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                normalized = normalize_roster_single_player(data)
                if normalized != data:
                    with open(user_roster_path, "w", encoding="utf-8") as wf:
                        json.dump(normalized, wf, ensure_ascii=False, indent=4)
                return normalized
        except Exception as e:
            print(f"Error loading user roster.json ({user_id}): {e}")

    roster = {}
    try:
        if os.path.exists(ROSTER_PATH):
            with open(ROSTER_PATH, "r", encoding="utf-8") as rf:
                roster = json.load(rf)
    except Exception as e:
        print(f"Error loading default roster.json: {e}")

    if not roster:
        for cid, profile in CANDIDATE_POOL.items():
            roster[cid] = {
                "name": profile.Name,
                "archetype": profile.Core_Archetype,
                "tags": profile.Tags,
                "description": profile.Background_Secret[:40] + "...",
                "file": f"{cid}.md",
                "is_player": profile.Name == "陆陈安然",
            }

    try:
        os.makedirs(os.path.dirname(user_roster_path), exist_ok=True)
        roster = normalize_roster_single_player(roster)
        with open(user_roster_path, "w", encoding="utf-8") as f:
            json.dump(roster, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

    return roster


import argparse
import json
import os
import socket
import sys
import time
import uuid
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
REPORT_PATH = os.path.join(BASE_DIR, "data", "relation_test_report.md")
API_BASE = "http://127.0.0.1:8000"
HTTP_TIMEOUT = 120.0


def _http_json(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    visitor_id: Optional[str] = None,
    timeout: Optional[float] = None,
    max_retries: int = 1,
) -> Dict[str, Any]:
    effective_timeout = float(timeout if timeout is not None else HTTP_TIMEOUT)
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if visitor_id:
        headers["X-Visitor-Id"] = visitor_id
    data = json.dumps(body).encode("utf-8") if body is not None else None
    last_err: Optional[Exception] = None
    for attempt in range(max(1, int(max_retries)) + 1):
        req = urllib.request.Request(url=url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                text = resp.read().decode("utf-8")
                return json.loads(text) if text.strip() else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {raw}") from e
        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
            last_err = e
            if attempt < max(1, int(max_retries)):
                time.sleep(1.0 + attempt * 0.5)
                continue
            raise RuntimeError(f"{method} {path} -> Network error: {e}") from e
    raise RuntimeError(f"{method} {path} -> Unknown network error: {last_err}")


def _set_single_dm_mode(visitor_id: str) -> None:
    _http_json(
        "POST",
        "/api/system/settings",
        {
            "dialogue_mode": "single_dm",
            "latency_mode": "balanced",
            "stability_mode": "stable",
            "turn_debug": True,
        },
        visitor_id=visitor_id,
        timeout=30.0,
    )


def _load_event_tag_map() -> Dict[str, List[str]]:
    # 延迟 import，避免在纯 API 网络失败时触发不必要错误
    from src.core.data_loader import load_all_events

    event_db = load_all_events(os.path.join(BASE_DIR, "data", "events"))
    out: Dict[str, List[str]] = {}
    for evt_id, evt in event_db.items():
        tags = [str(item).strip() for item in (getattr(evt, "narrative_tags", []) or []) if str(item).strip()]
        out[str(evt_id)] = tags
    return out


def _event_base_id(event_id: str) -> str:
    return str(event_id or "").split("__tgt_")[0]


def _is_relation_event(event_id: str, tag_map: Dict[str, List[str]]) -> Tuple[bool, List[str], bool]:
    eid = str(event_id or "").strip()
    if not eid:
        return False, [], False
    is_template_instance = "__tgt_" in eid
    base = _event_base_id(eid)
    tags = tag_map.get(base, [])
    keywords = ["关系", "暧昧", "约会", "冲突", "冷战", "和解", "升温", "恶化"]
    hit = any(any(k in t for k in keywords) for t in tags) or is_template_instance
    return hit, tags, is_template_instance


def _choose_option(
    options: List[str],
    turn_index: int,
    total_turns: int,
    repeat_same_event: int = 0,
) -> str:
    if not options:
        return "【进入下一幕】继续前进"
    continue_opts = [
        str(o)
        for o in options
        if any(token in str(o) for token in ["继续剧情", "进入下一幕", "下一幕", "转场", "继续前进"])
    ]
    # 若同一事件持续过久，优先转场，避免测试一直卡在开局事件
    if continue_opts and repeat_same_event >= 2:
        return continue_opts[0]
    # 定期转场，增加覆盖事件池概率
    if continue_opts and turn_index % 3 == 0:
        return continue_opts[0]
    aggressive = ["质问", "回怼", "拒绝", "摊牌", "冲突", "硬刚", "对抗", "追问"]
    warm = ["安慰", "缓和", "和解", "沟通", "道歉", "支持", "维护", "台阶"]
    prefer = aggressive if turn_index <= max(1, total_turns // 2) else warm
    for opt in options:
        if any(k in str(opt) for k in prefer):
            return str(opt)
    return str(options[0])


def _snapshot_rel_state(narrative_state: Dict[str, Any], active_roommates: List[str]) -> Dict[str, Dict[str, Any]]:
    rel_map = (narrative_state or {}).get("relationship_state", {})
    if not isinstance(rel_map, dict):
        return {}
    out = {}
    for name in active_roommates:
        rel = rel_map.get(name)
        if not isinstance(rel, dict):
            continue
        out[name] = {
            "stage": str(rel.get("relationship_stage", "熟悉")),
            "trust": float(rel.get("trust", 50) or 50),
            "tension": float(rel.get("tension", 50) or 50),
            "intimacy": float(rel.get("intimacy", 30) or 30),
        }
    return out


def _diff_rel(prev: Dict[str, Dict[str, Any]], cur: Dict[str, Dict[str, Any]]) -> List[str]:
    changes = []
    for name, now in cur.items():
        old = prev.get(name)
        if not old:
            continue
        old_stage = str(old.get("stage", ""))
        new_stage = str(now.get("stage", ""))
        if old_stage and new_stage and old_stage != new_stage:
            changes.append(f"{name}:{old_stage}->{new_stage}")
    return changes


def _write_report(payload: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# 单一DM关系联动专项测试报告")
    lines.append("")
    lines.append(f"- 测试时间: {payload.get('ts')}")
    lines.append(f"- API: `{payload.get('api_base')}`")
    lines.append(f"- visitor_id: `{payload.get('visitor_id')}`")
    lines.append(f"- 回合目标: `{payload.get('target_turns')}`")
    lines.append(f"- 实际回合: `{payload.get('executed_turns')}`")
    lines.append("")
    lines.append("## 总结")
    lines.append("")
    lines.append(f"- 平均回合耗时: `{payload.get('turn_avg_sec')}` s")
    lines.append(f"- 关系阶段变化次数: `{payload.get('stage_change_count')}`")
    lines.append(f"- 新增里程碑条数: `{payload.get('milestone_count')}`")
    lines.append(f"- 关系类事件命中: `{payload.get('relation_event_hits')}` / `{payload.get('executed_turns')}`")
    lines.append(f"- 模板事件命中: `{payload.get('template_event_hits')}`")
    lines.append("")
    lines.append("## 最终关系状态")
    lines.append("")
    lines.append("| 角色 | 阶段 | trust | tension | intimacy |")
    lines.append("|---|---|---:|---:|---:|")
    for name, rel in payload.get("final_rel_state", {}).items():
        lines.append(
            f"| {name} | {rel.get('stage','熟悉')} | "
            f"{round(float(rel.get('trust', 0)), 1)} | "
            f"{round(float(rel.get('tension', 0)), 1)} | "
            f"{round(float(rel.get('intimacy', 0)), 1)} |"
        )
    lines.append("")
    lines.append("## 最终好感度")
    lines.append("")
    lines.append("| 角色 | affinity |")
    lines.append("|---|---:|")
    for name, score in payload.get("final_affinity", {}).items():
        try:
            val = round(float(score), 1)
        except Exception:
            val = score
        lines.append(f"| {name} | {val} |")
    lines.append("")
    lines.append("## 新增里程碑")
    lines.append("")
    milestones = payload.get("milestones", [])
    if milestones:
        for item in milestones:
            lines.append(f"- {item}")
    else:
        lines.append("- （未检测到新增里程碑）")
    lines.append("")
    lines.append("## 回合明细")
    lines.append("")
    lines.append("| 回合 | 事件ID | 事件内回合 | 选项 | 过场预览 | 对话预览 | 耗时(s) | 关系事件 | 模板事件 | 阶段变化 | 真卡住 |")
    lines.append("|---:|---|---:|---|---|---|---:|---:|---:|---|---:|")
    for row in payload.get("rows", []):
        preview = str(row.get("dialogue_preview", "") or "").replace("|", "｜")
        transition_preview = str(row.get("transition_preview", "") or "").replace("|", "｜")
        lines.append(
            f"| {row.get('turn')} | `{row.get('evt_id')}` | {row.get('event_turn','-')} | "
            f"`{row.get('choice')}` | {transition_preview if transition_preview else '-'} | {preview if preview else '-'} | {row.get('elapsed')} | "
            f"{'Y' if row.get('is_relation_event') else 'N'} | "
            f"{'Y' if row.get('is_template_event') else 'N'} | "
            f"{', '.join(row.get('stage_changes', [])) if row.get('stage_changes') else '-'} | "
            f"{'Y' if row.get('is_stalled') else 'N'} |"
        )
    lines.append("")
    lines.append("## 回合对话全文")
    lines.append("")
    for row in payload.get("rows", []):
        lines.append(f"### 回合 {row.get('turn')}（`{row.get('evt_id')}`）")
        lines.append("")
        lines.append(f"- 选项: `{row.get('choice')}`")
        if row.get("narrator_transition"):
            lines.append(f"- 过场: {row.get('narrator_transition')}")
        dialog_lines = row.get("dialogue_lines", []) or []
        if dialog_lines:
            for dl in dialog_lines:
                lines.append(f"- {dl}")
        else:
            lines.append("- （无可用对话）")
        lines.append("")
    lines.append("## 观察结论")
    lines.append("")
    lines.append("- 如果“关系事件命中率”持续偏低，优先补充事件 `narrative_tags` 中的关系标签。")
    lines.append("- 如果“里程碑有变化但事件无反馈”，优先检查关系窗口命中池是否缺少对应标签事件。")
    lines.append("- 如果全程无阶段变化，可提升冲突/和解相关选项的选择策略强度。")
    lines.append("")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    global API_BASE, HTTP_TIMEOUT
    parser = argparse.ArgumentParser(description="Single-DM relationship flow benchmark")
    parser.add_argument("--turns", type=int, default=18, help="planned turns")
    parser.add_argument("--api-base", type=str, default=API_BASE, help="API base URL")
    parser.add_argument(
        "--roommates",
        type=str,
        default="tang_mengqi,lin_sa,li_yinuo",
        help="comma-separated roommate ids for start_game",
    )
    parser.add_argument(
        "--force-transition-every",
        type=int,
        default=2,
        help="force a transition turn every N rounds (use 0 to disable)",
    )
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=120.0,
        help="HTTP timeout (seconds) for each API call",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=1,
        help="retry times for transient timeout/network errors per API call",
    )
    args = parser.parse_args()

    API_BASE = args.api_base.rstrip("/")
    HTTP_TIMEOUT = max(30.0, float(args.http_timeout))
    http_retries = max(0, int(args.http_retries))
    turns_target = max(6, int(args.turns))
    force_transition_every = max(0, int(args.force_transition_every))
    roommates = [x.strip() for x in str(args.roommates).split(",") if x.strip()]
    visitor_id = f"rel-single-dm-{uuid.uuid4()}"
    tag_map = _load_event_tag_map()

    print("🚀 开始单一DM关系联动测试")
    print(f"🔁 计划回合: {turns_target}")
    print(f"👥 室友: {roommates}")
    print(f"🌐 API: {API_BASE}")

    _set_single_dm_mode(visitor_id)
    start_res = _http_json(
        "POST",
        "/api/game/start",
        {"roommates": roommates, "save_id": "slot_rel_test"},
        visitor_id=visitor_id,
        timeout=120.0,
    )

    current = dict(start_res)
    active_roommates = list(current.get("active_roommates") or roommates)
    seen_milestones = set(str(x) for x in ((current.get("narrative_state") or {}).get("long_term_milestones") or []))
    collected_milestones: List[str] = []
    prev_rel = _snapshot_rel_state(current.get("narrative_state") or {}, active_roommates)
    rows = []
    turn_costs: List[float] = []
    relation_event_hits = 0
    template_event_hits = 0
    stage_change_count = 0
    same_event_streak = 0
    last_evt_id = str(current.get("current_evt_id", "") or "")
    last_event_turn = int(current.get("turn", 1) or 1)

    for i in range(1, turns_target + 1):
        options = current.get("next_options") or []
        choice = _choose_option(options, i, turns_target, same_event_streak)
        force_transition = bool(force_transition_every and i % force_transition_every == 0)
        if force_transition:
            transition_opts = [
                str(o)
                for o in options
                if any(token in str(o) for token in ["继续剧情", "进入下一幕", "下一幕", "转场", "继续前进"])
            ]
            choice = transition_opts[0] if transition_opts else "【进入下一幕】继续前进"
        req = {
            "choice": choice,
            "active_roommates": current.get("active_roommates") or active_roommates,
            "current_evt_id": current.get("current_evt_id", ""),
            "is_transition": (
                force_transition
                or any(token in choice for token in ["继续剧情", "进入下一幕", "下一幕", "转场", "继续前进"])
                or bool(current.get("is_end"))
            ),
            "chapter": int(current.get("chapter", 1)),
            "turn": int(current.get("turn", i)),
            "san": int(current.get("san", 100)),
            "money": float(current.get("money", 2000)),
            "gpa": float(current.get("gpa", 4.0)),
            "hygiene": int(current.get("hygiene", 100)),
            "reputation": int(current.get("reputation", 100)),
            "arg_count": int(current.get("arg_count", 0)),
            "affinity": current.get("affinity", {}),
            "wechat_data_list": [],
            "save_id": "slot_rel_test",
        }
        t0 = time.perf_counter()
        res = _http_json(
            "POST",
            "/api/game/turn",
            req,
            visitor_id=visitor_id,
            timeout=HTTP_TIMEOUT,
            max_retries=http_retries,
        )
        elapsed = round(time.perf_counter() - t0, 3)
        turn_costs.append(float(elapsed))

        evt_id = str(res.get("current_evt_id", "") or "")
        event_turn = int(res.get("turn", i) or i)
        is_rel_evt, evt_tags, is_tpl_evt = _is_relation_event(evt_id, tag_map)
        if is_rel_evt:
            relation_event_hits += 1
        if is_tpl_evt:
            template_event_hits += 1

        cur_rel = _snapshot_rel_state(res.get("narrative_state") or {}, active_roommates)
        stage_changes = _diff_rel(prev_rel, cur_rel)
        stage_change_count += len(stage_changes)
        prev_rel = cur_rel
        dialog_seq = res.get("dialogue_sequence") or []
        dialog_lines: List[str] = []
        if isinstance(dialog_seq, list):
            for item in dialog_seq[:8]:
                if not isinstance(item, dict):
                    continue
                speaker = str(item.get("speaker", "") or "").strip() or "未知"
                content = str(item.get("content", "") or "").strip()
                if content:
                    content = content.replace("\n", " ").strip()
                    dialog_lines.append(f"[{speaker}] {content}")
        preview = " / ".join(dialog_lines[:2])
        if len(preview) > 140:
            preview = preview[:140] + "..."
        narrator_transition = str(res.get("narrator_transition", "") or "").strip().replace("\n", " ")
        transition_preview = narrator_transition
        if len(transition_preview) > 90:
            transition_preview = transition_preview[:90] + "..."

        milestones = [str(x).strip() for x in ((res.get("narrative_state") or {}).get("long_term_milestones") or []) if str(x).strip()]
        for item in milestones:
            if item not in seen_milestones:
                seen_milestones.add(item)
                collected_milestones.append(item)

        is_stalled = bool(evt_id == last_evt_id and event_turn <= last_event_turn)
        rows.append(
            {
                "turn": i,
                "evt_id": evt_id,
                "event_turn": event_turn,
                "choice": choice,
                "elapsed": elapsed,
                "is_relation_event": is_rel_evt,
                "is_template_event": is_tpl_evt,
                "evt_tags": evt_tags,
                "stage_changes": stage_changes,
                "is_stalled": is_stalled,
                "dialogue_preview": preview,
                "dialogue_lines": dialog_lines,
                "narrator_transition": narrator_transition,
                "transition_preview": transition_preview,
            }
        )
        current = dict(res)
        if evt_id and evt_id == last_evt_id:
            same_event_streak += 1
        else:
            same_event_streak = 0
        last_evt_id = evt_id
        last_event_turn = event_turn

    final_rel_state = _snapshot_rel_state(current.get("narrative_state") or {}, active_roommates)
    avg_turn = round(sum(turn_costs) / len(turn_costs), 3) if turn_costs else -1.0

    payload = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_base": API_BASE,
        "visitor_id": visitor_id,
        "target_turns": turns_target,
        "executed_turns": len(rows),
        "turn_avg_sec": avg_turn,
        "stage_change_count": stage_change_count,
        "milestone_count": len(collected_milestones),
        "relation_event_hits": relation_event_hits,
        "template_event_hits": template_event_hits,
        "final_rel_state": final_rel_state,
        "final_affinity": dict(current.get("affinity", {}) or {}),
        "milestones": collected_milestones,
        "rows": rows,
    }
    _write_report(payload)
    print(f"✅ 关系联动测试完成，报告已写入: {REPORT_PATH}")


if __name__ == "__main__":
    main()

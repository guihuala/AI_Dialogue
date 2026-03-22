import argparse
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Tuple


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EVENTS_DIR = os.path.join(BASE_DIR, "data", "events")
DEFAULT_OUTPUT = os.path.join(DEFAULT_EVENTS_DIR, "event_skeletons.generated.json")
DEFAULT_REPORT = os.path.join(DEFAULT_EVENTS_DIR, "event_skeletons.migration_report.md")


CHAR_ID_MAP = {
    "唐梦琪": "tang_mengqi",
    "林飒": "lin_sa",
    "李一诺": "li_yinuo",
    "苏浅": "su_qian",
}


def _split_list(raw: str) -> List[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    return [x.strip() for x in text.replace("，", "|").split("|") if x and x.strip()]


def _parse_bool(raw: str, default: bool = False) -> bool:
    text = str(raw or "").strip().lower()
    if text in {"1", "true", "y", "yes", "是"}:
        return True
    if text in {"0", "false", "n", "no", "否"}:
        return False
    return default


def _slug(text: str) -> str:
    s = str(text or "").strip().lower()
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _infer_type(row: Dict[str, str]) -> str:
    event_type = str(row.get("事件类型", "")).strip()
    trigger = str(row.get("触发条件", "")).strip()
    is_boss = _parse_bool(row.get("是否Boss", ""), default=False)

    key_markers = ["开局", "固定", "条件触发", "boss", "关键", "主线"]
    if is_boss:
        return "key"
    if any(marker in event_type.lower() for marker in key_markers):
        return "key"
    if trigger:
        return "key"
    return "daily"


def _infer_priority(row: Dict[str, str], evt_type: str) -> int:
    event_type = str(row.get("事件类型", "")).strip()
    chapter = int(float(str(row.get("所属章节", "1") or "1")))
    base = 64 if evt_type == "key" else 50
    if "开局" in event_type:
        base = max(base, 88)
    elif "固定" in event_type:
        base = max(base, 74)
    elif "条件触发" in event_type:
        base = max(base, 72)
    elif "角色专属" in event_type:
        base = max(base, 60)

    # 稍微给后期章节提权，便于自然推进。
    base += max(0, chapter - 1) * 2
    return max(10, min(95, int(base)))


def _infer_cooldown(evt_type: str, row: Dict[str, str]) -> int:
    event_type = str(row.get("事件类型", "")).strip()
    if evt_type == "daily":
        if "角色专属" in event_type:
            return 2
        return 1
    if "开局" in event_type:
        return 99
    if "固定" in event_type:
        return 4
    return 3


def _infer_once(row: Dict[str, str], evt_type: str) -> bool:
    event_type = str(row.get("事件类型", "")).strip()
    if evt_type == "key":
        return True if ("开局" in event_type or "固定" in event_type or "条件触发" in event_type) else False
    return False


def _extract_chapter(row: Dict[str, str]) -> int:
    raw = str(row.get("所属章节", "1") or "1").strip()
    try:
        return max(1, int(float(raw)))
    except Exception:
        return 1


def _chapter_to_day_min(chapter: int) -> int:
    # 四学年拆成阶段窗口，按文档玩法先给保守映射。
    return max(1, (chapter - 1) * 7 + 1)


def _map_char_id(raw_name: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return ""
    return CHAR_ID_MAP.get(name, _slug(name))


def _parse_trigger_conditions(trigger_text: str, exclusive_char: str, chapter: int) -> Dict[str, Any]:
    triggers: Dict[str, Any] = {"day_min": _chapter_to_day_min(chapter)}
    text = str(trigger_text or "").strip()
    if exclusive_char:
        char_id = _map_char_id(exclusive_char)
        if char_id:
            triggers["active_any"] = [char_id]

    if not text:
        return triggers

    low = text.lower().replace(" ", "")

    affinity_match = re.search(r"(affinity|好感度|好感)[><=]+(\d+)", low)
    if affinity_match:
        num = int(affinity_match.group(2))
        relation_target = {"char": _map_char_id(exclusive_char)} if exclusive_char else {}
        if ">" in low:
            relation_target["trust_gte"] = num
        elif "<" in low:
            relation_target["trust_lte"] = num
        if relation_target:
            triggers["relation_target"] = relation_target

    hygiene_match = re.search(r"(hygiene|卫生)[><=]+(\d+)", low)
    if hygiene_match:
        # 当前骨架没有 hygiene 语义，先降级到 flags，报告中会标注手动核验。
        num = int(hygiene_match.group(2))
        if "<" in low:
            triggers["flags_all_true"] = [f"legacy:hygiene_below_{num}"]
        elif ">" in low:
            triggers["flags_all_true"] = [f"legacy:hygiene_above_{num}"]

    # 轻量关键词映射
    if "冲突" in text or "争吵" in text or "冷战" in text:
        triggers["relation_any"] = {"tension_gte": 58}
    if "和解" in text or "亲密" in text or "约会" in text:
        triggers["relation_any"] = {"intimacy_gte": 52}

    return triggers


def _default_key_options(evt_id: str, title: str, desc: str) -> List[Dict[str, Any]]:
    base = _slug(evt_id) or "legacy_key"
    short_title = str(title or "关键事件").strip()
    scene_hint = str(desc or "").strip()[:18]
    subject = scene_hint if scene_hint else short_title
    return [
        {"id": f"{base}_support", "attitude": "支持", "effects": {"dorm_mood_delta": 2}, "text_hint": f"支持并推进：{subject}"},
        {"id": f"{base}_neutral", "attitude": "中立", "effects": {"dorm_mood_delta": 0}, "text_hint": f"保留意见：{subject}"},
        {"id": f"{base}_avoid", "attitude": "回避", "effects": {"dorm_mood_delta": -2}, "text_hint": f"先回避冲突：{subject}"},
    ]


def _infer_options(row: Dict[str, str], evt_type: str) -> List[Dict[str, Any]]:
    raw = str(row.get("玩家交互", "") or "").strip()
    title = str(row.get("事件标题", "")).strip()
    desc = str(row.get("场景与冲突描述", "") or row.get("描述", "")).strip()
    evt_id = str(row.get("Event_ID", "")).strip()

    if not raw:
        return _default_key_options(evt_id, title, desc) if evt_type == "key" else []

    parts = [p.strip() for p in raw.replace("，", "|").split("|") if p and p.strip()]
    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(parts):
        normalized = item.replace("：", ":")
        content = normalized.split(":", 1)[1].strip() if ":" in normalized else normalized
        low = content.lower()
        if any(k in content for k in ["支持", "同意", "帮", "配合"]):
            attitude = "支持"
            mood_delta = 2
        elif any(k in content for k in ["回避", "拒绝", "走开", "不管"]):
            attitude = "回避"
            mood_delta = -2
        elif any(k in content for k in ["质问", "对抗", "怼", "摊牌"]):
            attitude = "对抗"
            mood_delta = -3
        elif "neutral" in low or any(k in content for k in ["中立", "观望", "再想想"]):
            attitude = "中立"
            mood_delta = 0
        else:
            attitude = ["支持", "中立", "回避", "对抗"][idx % 4]
            mood_delta = {"支持": 2, "中立": 0, "回避": -2, "对抗": -3}[attitude]
        out.append(
            {
                "id": f"{_slug(evt_id) or 'legacy'}_opt_{idx + 1}",
                "attitude": attitude,
                "effects": {"dorm_mood_delta": mood_delta},
                "text_hint": content,
            }
        )
    return out[:4]


def _build_meta(row: Dict[str, str], source_csv: str, migration_notes: List[str]) -> Dict[str, Any]:
    chapter = _extract_chapter(row)
    tags = _split_list(row.get("叙事标签", ""))
    hooks = {
        "state_hooks": _split_list(row.get("状态钩子", "")),
        "relationship_hooks": _split_list(row.get("关系钩子", "")),
    }
    potential_conflicts = _split_list(row.get("潜在冲突点", ""))
    return {
        "source_csv": source_csv,
        "source_event_type": str(row.get("事件类型", "")).strip(),
        "chapter": chapter,
        "exclusive_char": str(row.get("专属角色", "")).strip(),
        "trigger_conditions_raw": str(row.get("触发条件", "")).strip(),
        "narrative_tags": tags,
        "potential_conflicts": potential_conflicts,
        "hooks": hooks,
        "migration_notes": migration_notes,
    }


def _migrate_row(row: Dict[str, str], source_csv: str) -> Tuple[Dict[str, Any], List[str]]:
    evt_id = str(row.get("Event_ID", "")).strip()
    title = str(row.get("事件标题", "")).strip() or evt_id
    desc = str(row.get("场景与冲突描述", "") or row.get("描述", "")).strip()
    chapter = _extract_chapter(row)
    exclusive_char = str(row.get("专属角色", "")).strip()
    trigger_text = str(row.get("触发条件", "")).strip()

    notes: List[str] = []
    evt_type = _infer_type(row)
    if trigger_text and ("hygiene" in trigger_text.lower() or "卫生" in trigger_text):
        notes.append("触发条件含 hygiene/卫生，已降级映射到 legacy flags，请人工复核。")
    if not trigger_text:
        notes.append("原事件无显式触发条件，已按 chapter/day_min 与事件类型做保守映射。")
    if not exclusive_char and "角色专属" in str(row.get("事件类型", "")):
        notes.append("标记为角色专属但未填写专属角色，需人工补充 active_any。")

    skeleton: Dict[str, Any] = {
        "id": evt_id,
        "type": evt_type,
        "title": title,
        "priority": _infer_priority(row, evt_type),
        "cooldown_days": _infer_cooldown(evt_type, row),
        "once": _infer_once(row, evt_type),
        "triggers": _parse_trigger_conditions(trigger_text, exclusive_char, chapter),
        "options": _infer_options(row, evt_type),
        "meta": _build_meta(row, source_csv=source_csv, migration_notes=notes),
    }

    if desc:
        skeleton["meta"]["legacy_scene"] = desc
    if str(row.get("开场目标", "")).strip():
        skeleton["meta"]["opening_goal"] = str(row.get("开场目标", "")).strip()
    if str(row.get("施压目标", "")).strip():
        skeleton["meta"]["pressure_goal"] = str(row.get("施压目标", "")).strip()
    if str(row.get("转折目标", "")).strip():
        skeleton["meta"]["turning_goal"] = str(row.get("转折目标", "")).strip()
    if str(row.get("收束目标", "")).strip():
        skeleton["meta"]["settlement_goal"] = str(row.get("收束目标", "")).strip()

    return skeleton, notes


def migrate_events(events_dir: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    migrated: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "files": 0,
        "rows": 0,
        "skipped_empty_id": 0,
        "types": Counter(),
        "csv_count": Counter(),
        "notes": Counter(),
    }

    csv_paths = sorted(
        os.path.join(events_dir, name)
        for name in os.listdir(events_dir)
        if name.endswith(".csv")
    )

    for path in csv_paths:
        stats["files"] += 1
        csv_name = os.path.basename(path)
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                clean_row = {str(k).strip(): str(v or "").strip() for k, v in (row or {}).items() if k is not None}
                evt_id = str(clean_row.get("Event_ID", "")).strip()
                if not evt_id:
                    stats["skipped_empty_id"] += 1
                    continue
                skeleton, notes = _migrate_row(clean_row, source_csv=csv_name)
                migrated.append(skeleton)
                stats["rows"] += 1
                stats["types"][skeleton.get("type", "daily")] += 1
                stats["csv_count"][csv_name] += 1
                for note in notes:
                    stats["notes"][note] += 1

    migrated.sort(key=lambda x: (0 if x.get("type") == "key" else 1, int(x.get("priority", 0)) * -1, str(x.get("id", ""))))
    return migrated, stats


def write_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_report(
    path: str,
    output_json: str,
    events_dir: str,
    stats: Dict[str, Any],
    sample: List[Dict[str, Any]],
) -> None:
    lines: List[str] = []
    lines.append("# 旧事件 -> 骨架事件 迁移报告")
    lines.append("")
    lines.append(f"- 生成时间: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append(f"- 事件目录: `{events_dir}`")
    lines.append(f"- 输出文件: `{output_json}`")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- CSV 文件数: `{stats.get('files', 0)}`")
    lines.append(f"- 读取事件行: `{stats.get('rows', 0)}`")
    lines.append(f"- 空 Event_ID 跳过: `{stats.get('skipped_empty_id', 0)}`")
    lines.append(f"- key 事件: `{stats.get('types', {}).get('key', 0)}`")
    lines.append(f"- daily 事件: `{stats.get('types', {}).get('daily', 0)}`")
    lines.append("")
    lines.append("## 按文件统计")
    lines.append("")
    for k in sorted(stats.get("csv_count", {})):
        lines.append(f"- `{k}`: `{stats['csv_count'][k]}`")
    lines.append("")
    lines.append("## 自动迁移提示")
    lines.append("")
    notes = stats.get("notes", {})
    if notes:
        for k, v in notes.items():
            lines.append(f"- `{k}` x `{v}`")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 样例（前5条）")
    lines.append("")
    for item in sample[:5]:
        lines.append(f"- `{item.get('id')}` | `{item.get('type')}` | priority `{item.get('priority')}`")
        lines.append(f"  - title: {item.get('title')}")
        lines.append(f"  - triggers: {json.dumps(item.get('triggers', {}), ensure_ascii=False)}")
        if item.get("options"):
            lines.append(f"  - options: {json.dumps(item.get('options', [])[:3], ensure_ascii=False)}")
    lines.append("")
    lines.append("## 后续建议")
    lines.append("")
    lines.append("- 先抽查 key 事件的 `triggers`，优先修正 `flags_all_true` 的 legacy 条件。")
    lines.append("- 再补充专属角色缺失项，避免角色专属事件进入全局池。")
    lines.append("- 验证通过后可把 `event_skeletons.generated.json` 改名为 `event_skeletons.json` 启用。")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate legacy CSV events into event skeleton JSON draft.")
    parser.add_argument("--events-dir", type=str, default=DEFAULT_EVENTS_DIR, help="path to events directory containing csv files")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="output generated skeleton json path")
    parser.add_argument("--report", type=str, default=DEFAULT_REPORT, help="output migration report markdown path")
    parser.add_argument("--overwrite", action="store_true", help="overwrite output files when exist")
    return parser.parse_args()


def ensure_writable(path: str, overwrite: bool) -> None:
    if os.path.exists(path) and not overwrite:
        raise RuntimeError(f"Output exists: {path}. Use --overwrite to replace.")


def main() -> None:
    args = parse_args()
    events_dir = os.path.abspath(args.events_dir)
    output_path = os.path.abspath(args.output)
    report_path = os.path.abspath(args.report)

    if not os.path.isdir(events_dir):
        raise RuntimeError(f"Events directory not found: {events_dir}")

    ensure_writable(output_path, args.overwrite)
    ensure_writable(report_path, args.overwrite)

    migrated, stats = migrate_events(events_dir)
    payload = {
        "version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "events_dir": events_dir,
            "csv_files": stats.get("files", 0),
            "rows": stats.get("rows", 0),
        },
        "events": migrated,
    }
    write_json(output_path, payload)
    write_report(report_path, output_json=output_path, events_dir=events_dir, stats=stats, sample=migrated)

    print(f"✅ 迁移完成: {stats.get('rows', 0)} 条事件")
    print(f"📦 JSON: {output_path}")
    print(f"📝 报告: {report_path}")


if __name__ == "__main__":
    main()

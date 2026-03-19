import csv
import os
from src.models.schema import ScriptedEvent

def load_all_events(events_dir: str) -> dict:
    event_db = {}
    if not os.path.exists(events_dir):
        os.makedirs(events_dir, exist_ok=True)
        return event_db

    def _to_bool(value, default=False):
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in ["true", "1", "y", "yes", "是"]:
            return True
        if text in ["false", "0", "n", "no", "否"]:
            return False
        return default

    def _to_int(value, default):
        try:
            return int(float(str(value).strip()))
        except Exception:
            return default

    def _to_float(value, default):
        try:
            return float(str(value).strip())
        except Exception:
            return default

    def _split_list(text):
        raw = str(text or "").strip()
        if not raw:
            return []
        return [x.strip() for x in raw.replace("，", "|").split("|") if x and x.strip()]

    def _parse_labeled_map(text):
        raw = str(text or "").strip()
        if not raw:
            return {}
        parts = [p.strip() for p in raw.split("|") if p and p.strip()]
        parsed = {}
        fallback_idx = 0
        fallback_keys = ["A", "B", "C", "D", "E"]
        for p in parts:
            normalized = p.replace("：", ":")
            if ":" in normalized:
                k, v = normalized.split(":", 1)
                parsed[k.strip()] = v.strip()
            else:
                key = fallback_keys[fallback_idx] if fallback_idx < len(fallback_keys) else f"opt_{fallback_idx + 1}"
                parsed[key] = normalized.strip()
                fallback_idx += 1
        return parsed

    for filename in os.listdir(events_dir):
        if not filename.endswith(".csv"): continue
            
        file_path = os.path.join(events_dir, filename)
        
        default_type = "通用随机池"
        if "CG" in filename.upper(): default_type = "CG过场"
        elif "开局" in filename: default_type = "开局剧情池"
        elif "固定" in filename: default_type = "固定池"
        elif "条件" in filename: default_type = "条件触发池"
        elif "专属" in filename: default_type = "角色专属事件"

        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            script_key = next((k for k in headers if k and "预设剧本" in k), "预设剧本")
            
            for row in reader:
                try:
                    # 清洗 key 防止空格干扰
                    clean_row = {str(k).strip(): str(v or "").strip() for k, v in row.items() if k is not None}
                    evt_id = clean_row.get("Event_ID", "").strip()
                    if not evt_id: continue 
                    
                    options_dict = _parse_labeled_map(clean_row.get("玩家交互", ""))
                    outcomes_dict = _parse_labeled_map(clean_row.get("结果", ""))
                    
                    is_boss_str = str(clean_row.get("是否Boss", "FALSE")).strip().upper()
                    
                    # 🌟 核心防御：提取剧本，并抢救因为逗号错位被挤到表格外的列！
                    raw_fixed_dialogue = clean_row.get(script_key, "").strip()
                    leftover = row.get(None, []) # 获取被挤出表格的数据
                    if leftover:
                        raw_fixed_dialogue += "|" + "|".join(str(x) for x in leftover if x)
                        
                    fixed_dialogue = []
                    if raw_fixed_dialogue:
                        for line in raw_fixed_dialogue.split("|"):
                            line = line.replace("：", ":") # 兼容中文冒号
                            if ":" in line:
                                spk, cont = line.split(":", 1)
                                fixed_dialogue.append({"speaker": spk.strip(), "content": cont.strip(), "mood": "neutral"})
                    
                    is_cg = (len(fixed_dialogue) > 0 or "CG" in str(clean_row.get("事件类型", default_type)).upper())

                    min_turn_for_end = _to_int(clean_row.get("最短回合", clean_row.get("最少回合", 5)), 5)
                    max_turn_for_end = _to_int(clean_row.get("最长回合", clean_row.get("最多回合", 10)), 10)
                    if max_turn_for_end < min_turn_for_end:
                        max_turn_for_end = min_turn_for_end + 2

                    progress_beats = _split_list(
                        clean_row.get("推进节点", clean_row.get("剧情推进节点", clean_row.get("阶段节点", "")))
                    )
                    end_signals = _split_list(clean_row.get("收束条件", clean_row.get("结束信号", "")))
                    next_event_id = clean_row.get("下一事件ID", clean_row.get("下一事件", "")).strip() or None
                    event_weight = _to_float(clean_row.get("权重", clean_row.get("事件权重", 1.0)), 1.0)
                    cooldown_turns = _to_int(clean_row.get("冷却回合", clean_row.get("事件冷却", 2)), 2)
                    allow_repeat = _to_bool(clean_row.get("允许重复", "FALSE"), False)

                    event = ScriptedEvent(
                        id=evt_id,
                        name=clean_row.get("事件标题", "未命名").strip(),
                        chapter=int(clean_row.get("所属章节", 1) or 1),
                        event_type=clean_row.get("事件类型", default_type).strip(),
                        trigger_conditions=clean_row.get("触发条件", "").strip(),
                        exclusive_char=clean_row.get("专属角色", "").strip(),
                        is_boss=(is_boss_str in ["TRUE", "1", "Y"]),
                        description=clean_row.get("场景与冲突描述", clean_row.get("描述", "")).strip(),
                        potential_conflicts=_split_list(clean_row.get("潜在冲突点", "")),
                        next_event_id=next_event_id,
                        event_weight=max(0.1, event_weight),
                        cooldown_turns=max(0, cooldown_turns),
                        min_turn_for_end=max(2, min_turn_for_end),
                        max_turn_for_end=max(3, max_turn_for_end),
                        progress_beats=progress_beats,
                        end_signals=end_signals,
                        allow_repeat=allow_repeat,
                        options=options_dict,
                        outcomes=outcomes_dict,
                        is_cg=is_cg,
                        fixed_dialogue=fixed_dialogue
                    )
                    event_db[evt_id] = event
                except Exception as e:
                    print(f"❌ 解析 {filename} 出错: {e}")
                    
    print(f"✅ 成功从 {events_dir} 加载了 {len(event_db)} 个事件！")
    return event_db

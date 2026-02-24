import csv
import os
from src.models.schema import ScriptedEvent

def load_all_events(events_dir: str) -> dict:
    event_db = {}
    if not os.path.exists(events_dir):
        os.makedirs(events_dir, exist_ok=True)
        return event_db

    for filename in os.listdir(events_dir):
        if not filename.endswith(".csv"): continue
            
        file_path = os.path.join(events_dir, filename)
        
        # 1. 根据文件名判定类型
        default_type = "通用随机池"
        if "CG" in filename.upper(): default_type = "CG过场"
        elif "固定" in filename: default_type = "固定池"
        elif "条件" in filename: default_type = "条件触发池"
        elif "专属" in filename: default_type = "角色专属事件"

        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    evt_id = row.get("Event_ID", "").strip()
                    if not evt_id: continue 
                    
                    options_dict = {k.strip(): v.strip() for opt in row.get("玩家交互", "").split("|") if ":" in opt for k, v in [opt.split(":", 1)]}
                    outcomes_dict = {k.strip(): v.strip() for out in row.get("结果", "").split("|") if ":" in out for k, v in [out.split(":", 1)]}
                    
                    is_boss_str = str(row.get("是否Boss", "FALSE")).strip().upper()
                    
                    # 🌟 2. 解析 CG 专属的“预设剧本”
                    raw_fixed_dialogue = row.get("预设剧本", "").strip()
                    fixed_dialogue = []
                    if raw_fixed_dialogue:
                        for line in raw_fixed_dialogue.split("|"):
                            if ":" in line:
                                spk, cont = line.split(":", 1)
                                fixed_dialogue.append({"speaker": spk.strip(), "content": cont.strip(), "mood": "neutral"})
                    
                    # 如果填了预设剧本，或者在这个表里，就是 CG
                    is_cg = (len(fixed_dialogue) > 0 or default_type == "CG过场")

                    event = ScriptedEvent(
                        id=evt_id,
                        name=row.get("事件标题", "未命名").strip(),
                        chapter=int(row.get("所属章节", 1) or 1),
                        event_type=row.get("事件类型", default_type).strip(),
                        trigger_conditions=row.get("触发条件", "").strip(),
                        exclusive_char=row.get("专属角色", "").strip(),
                        is_boss=(is_boss_str in ["TRUE", "1", "Y"]),
                        description=row.get("场景与冲突描述", row.get("描述", "")).strip(),
                        potential_conflicts=[c.strip() for c in row.get("潜在冲突点", "").split("|") if c.strip()],
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
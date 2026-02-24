import csv
import os
from src.models.schema import ScriptedEvent

def load_events_from_csv(csv_path: str) -> dict:
    """
    从 CSV 文件加载事件配置表
    返回格式: { "evt_id": ScriptedEvent_Object }
    """
    event_db = {}
    
    if not os.path.exists(csv_path):
        print(f"⚠️ 警告: 找不到配置文件 {csv_path}，请检查路径。")
        return event_db

    # 使用 utf-8-sig 防止带 BOM 的中文 CSV 乱码
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # 1. 提取基础 ID 并跳过空行
                evt_id = row.get("Event_ID", "").strip()
                if not evt_id: 
                    continue 
                
                # 2. 解析列表格式 (用 | 分割)
                raw_conflicts = row.get("潜在冲突点", "")
                conflicts = [c.strip() for c in raw_conflicts.split("|") if c.strip()]
                
                # 3. 解析选项 (格式: A:内容|B:内容)
                raw_options = row.get("玩家交互", "")
                options_dict = {}
                for opt in raw_options.split("|"):
                    if ":" in opt:
                        k, v = opt.split(":", 1) # 只切分第一个冒号
                        options_dict[k.strip()] = v.strip()
                        
                # 4. 解析结果 (格式: A:结果|B:结果)
                raw_outcomes = row.get("结果", "")
                outcomes_dict = {}
                for out in raw_outcomes.split("|"):
                    if ":" in out:
                        k, v = out.split(":", 1)
                        outcomes_dict[k.strip()] = v.strip()

                # 5. 处理布尔值
                is_boss_str = str(row.get("是否Boss", "FALSE")).strip().upper()
                is_boss = is_boss_str in ["TRUE", "1", "是", "Y"]

                # 6. 实例化数据模型
                event = ScriptedEvent(
                    id=evt_id,
                    name=row.get("事件标题", "未命名事件").strip(),
                    chapter=int(row.get("所属章节", 1)),
                    is_boss=is_boss,
                    description=row.get("场景与冲突描述", "").strip(),
                    potential_conflicts=conflicts,
                    options=options_dict,
                    outcomes=outcomes_dict
                )
                
                event_db[evt_id] = event
            except Exception as e:
                print(f"❌ 解析事件表格出错 (Event_ID: {row.get('Event_ID')}): {e}")
                
    print(f"✅ 成功从 {os.path.basename(csv_path)} 加载了 {len(event_db)} 个事件！")
    return event_db
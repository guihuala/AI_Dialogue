import os
from src.core.data_loader import load_all_events

# --- 章节过场文案 ---
CHAPTER_TRANSITIONS = {
    1: "【第一章：大一·磨合】\n四个性格迥异的女生被随机塞进了404寝室。初见的美好很快被生活习惯的摩擦击碎...",
    2: "就这样，我们在磕磕绊绊与争吵中度过了大一。\n\n【第二章：大二·分化】\n随着专业课增多，有人开始混日子，有人开始卷绩点...",
    3: "【第三章：大三·内卷】\n考研、保研、实习的压力如同乌云笼罩...",
    4: "【第四章：毕业·清算】\n大学的最后时光。散伙饭上的暗流涌动，一切都将迎来最终的清算..."
}

# 指向 events 文件夹
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVENTS_DIR = os.path.join(BASE_DIR, "data", "events")

# 🌟 启动时统一加载所有表单
EVENT_DATABASE = load_all_events(EVENTS_DIR)

def get_event(event_id: str):
    return EVENT_DATABASE.get(event_id)
import os
import random
from src.models.schema import ScriptedEvent
from src.core.data_loader import load_events_from_csv

# --- 章节过场文案 ---
CHAPTER_TRANSITIONS = {
    1: "【第一章：大一·磨合】\n四个性格迥异的女生被随机塞进了404寝室。初见的美好很快被生活习惯的摩擦击碎...",
    2: "就这样，我们在磕磕绊绊与争吵中度过了大一。\n\n【第二章：大二·分化】\n随着专业课增多，有人开始混日子，有人开始卷绩点。寝室里的小团体也初见端倪...",
    3: "【第三章：大三·内卷】\n考研、保研、实习的压力如同乌云笼罩。曾经的盟友可能因为一个名额反目成仇...",
    4: "【第四章：毕业·清算】\n大学的最后时光。散伙饭上的暗流涌动，二手群里的恩怨，一切都将迎来最终的清算..."
}

# 动态获取 events.csv 的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVENTS_CSV_PATH = os.path.join(BASE_DIR, "data", "events.csv")

# 游戏启动时，自动读取表格数据到内存中
EVENT_DATABASE = load_events_from_csv(EVENTS_CSV_PATH)

def get_random_event(chapter: int, exclude_ids: list) -> ScriptedEvent:
    """从普通池中抽取一个事件"""
    pool = [e for e in EVENT_DATABASE.values() if e.chapter == chapter and not e.is_boss and e.id not in exclude_ids]
    return random.choice(pool) if pool else None

def get_boss_event(chapter: int) -> ScriptedEvent:
    """获取该章节的 Boss 事件"""
    pool = [e for e in EVENT_DATABASE.values() if e.chapter == chapter and e.is_boss]
    return pool[0] if pool else None

def get_event(event_id: str) -> ScriptedEvent:
    """通过 ID 获取特定事件"""
    return EVENT_DATABASE.get(event_id)
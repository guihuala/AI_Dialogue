import os
from src.core.data_loader import load_all_events

# 指向 events 文件夹
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVENTS_DIR = os.path.join(BASE_DIR, "data", "events")

# 启动时统一加载所有表单
EVENT_DATABASE = load_all_events(EVENTS_DIR)

def get_event(event_id: str):
    return EVENT_DATABASE.get(event_id)
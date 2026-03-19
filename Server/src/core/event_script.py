EVENT_DATABASE = {}

import os
from src.core.data_loader import load_all_events
from src.core.config import get_user_events_dir, DEFAULT_EVENTS_DIR

def load_user_events(user_id: str = "default"):
    """为特定用户动态加载事件库（默认库 + 用户库覆盖）"""
    events_dir = get_user_events_dir(user_id)
    default_db = load_all_events(DEFAULT_EVENTS_DIR)
    user_db = load_all_events(events_dir)

    # 用户库按 Event_ID 覆盖默认库，未覆盖项保留默认事件（尤其是开局固定剧情）
    if user_db:
        default_db.update(user_db)
    return default_db

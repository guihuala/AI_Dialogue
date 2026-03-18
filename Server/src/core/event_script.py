import os
from src.core.data_loader import load_all_events

from src.core.config import get_user_events_dir, DEFAULT_EVENTS_DIR

def load_user_events(user_id: str = "default"):
    """为特定用户动态加载事件库"""
    events_dir = get_user_events_dir(user_id)
    # 1. 加载用户私有事件
    user_db = load_all_events(events_dir)
    
    # 2. 如果是 default 用户或者用户没有任何私有事件，加载默认公共事件
    if not user_db:
        return load_all_events(DEFAULT_EVENTS_DIR)
    
    return user_db
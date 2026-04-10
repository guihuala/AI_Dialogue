EVENT_DATABASE = {}

import os
from src.core.data_loader import load_all_events
from src.core.config import get_user_events_dir, DEFAULT_EVENTS_DIR

def load_user_events(user_id: str = "default"):
    """为特定用户动态加载事件库（按文件名覆盖默认库）"""
    events_dir = get_user_events_dir(user_id)
    user_db = load_all_events(events_dir)
    user_csv_names = set()
    if os.path.exists(events_dir):
        try:
            user_csv_names = {
                name for name in os.listdir(events_dir)
                if str(name).endswith(".csv")
            }
        except Exception:
            user_csv_names = set()

    default_csv_names = set()
    if os.path.exists(DEFAULT_EVENTS_DIR):
        try:
            default_csv_names = {
                name for name in os.listdir(DEFAULT_EVENTS_DIR)
                if str(name).endswith(".csv")
            }
        except Exception:
            default_csv_names = set()

    # 模组一旦提供同名 CSV，就应整体覆盖默认事件池，而不是只按 Event_ID 零散覆盖。
    default_only_names = default_csv_names - user_csv_names
    default_db = load_all_events(DEFAULT_EVENTS_DIR, include_filenames=default_only_names)

    # 仍保留模组未提供的默认文件，避免缺少基础事件时直接空池。
    if user_db:
        default_db.update(user_db)
    return default_db

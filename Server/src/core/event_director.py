import random
import json
import os
from src.core.event_script import EVENT_DATABASE

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TIMELINE_PATH = os.path.join(BASE_DIR, "data", "events", "timeline.json")

class EventDirector:
    def __init__(self):
        self.used_events = []
        self.current_chapter = 1
        self.chapter_progress = 0
        self.timeline_config = self._load_timeline()
        
    def reload_timeline(self):
        """支持热更新读取"""
        self.timeline_config = self._load_timeline()

    def _load_timeline(self):
        if os.path.exists(TIMELINE_PATH):
            try:
                with open(TIMELINE_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Timeline 读取失败: {e}")
        
        # 🌟 默认的章节抽卡时间轴配置
        default_timeline = {
            "1": ["CG", "随机或专属", "通用", "Boss"],
            "2": ["CG", "通用", "随机或专属", "Boss"],
            "3": ["CG", "条件", "通用", "Boss"],
            "4": ["CG", "随机或专属", "通用", "Boss"]
        }
        os.makedirs(os.path.dirname(TIMELINE_PATH), exist_ok=True)
        with open(TIMELINE_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_timeline, f, ensure_ascii=False, indent=4)
        return default_timeline
        
    def get_next_event(self, player_stats: dict, active_chars: list):
        """精准读取 timeline.json 调度事件"""
        self.chapter_progress += 1
        chapter_key = str(self.current_chapter)
        
        current_timeline = self.timeline_config.get(chapter_key, ["CG", "通用", "Boss"])
        
        # 进度超过当前章节配置，强制进入下一章
        if self.chapter_progress > len(current_timeline):
            self.chapter_progress = 1
            self.current_chapter += 1
            chapter_key = str(self.current_chapter)
            current_timeline = self.timeline_config.get(chapter_key, ["CG", "通用", "Boss"])

        expected_type = current_timeline[self.chapter_progress - 1]
        available_events = [e for e in EVENT_DATABASE.values() if e.id not in self.used_events and e.chapter == self.current_chapter]
        
        pool = []
        
        # 1. 匹配当前回合需要的池子
        if "CG" in expected_type:
            pool = [e for e in available_events if "CG" in e.event_type.upper() or getattr(e, 'is_cg', False)]
        elif "Boss" in expected_type:
            pool = [e for e in available_events if getattr(e, 'is_boss', False)]
        elif "条件" in expected_type:
            if player_stats.get("hygiene", 100) < 60:
                pool = [e for e in available_events if "条件" in e.event_type and "Hygiene" in e.trigger_conditions]
            elif player_stats.get("money", 1500) < 300:
                pool = [e for e in available_events if "条件" in e.event_type and "Money" in e.trigger_conditions]
        elif "专属" in expected_type:
            ex_pool = [e for e in available_events if "专属" in e.event_type and e.exclusive_char in active_chars]
            # 如果配置的是 "随机或专属"，给 50% 几率下放，防止干瘪
            if "随机" in expected_type and random.random() < 0.5:
                pass 
            elif ex_pool:
                pool = ex_pool
        
        # 2. 如果池子干了（或要求通用），则降级到通用池
        if not pool and ("通用" in expected_type or "随机" in expected_type or not pool):
            pool = [e for e in available_events if "通用" in e.event_type or "随机" in e.event_type]
            
        # 3. 终极防崩溃：有什么出什么
        if not pool:
            pool = available_events
            
        if pool:
            evt = random.choice(pool)
            self.used_events.append(evt.id)
            return evt
            
        return None
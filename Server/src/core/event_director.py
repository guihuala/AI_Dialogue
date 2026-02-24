import random
from src.core.event_script import EVENT_DATABASE

class EventDirector:
    def __init__(self):
        self.used_events = []
        self.current_chapter = 1
        self.chapter_progress = 0 # 当前章节已经历的事件数
        
    def get_next_event(self, player_stats: dict, active_chars: list):
        """核心调度逻辑：决定接下来发生什么"""
        self.chapter_progress += 1
        
        # 1. 强制 Boss 节点 (章节底层必然是本章的 Boss)
        if self.chapter_progress >= 4:
            self.chapter_progress = 0
            self.current_chapter += 1
            boss_events = [e for e in EVENT_DATABASE.values() if e.chapter == self.current_chapter - 1 and e.is_boss]
            if boss_events: 
                return boss_events[0]
            
        available_events = [e for e in EVENT_DATABASE.values() if e.id not in self.used_events and e.chapter == self.current_chapter]
        
        # 2. 检查条件触发池
        if player_stats.get("hygiene", 100) < 60:
            cond_events = [e for e in available_events if "条件" in e.event_type and "Hygiene" in e.trigger_conditions]
            if cond_events:
                evt = random.choice(cond_events)
                self.used_events.append(evt.id)
                return evt
                
        # 3. 检查角色专属事件 (例如唐梦琪好感达标且她在场)
        if "唐梦琪" in active_chars and player_stats.get("affinity_tang", 0) > 50:
            ex_events = [e for e in available_events if "专属" in e.event_type and "唐梦琪" in e.exclusive_char]
            if ex_events:
                evt = random.choice(ex_events)
                self.used_events.append(evt.id)
                return evt
                
        # 4. 否则，从通用随机池抽一张卡
        rand_events = [e for e in available_events if "通用" in e.event_type or "随机" in e.event_type]
        if rand_events:
            evt = random.choice(rand_events)
            self.used_events.append(evt.id)
            return evt
            
        # 5. 保底措施：如果随机池被抽空了，抽普通的固定事件
        fixed_events = [e for e in available_events if "固定" in e.event_type and not e.is_boss]
        if fixed_events:
            evt = fixed_events[0]
            self.used_events.append(evt.id)
            return evt
            
        return None # 游戏通关或当前章节卡池已彻底枯竭
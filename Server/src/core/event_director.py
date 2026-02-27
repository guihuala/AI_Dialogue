import random
from src.core.event_script import EVENT_DATABASE

class EventDirector:
    def __init__(self):
        self.used_events = []
        self.current_chapter = 1
        self.chapter_progress = 0 # 当前章节已经历的事件数
        self.max_events_per_chapter = 4 # 🌟 设定每章的长度（例如：第4个事件必定是期末Boss结算）
        
    def get_next_event(self, player_stats: dict, active_chars: list):
        """核心调度逻辑：重新编排优先级，确保 CG 和日常交替进行"""
        self.chapter_progress += 1
        
        # 0. 过滤出当前章节，且未发生过的可用事件
        available_events = [e for e in EVENT_DATABASE.values() if e.id not in self.used_events and e.chapter == self.current_chapter]
        
        # ---------------------------------------------------------
        # 🌟 优先级 1: 章节 Boss 战 / 关底结算 (进度达到阈值强制触发)
        # ---------------------------------------------------------
        if self.chapter_progress >= self.max_events_per_chapter:
            self.chapter_progress = 0
            self.current_chapter += 1 # 推进到下一章
            
            boss_events = [e for e in EVENT_DATABASE.values() if e.chapter == self.current_chapter - 1 and getattr(e, 'is_boss', False)]
            if boss_events: 
                evt = boss_events[0]
                self.used_events.append(evt.id)
                return evt

        # ---------------------------------------------------------
        # 🌟 优先级 2: 章节开场 CG 或 固定主线 (只要是本章的第 1 个事件，强制播过场)
        # ---------------------------------------------------------
        if self.chapter_progress == 1:
            fixed_events = [e for e in available_events if "固定" in e.event_type or getattr(e, 'is_cg', False)]
            if fixed_events:
                evt = fixed_events[0] # 按配置表顺序取第一个
                self.used_events.append(evt.id)
                return evt

        # ---------------------------------------------------------
        # 🌟 优先级 3: 紧急条件触发池 (玩家数值告急时，强制打断日常)
        # ---------------------------------------------------------
        if player_stats.get("hygiene", 100) < 60:
            cond_events = [e for e in available_events if "条件" in e.event_type and "Hygiene" in e.trigger_conditions]
            if cond_events:
                evt = random.choice(cond_events)
                self.used_events.append(evt.id)
                return evt
                
        if player_stats.get("money", 1500) < 300: # 如果玩家快破产了，触发吃土事件
            cond_events = [e for e in available_events if "条件" in e.event_type and "Money" in e.trigger_conditions]
            if cond_events:
                evt = random.choice(cond_events)
                self.used_events.append(evt.id)
                return evt

        # ---------------------------------------------------------
        # 🌟 优先级 4: 角色专属事件 (根据在场人员概率触发)
        # ---------------------------------------------------------
        ex_events = []
        for e in available_events:
            # 如果事件专属角色在场，加入备选池
            if "专属" in e.event_type and e.exclusive_char in active_chars:
                ex_events.append(e)
        
        # 50%的几率触发专属剧情，留50%给日常，防止太生硬
        if ex_events and random.random() < 0.5:
            evt = random.choice(ex_events)
            self.used_events.append(evt.id)
            return evt
            
        # ---------------------------------------------------------
        # 🌟 优先级 5: 通用随机池 (日常划水填充)
        # ---------------------------------------------------------
        rand_events = [e for e in available_events if "通用" in e.event_type or "随机" in e.event_type]
        if rand_events:
            evt = random.choice(rand_events)
            self.used_events.append(evt.id)
            return evt
            
        # ---------------------------------------------------------
        # 🌟 兜底：如果上面的卡池都没抽到，有什么出什么
        # ---------------------------------------------------------
        if available_events:
            evt = random.choice(available_events)
            self.used_events.append(evt.id)
            return evt
            
        return None # 卡池彻底抽空，游戏结束